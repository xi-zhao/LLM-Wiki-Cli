import json
from pathlib import Path

from wikify.maintenance.bundle_request import (
    BundleRequestError,
    build_bundle_request,
    request_path,
    write_bundle_request,
)
from wikify.maintenance.bundle_producer import (
    DEFAULT_TIMEOUT_SECONDS,
    BundleProducerError,
    produce_patch_bundle,
)
from wikify.maintenance.bundle_verifier import BundleVerifierError, verify_patch_bundle
from wikify.maintenance.patch_apply import PatchApplyError, apply_patch_bundle, preflight_patch_bundle
from wikify.maintenance.proposal import ProposalError, build_patch_proposal, proposal_path, write_patch_proposal
from wikify.maintenance.task_lifecycle import TaskLifecycleError, apply_lifecycle_action
from wikify.maintenance.task_reader import TaskNotFound, TaskQueueNotFound, load_task_queue, select_tasks


SCHEMA_VERSION = 'wikify.agent-task-run.v1'
BUNDLE_DIR_RELATIVE_PATH = Path('sorted') / 'graph-patch-bundles'


class TaskRunError(ValueError):
    def __init__(self, message: str, code: str = 'agent_task_run_failed', details: dict | None = None):
        self.code = code
        self.details = details or {}
        super().__init__(message)


def _relative_to_root(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root)).replace('\\', '/')
    except ValueError:
        return str(path)


def _bundle_path(root: Path, task_id: str, bundle_path: Path | str | None = None) -> Path:
    if bundle_path:
        path = Path(bundle_path).expanduser()
        if not path.is_absolute():
            path = root / path
        return path.resolve()
    return (root / BUNDLE_DIR_RELATIVE_PATH / f'{task_id}.json').resolve()


def _step(name: str, status: str, **extra) -> dict:
    payload = {'name': name, 'status': status}
    payload.update({key: value for key, value in extra.items() if value is not None})
    return payload


def _wrap_error(exc: Exception, phase: str) -> TaskRunError:
    if isinstance(exc, TaskQueueNotFound):
        code = 'agent_task_queue_missing'
        details = {'path': str(exc.path)}
    elif isinstance(exc, TaskNotFound):
        code = 'agent_task_not_found'
        details = {'id': exc.task_id}
    else:
        code = getattr(exc, 'code', 'agent_task_run_failed')
        details = dict(getattr(exc, 'details', {}) or {})
    details['phase'] = phase
    return TaskRunError(str(exc), code=code, details=details)


def _verifier_rejection_feedback(exc: BundleVerifierError) -> dict:
    details = dict(exc.details or {})
    verdict = dict(details.get('verdict') or {})
    return {
        'source': 'bundle_verifier',
        'reason': exc.code,
        'summary': verdict.get('summary') or str(exc),
        'findings': verdict.get('findings') or [],
        'verification_path': details.get('verification_path'),
        'verdict': verdict,
    }


def _task_for_task(root: Path, task_id: str) -> dict:
    queue = load_task_queue(root)
    selected = select_tasks(queue, task_id=task_id)
    return selected['tasks'][0]


def _verifier_block_feedback(task: dict) -> dict | None:
    feedback = task.get('blocked_feedback')
    if not isinstance(feedback, dict):
        return None
    if feedback.get('source') != 'bundle_verifier':
        return None
    return feedback


def _latest_verifier_block_event_feedback(root: Path, task_id: str) -> dict | None:
    from wikify.maintenance.task_lifecycle import events_path

    path = events_path(root)
    try:
        document = json.loads(path.read_text(encoding='utf-8'))
    except (FileNotFoundError, ValueError):
        return None
    for event in reversed(document.get('events') or []):
        if event.get('task_id') != task_id or event.get('action') != 'block':
            continue
        details = event.get('details')
        if isinstance(details, dict) and details.get('source') == 'bundle_verifier':
            return details
    return None


def _repair_feedback_for_task(
    root: Path,
    task_id: str,
    agent_command: str | list[str] | None,
) -> dict | None:
    if not agent_command:
        return None
    task = _task_for_task(root, task_id)
    status = task.get('status') or 'queued'
    if status == 'blocked':
        return _verifier_block_feedback(task)
    if status not in {'queued', 'proposed'}:
        return None
    return _latest_verifier_block_event_feedback(root, task_id)


