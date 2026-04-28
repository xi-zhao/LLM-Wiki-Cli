import argparse
import os

from wikify.config import discover_base
from wikify.envelope import envelope_error, envelope_ok, print_output
from wikify.graph.builder import build_graph_artifacts
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
from wikify.maintenance.batch_runner import (
    DEFAULT_LIMIT as DEFAULT_BATCH_LIMIT,
    DEFAULT_STATUS as DEFAULT_BATCH_STATUS,
    BatchTaskRunError,
    run_agent_tasks,
)
from wikify.maintenance.patch_apply import (
    PatchApplyError,
    apply_patch_bundle,
    preflight_patch_bundle,
    rollback_application,
)
from wikify.maintenance.proposal import (
    ProposalError,
    build_patch_proposal,
    proposal_path,
    write_patch_proposal,
)
from wikify.maintenance.task_lifecycle import TaskLifecycleError, apply_lifecycle_action
from wikify.maintenance.task_reader import (
    TaskNotFound,
    TaskQueueNotFound,
    load_task_queue,
    select_tasks,
    task_queue_path,
)
from wikify.maintenance.runner import run_maintenance
from wikify.maintenance.task_runner import TaskRunError, run_agent_task


def _sync_legacy_env():
    wikify_base = os.environ.get('WIKIFY_BASE')
    if wikify_base and not os.environ.get('FOKB_BASE'):
        os.environ['FOKB_BASE'] = wikify_base


def _legacy_fokb():
    _sync_legacy_env()
    from scripts import fokb

    return fokb


def cmd_graph(args):
    try:
        result = build_graph_artifacts(
            discover_base(),
            scope=args.scope,
            include_html=not args.no_html,
        )
    except Exception as exc:
        return envelope_error(
            'graph',
            'graph_build_failed',
            str(exc),
            1,
            retryable=False,
        )
    artifacts = [path for path in result.get('artifacts', {}).values() if path]
    result['completion'] = {
        'status': 'completed',
        'summary': 'graph completed, artifacts written to graph directory',
        'artifacts': artifacts,
        'next_actions': [],
        'user_message': 'graph completed',
    }
    return envelope_ok('graph', result)


def cmd_maintain(args):
    try:
        result = run_maintenance(
            discover_base(),
            policy=args.policy,
            dry_run=args.dry_run,
        )
    except Exception as exc:
        return envelope_error(
            'maintain',
            'graph_maintenance_failed',
            str(exc),
            1,
            retryable=False,
        )
    artifacts = [path for path in result.get('artifacts', {}).values() if path]
    result['completion'] = {
        'status': 'completed',
        'summary': 'maintenance completed, graph audit artifacts generated',
        'artifacts': artifacts,
        'next_actions': result.get('next_commands', []),
        'user_message': 'maintenance completed',
    }
    return envelope_ok('maintain', result)


def _tasks_lifecycle_action(args):
    actions = [
        ('mark_proposed', args.mark_proposed),
        ('start', args.start),
        ('mark_done', args.mark_done),
        ('mark_failed', args.mark_failed),
        ('block', args.block),
        ('cancel', args.cancel),
        ('retry', args.retry),
        ('restore', args.restore),
    ]
    selected = [action for action, enabled in actions if enabled]
    if len(selected) > 1:
        raise ValueError('only one lifecycle action can be used at a time')
    return selected[0] if selected else None


