import argparse
import os

from wikify.config import discover_base
from wikify.envelope import envelope_error, envelope_ok, print_output
from wikify.graph.builder import build_graph_artifacts


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

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    payload, exit_code = args.func(args)
    print_output(payload, args.output)
    raise SystemExit(exit_code)


if __name__ == '__main__':
    main()