def _verifier_rejection_error(root: Path, task_id: str, exc: BundleVerifierError) -> TaskRunError:
    feedback = _verifier_rejection_feedback(exc)
    details = dict(exc.details or {})
    details['phase'] = 'bundle_verifier'
    details['summary'] = feedback['summary']
    details['findings'] = feedback['findings']
    details['feedback'] = feedback

    try:
        lifecycle = apply_lifecycle_action(
            root,
            task_id,
            'block',
            note='patch bundle rejected by verifier',
            details=feedback,
        )
    except TaskLifecycleError as lifecycle_exc:
        details['lifecycle_error'] = {
            'code': lifecycle_exc.code,
            'message': str(lifecycle_exc),
            'details': lifecycle_exc.details,
        }
    else:
        details['agent_tasks'] = lifecycle['artifacts']['agent_tasks']
        details['task_events'] = lifecycle['artifacts']['task_events']

    return TaskRunError(str(exc), code=exc.code, details=details)


def _status_for_task(root: Path, task_id: str) -> str:
    queue = load_task_queue(root)
    selected = select_tasks(queue, task_id=task_id)
    return selected['tasks'][0].get('status') or 'queued'


def _mark_proposed_if_needed(root: Path, task_id: str, relative_proposal_path: str) -> dict | None:
    status = _status_for_task(root, task_id)
    if status == 'queued':
        return apply_lifecycle_action(root, task_id, 'mark_proposed', proposal_path=relative_proposal_path)
    return None


def _retry_blocked_verifier_task_if_needed(root: Path, task_id: str, should_repair: bool) -> dict | None:
    if not should_repair:
        return None
    if _status_for_task(root, task_id) != 'blocked':
        return None
    return apply_lifecycle_action(
        root,
        task_id,
        'retry',
        note='retrying verifier-blocked task for repair',
    )


def _mark_done_if_needed(root: Path, task_id: str) -> dict | None:
    status = _status_for_task(root, task_id)
    if status == 'done':
        return None
    return apply_lifecycle_action(root, task_id, 'mark_done')


def _base_result(root: Path, task_id: str, dry_run: bool, proposal_file: Path, bundle_file: Path) -> dict:
    return {
        'schema_version': SCHEMA_VERSION,
        'base': str(root),
        'task_id': task_id,
        'dry_run': dry_run,
        'status': 'running',
        'steps': [],
        'artifacts': {
            'proposal': str(proposal_file) if proposal_file.exists() else None,
            'bundle': str(bundle_file) if bundle_file.exists() else None,
            'verification': None,
            'patch_bundle_request': None,
            'application': None,
            'agent_tasks': None,
            'task_events': None,
        },
        'next_actions': [],
        'summary': {
            'task_id': task_id,
        },
    }