def cmd_tasks(args):
    base = discover_base()
    try:
        lifecycle_action = _tasks_lifecycle_action(args)
        if lifecycle_action:
            if not args.id:
                return envelope_error(
                    'tasks',
                    'agent_task_id_required',
                    'task id is required for lifecycle actions',
                    2,
                    retryable=False,
                )
            result = apply_lifecycle_action(
                base,
                args.id,
                lifecycle_action,
                note=args.note,
                proposal_path=args.proposal_path,
            )
            result['completion'] = {
                'status': 'completed',
                'summary': 'agent task lifecycle action completed',
                'artifacts': [
                    result['artifacts']['agent_tasks'],
                    result['artifacts']['task_events'],
                ],
                'next_actions': [],
                'user_message': 'agent task lifecycle action completed',
            }
            return envelope_ok('tasks', result)

        refreshed = False
        refresh_result = None
        if args.refresh:
            refresh_result = run_maintenance(
                base,
                policy=args.policy,
                dry_run=False,
            )
            queue = refresh_result['task_queue']
            refreshed = True
        else:
            queue = load_task_queue(base)

        selected = select_tasks(
            queue,
            status=args.status,
            action=args.action,
            task_id=args.id,
            limit=args.limit,
        )
    except TaskQueueNotFound as exc:
        return envelope_error(
            'tasks',
            'agent_task_queue_missing',
            'agent task queue not found; run wikify maintain first or use --refresh',
            2,
            retryable=False,
            details={'path': str(exc.path)},
        )
    except TaskNotFound as exc:
        return envelope_error(
            'tasks',
            'agent_task_not_found',
            'agent task not found',
            2,
            retryable=False,
            details={'id': exc.task_id},
        )
    except TaskLifecycleError as exc:
        return envelope_error(
            'tasks',
            exc.code,
            str(exc),
            2,
            retryable=False,
            details=exc.details,
        )
    except ValueError as exc:
        return envelope_error(
            'tasks',
            'invalid_agent_task_query',
            str(exc),
            1,
            retryable=False,
        )
    except Exception as exc:
        return envelope_error(
            'tasks',
            'agent_task_query_failed',
            str(exc),
            1,
            retryable=False,
        )

    result = {
        'base': str(base),
        'refreshed': refreshed,
        'artifacts': {
            'agent_tasks': str(task_queue_path(base)),
        },
        'summary': selected['summary'],
        'task_queue': selected,
        'completion': {
            'status': 'completed',
            'summary': 'agent task query completed',
            'artifacts': [str(task_queue_path(base))],
            'next_actions': [],
            'user_message': 'agent task query completed',
        },
    }
    if refresh_result:
        result['refresh'] = {
            'summary': refresh_result.get('summary', {}),
            'artifacts': refresh_result.get('artifacts', {}),
        }
    return envelope_ok('tasks', result)


def cmd_propose(args):
    base = discover_base()
    try:
        proposal = build_patch_proposal(base, args.task_id)
        expected_path = proposal_path(base, args.task_id)
        written_path = None
        if not args.dry_run:
            written_path = write_patch_proposal(base, proposal)
    except TaskQueueNotFound as exc:
        return envelope_error(
            'propose',
            'agent_task_queue_missing',
            'agent task queue not found; run wikify maintain first',
            2,
            retryable=False,
            details={'path': str(exc.path)},
        )
    except TaskNotFound as exc:
        return envelope_error(
            'propose',
            'agent_task_not_found',
            'agent task not found',
            2,
            retryable=False,
            details={'id': exc.task_id},
        )
    except ProposalError as exc:
        return envelope_error(
            'propose',
            exc.code,
            str(exc),
            2,
            retryable=False,
            details=exc.details,
        )
    except Exception as exc:
        return envelope_error(
            'propose',
            'patch_proposal_failed',
            str(exc),
            1,
            retryable=False,
        )

    artifact_path = str(expected_path)
    result = {
        'base': str(base),
        'dry_run': args.dry_run,
        'artifact_path': artifact_path,
        'artifacts': {
            'patch_proposal': str(written_path) if written_path else None,
        },
        'summary': {
            'task_id': proposal.get('task_id'),
            'planned_edit_count': len(proposal.get('planned_edits', [])),
            'written': written_path is not None,
            'risk': proposal.get('risk'),
        },
        'proposal': proposal,
        'completion': {
            'status': 'completed',
            'summary': 'patch proposal generated',
            'artifacts': [str(written_path)] if written_path else [],
            'next_actions': [],
            'user_message': 'patch proposal generated',
        },
    }
    return envelope_ok('propose', result)


