from pathlib import Path

from wikify.maintenance.bundle_request import (
    BundleRequestError,
    build_bundle_request,
    request_path,
    write_bundle_request,
)
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


def _status_for_task(root: Path, task_id: str) -> str:
    queue = load_task_queue(root)
    selected = select_tasks(queue, task_id=task_id)
    return selected['tasks'][0].get('status') or 'queued'


def _mark_proposed_if_needed(root: Path, task_id: str, relative_proposal_path: str) -> dict | None:
    status = _status_for_task(root, task_id)
    if status == 'queued':
        return apply_lifecycle_action(root, task_id, 'mark_proposed', proposal_path=relative_proposal_path)
    return None


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
) -> dict:
    root = Path(base).expanduser().resolve()
    proposal_file = proposal_path(root, task_id)
    bundle_file = _bundle_path(root, task_id, bundle_path)
    relative_proposal_path = _relative_to_root(root, proposal_file)
    result = _base_result(root, task_id, dry_run, proposal_file, bundle_file)

    try:
        load_task_queue(root)
        proposal = build_patch_proposal(root, task_id)
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

    if not bundle_file.exists():
        try:
            bundle_request = build_bundle_request(root, task_id)
        except BundleRequestError as exc:
            raise _wrap_error(exc, 'bundle_request') from exc

        bundle_request_file = request_path(root, task_id)
        result['summary']['bundle_request_path'] = str(bundle_request_file)
        result['summary']['suggested_bundle_path'] = bundle_request.get('suggested_bundle_path')
        if dry_run:
            result['steps'].append(_step('bundle_request', 'would_write', path=str(bundle_request_file)))
        else:
            try:
                written_request_path = write_bundle_request(root, bundle_request)
            except BundleRequestError as exc:
                raise _wrap_error(exc, 'bundle_request') from exc
            result['steps'].append(_step('bundle_request', 'written', path=str(written_request_path)))
            result['artifacts']['patch_bundle_request'] = str(written_request_path)

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
            result['status'] = 'ready_to_apply'
        else:
            result['steps'].append(_step('apply', 'would_preflight_after_proposal_write'))
            result['status'] = 'waiting_for_proposal_write'
        return result

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