def run_agent_task(
    base: Path | str,
    task_id: str,
    bundle_path: Path | str | None = None,
    dry_run: bool = False,
    agent_command: str | list[str] | None = None,
    producer_timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    verifier_command: str | list[str] | None = None,
    verifier_timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict:
    root = Path(base).expanduser().resolve()
    proposal_file = proposal_path(root, task_id)
    bundle_file = _bundle_path(root, task_id, bundle_path)
    relative_proposal_path = _relative_to_root(root, proposal_file)
    result = _base_result(root, task_id, dry_run, proposal_file, bundle_file)
    repairing_verifier_rejection = False
    repair_feedback = None

    try:
        load_task_queue(root)
        repair_feedback = _repair_feedback_for_task(root, task_id, agent_command)
        repairing_verifier_rejection = repair_feedback is not None and not dry_run
        if repairing_verifier_rejection:
            lifecycle = _retry_blocked_verifier_task_if_needed(root, task_id, repairing_verifier_rejection)
            if lifecycle:
                result['steps'].append(_step('lifecycle', 'retried_blocked_verifier_task', event=lifecycle.get('event')))
                result['artifacts']['agent_tasks'] = lifecycle['artifacts']['agent_tasks']
                result['artifacts']['task_events'] = lifecycle['artifacts']['task_events']
        proposal = build_patch_proposal(root, task_id)
    except TaskLifecycleError as exc:
        raise _wrap_error(exc, 'lifecycle') from exc
    except (ProposalError, Exception) as exc:
        raise _wrap_error(exc, 'proposal') from exc

    if proposal_file.exists():
        result['steps'].append(_step('proposal', 'existing', path=str(proposal_file)))
        result['artifacts']['proposal'] = str(proposal_file)
    elif dry_run:
        result['steps'].append(_step('proposal', 'would_write', path=str(proposal_file)))
    else:
        try:
            written_path = write_patch_proposal(root, proposal)
        except ProposalError as exc:
            raise _wrap_error(exc, 'proposal') from exc
        result['steps'].append(_step('proposal', 'written', path=str(written_path)))
        result['artifacts']['proposal'] = str(written_path)

    if dry_run:
        result['steps'].append(_step('lifecycle', 'would_mark_proposed', from_status=_status_for_task(root, task_id)))
    else:
        try:
            lifecycle = _mark_proposed_if_needed(root, task_id, relative_proposal_path)
        except TaskLifecycleError as exc:
            raise _wrap_error(exc, 'lifecycle') from exc
        if lifecycle:
            result['steps'].append(_step('lifecycle', 'marked_proposed', event=lifecycle.get('event')))
            result['artifacts']['agent_tasks'] = lifecycle['artifacts']['agent_tasks']
            result['artifacts']['task_events'] = lifecycle['artifacts']['task_events']
        else:
            result['steps'].append(_step('lifecycle', 'proposal_state_already_set'))

    should_produce_bundle = not bundle_file.exists() or repairing_verifier_rejection
    if should_produce_bundle:
        try:
            bundle_request = build_bundle_request(root, task_id, repair_feedback=repair_feedback)
        except BundleRequestError as exc:
            raise _wrap_error(exc, 'bundle_request') from exc

        bundle_request_file = request_path(root, task_id)
        result['summary']['bundle_request_path'] = str(bundle_request_file)
        result['summary']['suggested_bundle_path'] = bundle_request.get('suggested_bundle_path')
        if dry_run:
            result['steps'].append(_step('bundle_request', 'would_write', path=str(bundle_request_file)))
            if agent_command:
                result['steps'].append(_step('bundle_producer', 'would_execute'))
        else:
            try:
                written_request_path = write_bundle_request(root, bundle_request)
            except BundleRequestError as exc:
                raise _wrap_error(exc, 'bundle_request') from exc
            request_status = 'repair_written' if repairing_verifier_rejection else 'written'
            result['steps'].append(_step('bundle_request', request_status, path=str(written_request_path)))
            result['artifacts']['patch_bundle_request'] = str(written_request_path)

            if agent_command:
                try:
                    production = produce_patch_bundle(
                        root,
                        written_request_path,
                        agent_command,
                        timeout_seconds=producer_timeout_seconds,
                    )
                except BundleProducerError as exc:
                    raise _wrap_error(exc, 'bundle_producer') from exc
                result['steps'].append(_step('bundle_producer', 'bundle_ready', production=production))
                bundle_file = Path(production['artifacts']['patch_bundle'])
                result['artifacts']['bundle'] = str(bundle_file)

        if not agent_command or dry_run:
            result['status'] = 'waiting_for_patch_bundle'
            result['artifacts']['bundle'] = None
            result['next_actions'] = ['generate_patch_bundle']
            result['summary']['next_action'] = 'generate_patch_bundle'
            result['summary']['bundle_path'] = str(bundle_file)
            return result

    result['artifacts']['bundle'] = str(bundle_file)
    if dry_run:
        if proposal_file.exists():
            try:
                preflight = preflight_patch_bundle(root, proposal_file, bundle_file)
            except PatchApplyError as exc:
                raise _wrap_error(exc, 'apply') from exc
            result['steps'].append(_step('apply', 'preflight_passed', preflight=preflight))
            if verifier_command:
                result['steps'].append(_step('bundle_verifier', 'would_execute'))
            result['status'] = 'ready_to_apply'
        else:
            result['steps'].append(_step('apply', 'would_preflight_after_proposal_write'))
            result['status'] = 'waiting_for_proposal_write'
        return result

    if verifier_command:
        try:
            verification = verify_patch_bundle(
                root,
                proposal_file,
                bundle_file,
                verifier_command,
                timeout_seconds=verifier_timeout_seconds,
            )
        except BundleVerifierError as exc:
            if exc.code == 'patch_bundle_verification_rejected':
                raise _verifier_rejection_error(root, task_id, exc) from exc
            raise _wrap_error(exc, 'bundle_verifier') from exc
        result['steps'].append(_step('bundle_verifier', 'accepted', verification=verification))
        result['artifacts']['verification'] = verification['artifacts']['verification']

    try:
        application = apply_patch_bundle(root, proposal_file, bundle_file)
    except PatchApplyError as exc:
        raise _wrap_error(exc, 'apply') from exc
    result['steps'].append(_step('apply', 'applied', application_id=application.get('application_id')))
    result['artifacts']['application'] = application['artifacts']['application']

    try:
        lifecycle = _mark_done_if_needed(root, task_id)
    except TaskLifecycleError as exc:
        raise _wrap_error(exc, 'lifecycle') from exc
    if lifecycle:
        result['steps'].append(_step('lifecycle', 'marked_done', event=lifecycle.get('event')))
        result['artifacts']['agent_tasks'] = lifecycle['artifacts']['agent_tasks']
        result['artifacts']['task_events'] = lifecycle['artifacts']['task_events']
    else:
        result['steps'].append(_step('lifecycle', 'done_state_already_set'))

    result['status'] = 'completed'
    result['summary']['application_id'] = application.get('application_id')
    return result