def cmd_bundle_request(args):
    base = discover_base()
    try:
        request = build_bundle_request(base, args.task_id)
        expected_path = request_path(base, args.task_id)
        proposal_file = proposal_path(base, args.task_id)
        written_request_path = None
        written_proposal_path = None
        if not args.dry_run:
            if not proposal_file.exists():
                written_proposal_path = write_patch_proposal(base, request['proposal'])
            written_request_path = write_bundle_request(base, request)
    except TaskQueueNotFound as exc:
        return envelope_error(
            'bundle-request',
            'agent_task_queue_missing',
            'agent task queue not found; run wikify maintain first',
            2,
            retryable=False,
            details={'path': str(exc.path)},
        )
    except TaskNotFound as exc:
        return envelope_error(
            'bundle-request',
            'agent_task_not_found',
            'agent task not found',
            2,
            retryable=False,
            details={'id': exc.task_id},
        )
    except ProposalError as exc:
        return envelope_error(
            'bundle-request',
            exc.code,
            str(exc),
            2,
            retryable=False,
            details=exc.details,
        )
    except BundleRequestError as exc:
        return envelope_error(
            'bundle-request',
            exc.code,
            str(exc),
            2,
            retryable=False,
            details=exc.details,
        )
    except Exception as exc:
        return envelope_error(
            'bundle-request',
            'bundle_request_failed',
            str(exc),
            1,
            retryable=False,
        )

    artifacts = {
        'patch_bundle_request': str(written_request_path) if written_request_path else None,
        'patch_proposal': str(written_proposal_path) if written_proposal_path else (str(proposal_file) if proposal_file.exists() and not args.dry_run else None),
    }
    result = {
        'base': str(base),
        'dry_run': args.dry_run,
        'artifact_path': str(expected_path),
        'suggested_bundle_path': request.get('suggested_bundle_path'),
        'artifacts': artifacts,
        'summary': {
            'task_id': request.get('task_id'),
            'target_count': len(request.get('targets', [])),
            'written': written_request_path is not None,
            'proposal_written': written_proposal_path is not None,
            'suggested_bundle_path': request.get('suggested_bundle_path'),
        },
        'request': request,
        'completion': {
            'status': 'completed',
            'summary': 'patch bundle request generated',
            'artifacts': [path for path in artifacts.values() if path],
            'next_actions': ['generate_patch_bundle'],
            'user_message': 'patch bundle request generated',
        },
    }
    return envelope_ok('bundle-request', result)


def cmd_produce_bundle(args):
    base = discover_base()
    try:
        result = produce_patch_bundle(
            base,
            args.request_path,
            args.agent_command,
            timeout_seconds=args.timeout,
            dry_run=args.dry_run,
        )
    except BundleProducerError as exc:
        return envelope_error(
            'produce-bundle',
            exc.code,
            str(exc),
            2,
            retryable=False,
            details=exc.details,
        )
    except Exception as exc:
        return envelope_error(
            'produce-bundle',
            'bundle_producer_failed',
            str(exc),
            1,
            retryable=False,
        )

    artifacts = [path for path in result.get('artifacts', {}).values() if path]
    result['completion'] = {
        'status': result.get('status'),
        'summary': 'patch bundle production completed',
        'artifacts': artifacts,
        'next_actions': ['run_task'] if result.get('status') == 'bundle_ready' else [],
        'user_message': 'patch bundle production completed',
    }
    return envelope_ok('produce-bundle', result)


def cmd_apply(args):
    base = discover_base()
    try:
        if args.dry_run:
            result = preflight_patch_bundle(base, args.proposal_path, args.bundle_path)
            result['dry_run'] = True
            result['artifacts'] = {'application': None}
        else:
            result = apply_patch_bundle(base, args.proposal_path, args.bundle_path)
            result['dry_run'] = False
    except PatchApplyError as exc:
        return envelope_error(
            'apply',
            exc.code,
            str(exc),
            2,
            retryable=False,
            details=exc.details,
        )
    except Exception as exc:
        return envelope_error(
            'apply',
            'patch_apply_failed',
            str(exc),
            1,
            retryable=False,
        )

    artifacts = [path for path in result.get('artifacts', {}).values() if path]
    result['completion'] = {
        'status': 'completed',
        'summary': 'patch apply preflight completed' if args.dry_run else 'patch applied',
        'artifacts': artifacts,
        'next_actions': [],
        'user_message': 'patch apply preflight completed' if args.dry_run else 'patch applied',
    }
    return envelope_ok('apply', result)


