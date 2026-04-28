import argparse
import os

from wikify.config import discover_base
from wikify.envelope import envelope_error, envelope_ok, print_output
from wikify.graph.builder import build_graph_artifacts
from wikify.maintenance.task_reader import (
    TaskNotFound,
    TaskQueueNotFound,
    load_task_queue,
    select_tasks,
    task_queue_path,
)
from wikify.maintenance.runner import run_maintenance


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


def cmd_tasks(args):
    base = discover_base()
    try:
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
        p_tasks.add_argument('--status', choices=['queued', 'in_progress', 'done', 'blocked'])
        p_tasks.add_argument('--action')
        p_tasks.add_argument('--id')
        p_tasks.add_argument('--limit', type=int)
        p_tasks.add_argument('--refresh', action='store_true')
        p_tasks.add_argument('--policy', choices=['conservative', 'balanced', 'aggressive'], default='balanced')
        p_tasks.set_defaults(func=cmd_tasks)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    payload, exit_code = args.func(args)
    print_output(payload, args.output)
    raise SystemExit(exit_code)


if __name__ == '__main__':
    main()