def cmd_rollback(args):
    base = discover_base()
    try:
        result = rollback_application(base, args.application_path, dry_run=args.dry_run)
    except PatchApplyError as exc:
        return envelope_error(
            'rollback',
            exc.code,
            str(exc),
            2,
            retryable=False,
            details=exc.details,
        )
    except Exception as exc:
        return envelope_error(
            'rollback',
            'patch_rollback_failed',
            str(exc),
            1,
            retryable=False,
        )

    artifacts = [path for path in result.get('artifacts', {}).values() if path]
    result['completion'] = {
        'status': 'completed',
        'summary': 'patch rollback preflight completed' if args.dry_run else 'patch rolled back',
        'artifacts': artifacts,
        'next_actions': [],
        'user_message': 'patch rollback preflight completed' if args.dry_run else 'patch rolled back',
    }
    return envelope_ok('rollback', result)


def cmd_run_task(args):
    base = discover_base()
    try:
        result = run_agent_task(
            base,
            args.id,
            bundle_path=args.bundle_path,
            dry_run=args.dry_run,
            agent_command=args.agent_command,
            producer_timeout_seconds=args.producer_timeout,
        )
    except TaskRunError as exc:
        return envelope_error(
            'run-task',
            exc.code,
            str(exc),
            2,
            retryable=False,
            details=exc.details,
        )
    except Exception as exc:
        return envelope_error(
            'run-task',
            'agent_task_run_failed',
            str(exc),
            1,
            retryable=False,
        )

    artifacts = [path for path in result.get('artifacts', {}).values() if path]
    result['completion'] = {
        'status': result.get('status'),
        'summary': 'agent task workflow advanced',
        'artifacts': artifacts,
        'next_actions': result.get('next_actions', []),
        'user_message': 'agent task workflow advanced',
    }
    return envelope_ok('run-task', result)


def cmd_run_tasks(args):
    base = discover_base()
    try:
        result = run_agent_tasks(
            base,
            status=args.status,
            action=args.action,
            task_id=args.id,
            limit=args.limit,
            dry_run=args.dry_run,
            agent_command=args.agent_command,
            producer_timeout_seconds=args.producer_timeout,
            continue_on_error=args.continue_on_error,
        )
    except BatchTaskRunError as exc:
        return envelope_error(
            'run-tasks',
            exc.code,
            str(exc),
            2,
            retryable=False,
            details=exc.details,
        )
    except Exception as exc:
        return envelope_error(
            'run-tasks',
            'agent_task_batch_run_failed',
            str(exc),
            1,
            retryable=False,
        )

    artifacts = [path for path in result.get('artifacts', {}).values() if path]
    result['completion'] = {
        'status': result.get('status'),
        'summary': 'agent task batch workflow advanced',
        'artifacts': artifacts,
        'next_actions': result.get('next_actions', []),
        'user_message': 'agent task batch workflow advanced',
    }
    return envelope_ok('run-tasks', result)


def _subparsers_action(parser: argparse.ArgumentParser):
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    raise RuntimeError('parser has no subparsers action')


def build_parser() -> argparse.ArgumentParser:
    parser = _legacy_fokb().build_parser()
    parser.prog = 'wikify'
    parser.description = 'Wikify agent-facing Markdown knowledge base CLI'

    sub = _subparsers_action(parser)
    if 'graph' not in sub.choices:
        p_graph = sub.add_parser('graph', help='Build graph artifacts from compiled Markdown wiki files')
        p_graph.add_argument('--scope', choices=['all', 'topics', 'timelines', 'briefs', 'parsed', 'sorted', 'sources'], default='all')
        p_graph.add_argument('--no-html', action='store_true')
        p_graph.set_defaults(func=cmd_graph)

    if 'maintain' not in sub.choices:
        p_maintain = sub.add_parser('maintain', help='Run autonomous graph maintenance audit')
        p_maintain.add_argument('--policy', choices=['conservative', 'balanced', 'aggressive'], default='balanced')
        p_maintain.add_argument('--dry-run', action='store_true')
        p_maintain.set_defaults(func=cmd_maintain)

    if 'tasks' not in sub.choices:
        p_tasks = sub.add_parser('tasks', help='Read queued graph agent tasks')
        p_tasks.add_argument('--status', choices=['queued', 'proposed', 'in_progress', 'done', 'failed', 'blocked', 'rejected'])
        p_tasks.add_argument('--action')
        p_tasks.add_argument('--id')
        p_tasks.add_argument('--limit', type=int)
        p_tasks.add_argument('--refresh', action='store_true')
        p_tasks.add_argument('--policy', choices=['conservative', 'balanced', 'aggressive'], default='balanced')
        p_tasks.add_argument('--mark-proposed', action='store_true')
        p_tasks.add_argument('--start', action='store_true')
        p_tasks.add_argument('--mark-done', action='store_true')
        p_tasks.add_argument('--mark-failed', action='store_true')
        p_tasks.add_argument('--block', action='store_true')
        p_tasks.add_argument('--cancel', action='store_true')
        p_tasks.add_argument('--retry', action='store_true')
        p_tasks.add_argument('--restore', action='store_true')
        p_tasks.add_argument('--note')
        p_tasks.add_argument('--proposal-path')
        p_tasks.set_defaults(func=cmd_tasks)

    if 'propose' not in sub.choices:
        p_propose = sub.add_parser('propose', help='Generate a scoped patch proposal from one graph agent task')
        p_propose.add_argument('--task-id', required=True)
        p_propose.add_argument('--dry-run', action='store_true')
        p_propose.set_defaults(func=cmd_propose)

    if 'bundle-request' not in sub.choices:
        p_bundle_request = sub.add_parser('bundle-request', help='Generate an agent-facing patch bundle request')
        p_bundle_request.add_argument('--task-id', required=True)
        p_bundle_request.add_argument('--dry-run', action='store_true')
        p_bundle_request.set_defaults(func=cmd_bundle_request)

    if 'produce-bundle' not in sub.choices:
        p_produce_bundle = sub.add_parser('produce-bundle', help='Invoke an explicit external agent command to produce a patch bundle')
        p_produce_bundle.add_argument('--request-path', required=True)
        p_produce_bundle.add_argument('--agent-command', required=True)
        p_produce_bundle.add_argument('--timeout', type=float, default=DEFAULT_TIMEOUT_SECONDS)
        p_produce_bundle.add_argument('--dry-run', action='store_true')
        p_produce_bundle.set_defaults(func=cmd_produce_bundle)

    if 'apply' not in sub.choices:
        p_apply = sub.add_parser('apply', help='Validate and apply an agent-generated patch bundle')
        p_apply.add_argument('--proposal-path', required=True)
        p_apply.add_argument('--bundle-path', required=True)
        p_apply.add_argument('--dry-run', action='store_true')
        p_apply.set_defaults(func=cmd_apply)

    if 'rollback' not in sub.choices:
        p_rollback = sub.add_parser('rollback', help='Rollback a recorded patch application')
        p_rollback.add_argument('--application-path', required=True)
        p_rollback.add_argument('--dry-run', action='store_true')
        p_rollback.set_defaults(func=cmd_rollback)

    if 'run-task' not in sub.choices:
        p_run_task = sub.add_parser('run-task', help='Advance one graph agent task through proposal, apply, and lifecycle')
        p_run_task.add_argument('--id', required=True)
        p_run_task.add_argument('--bundle-path')
        p_run_task.add_argument('--agent-command')
        p_run_task.add_argument('--producer-timeout', type=float, default=DEFAULT_TIMEOUT_SECONDS)
        p_run_task.add_argument('--dry-run', action='store_true')
        p_run_task.set_defaults(func=cmd_run_task)

    if 'run-tasks' not in sub.choices:
        p_run_tasks = sub.add_parser('run-tasks', help='Advance a bounded batch of graph agent tasks sequentially')
        p_run_tasks.add_argument('--status', choices=['queued', 'proposed', 'in_progress', 'done', 'failed', 'blocked', 'rejected'], default=DEFAULT_BATCH_STATUS)
        p_run_tasks.add_argument('--action')
        p_run_tasks.add_argument('--id')
        p_run_tasks.add_argument('--limit', type=int, default=DEFAULT_BATCH_LIMIT)
        p_run_tasks.add_argument('--agent-command')
        p_run_tasks.add_argument('--producer-timeout', type=float, default=DEFAULT_TIMEOUT_SECONDS)
        p_run_tasks.add_argument('--continue-on-error', action='store_true')
        p_run_tasks.add_argument('--dry-run', action='store_true')
        p_run_tasks.set_defaults(func=cmd_run_tasks)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    payload, exit_code = args.func(args)
    print_output(payload, args.output)
    raise SystemExit(exit_code)


if __name__ == '__main__':
    main()
