import json
import tempfile
import unittest
from pathlib import Path


class AgentInterfaceTests(unittest.TestCase):
    def _read_json(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding='utf-8'))

    def _write_json(self, path: Path, document: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def _init_workspace(self, root: Path):
        from wikify.workspace import initialize_workspace

        initialize_workspace(root)

    def _add_source(self, root: Path, locator: Path | str, source_type: str) -> dict:
        from wikify.workspace import add_source

        return add_source(root, str(locator), source_type)['source']

    def _sync(self, root: Path):
        from wikify.sync import sync_workspace

        return sync_workspace(root)

    def _wikiize(self, root: Path):
        from wikify.wikiize import run_wikiization

        return run_wikiization(root)

    def _views(self, root: Path):
        from wikify.views import run_view_generation

        return run_view_generation(root, include_html=False)

    def _write_note_workspace(
        self,
        root: Path,
        content: str = '# Source Title\n\nAgent Context is durable source-backed context for coding agents.\n',
    ) -> tuple[Path, dict, dict]:
        self._init_workspace(root)
        source_path = root / 'sources' / 'source.md'
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text(content, encoding='utf-8')
        source = self._add_source(root, source_path, 'file')
        sync_result = self._sync(root)
        item = sync_result['items'][0]
        self._wikiize(root)
        return source_path, source, item

    def _write_semantic_object_fixtures(self, root: Path, source: dict, item: dict) -> dict:
        from wikify.objects import (
            make_citation_object,
            make_decision_object,
            make_graph_edge_object,
            make_object_index,
            make_topic_object,
            object_document_path,
            object_index_path,
        )

        page_path = next((root / 'artifacts' / 'objects' / 'wiki_pages').glob('*.json'))
        page = self._read_json(page_path)
        page['outbound_links'] = ['topic_agent_context']
        page['backlinks'] = ['decision_cli_first']
        self._write_json(page_path, page)
        source_refs = [{
            'source_id': source['source_id'],
            'item_id': item['item_id'],
            'locator': item.get('locator'),
            'relative_path': item.get('relative_path'),
            'confidence': 0.91,
        }]
        objects = [
            page,
            make_topic_object(
                object_id='topic_agent_context',
                title='Agent Context',
                summary='Durable context for coding agents.',
                page_ids=[page['id']],
                source_refs=source_refs,
            ),
            make_decision_object(
                object_id='decision_cli_first',
                title='Keep Wikify CLI-first',
                summary='Agents should query durable files and JSON envelopes.',
                status='accepted',
                source_refs=source_refs,
            ),
            make_citation_object(
                object_id='citation_source_title',
                source_id=source['source_id'],
                item_id=item['item_id'],
                locator='sources/source.md#L1',
                confidence=0.91,
                snippet='Source Title',
            ),
            make_graph_edge_object(
                object_id='edge_page_topic',
                source=page['id'],
                target='topic_agent_context',
                edge_type='mentions',
                provenance='EXTRACTED',
                confidence=0.88,
                source_path=page['body_path'],
                line=1,
                label='mentions',
            ),
        ]
        for obj in objects[1:]:
            object_type = obj.get('type') or obj.get('object_type')
            self._write_json(object_document_path(root, object_type, obj['id']), obj)
        self._write_json(object_index_path(root), make_object_index(root, objects))
        self._views(root)
        return page

    def test_agent_export_dry_run_reports_planned_artifacts_without_writes(self):
        from wikify.agent import (
            AGENT_EXPORT_SCHEMA_VERSION,
            agent_graph_path,
            agent_report_path,
            citation_index_path,
            page_index_path,
            related_index_path,
            run_agent_export,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _source_path, source, item = self._write_note_workspace(root)
            self._write_semantic_object_fixtures(root, source, item)

            result = run_agent_export(root, dry_run=True)

            self.assertEqual(result['schema_version'], AGENT_EXPORT_SCHEMA_VERSION)
            self.assertEqual(result['status'], 'dry_run')
            self.assertTrue(result['dry_run'])
            planned = {item['path'] for item in result['planned']}
            self.assertIn('llms.txt', planned)
            self.assertIn('llms-full.txt', planned)
            self.assertIn('artifacts/agent/page-index.json', planned)
            self.assertIn('artifacts/agent/citation-index.json', planned)
            self.assertIn('artifacts/agent/related-index.json', planned)
            self.assertIn('artifacts/agent/graph.json', planned)
            self.assertIn('.wikify/agent/last-agent-export.json', planned)
            self.assertEqual(result['summary']['page_count'], 1)
            self.assertGreaterEqual(result['summary']['citation_evidence_count'], 2)
            self.assertFalse((root / 'llms.txt').exists())
            self.assertFalse((root / 'llms-full.txt').exists())
            self.assertFalse(page_index_path(root).exists())
            self.assertFalse(citation_index_path(root).exists())
            self.assertFalse(related_index_path(root).exists())
            self.assertFalse(agent_graph_path(root).exists())
            self.assertFalse(agent_report_path(root).exists())

    def test_agent_export_writes_llms_and_indexes_from_object_model(self):
        from wikify.agent import (
            AGENT_GRAPH_SCHEMA_VERSION,
            CITATION_INDEX_SCHEMA_VERSION,
            PAGE_INDEX_SCHEMA_VERSION,
            RELATED_INDEX_SCHEMA_VERSION,
            agent_graph_path,
            agent_report_path,
            citation_index_path,
            page_index_path,
            related_index_path,
            run_agent_export,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_path, source, item = self._write_note_workspace(root)
            page = self._write_semantic_object_fixtures(root, source, item)

            result = run_agent_export(root)

            self.assertEqual(result['status'], 'completed')
            self.assertTrue((root / 'llms.txt').is_file())
            self.assertTrue((root / 'llms-full.txt').is_file())
            self.assertTrue(page_index_path(root).is_file())
            self.assertTrue(citation_index_path(root).is_file())
            self.assertTrue(related_index_path(root).is_file())
            self.assertTrue(agent_graph_path(root).is_file())
            self.assertTrue(agent_report_path(root).is_file())

            page_index = self._read_json(page_index_path(root))
            self.assertEqual(page_index['schema_version'], PAGE_INDEX_SCHEMA_VERSION)
            page_entry = page_index['pages'][0]
            for key in [
                'id',
                'title',
                'summary',
                'body_path',
                'review_status',
                'confidence',
                'updated_at',
                'source_refs',
                'outbound_links',
                'backlinks',
                'human_view_path',
            ]:
                self.assertIn(key, page_entry)
            self.assertEqual(page_entry['id'], page['id'])
            self.assertEqual(page_entry['human_view_path'], 'views/pages.md')

            citation_index = self._read_json(citation_index_path(root))
            self.assertEqual(citation_index['schema_version'], CITATION_INDEX_SCHEMA_VERSION)
            evidence_types = [entry['evidence_type'] for entry in citation_index['evidence']]
            self.assertIn('explicit_citation', evidence_types)
            self.assertIn('page_source_ref', evidence_types)

            related_index = self._read_json(related_index_path(root))
            self.assertEqual(related_index['schema_version'], RELATED_INDEX_SCHEMA_VERSION)
            self.assertGreaterEqual(len(related_index['related']), 1)
            signals = related_index['related'][0]['signals']
            for key in [
                'direct_object_link',
                'graph_edge',
                'shared_source',
                'citation_overlap',
                'common_neighbor',
                'type_affinity',
                'text_match',
            ]:
                self.assertIn(key, signals)

            graph = self._read_json(agent_graph_path(root))
            self.assertEqual(graph['schema_version'], AGENT_GRAPH_SCHEMA_VERSION)
            self.assertIn(page['id'], {node['id'] for node in graph['nodes']})
            self.assertIn('provenance', graph['edges'][0])
            self.assertFalse((root / 'graph' / 'graph.json').exists())

            llms = (root / 'llms.txt').read_text(encoding='utf-8')
            self.assertIn('Wikify Agent Context', llms)
            self.assertIn('artifacts/agent/page-index.json', llms)
            self.assertIn('artifacts/agent/citation-index.json', llms)
            self.assertIn('cite source refs', llms)

            llms_full = (root / 'llms-full.txt').read_text(encoding='utf-8')
            self.assertIn('Truncation', llms_full)
            self.assertIn('Agent Context is durable source-backed context', llms_full)
            self.assertNotIn(str(source_path), llms_full)
            self.assertIn('artifacts/agent/page-index.json', result['completion']['artifacts'])

    def test_agent_context_dry_run_selects_budgeted_source_backed_items_without_writes(self):
        from wikify.agent import context_pack_dir, context_pack_manifest_path, run_agent_context

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _source_path, source, item = self._write_note_workspace(root)
            self._write_semantic_object_fixtures(root, source, item)

            result = run_agent_context(root, 'agent context', dry_run=True, max_chars=800, max_pages=2)

            self.assertEqual(result['schema_version'], 'wikify.context-pack.v1')
            self.assertEqual(result['status'], 'dry_run')
            self.assertEqual(result['query'], 'agent context')
            self.assertFalse(context_pack_dir(root).exists())
            self.assertFalse(context_pack_manifest_path(root).exists())
            self.assertEqual(result['budget']['requested_max_chars'], 800)
            self.assertEqual(result['budget']['max_pages'], 2)
            self.assertLessEqual(result['budget']['included_chars'], 800)
            self.assertGreater(len(result['items']), 0)
            selected = result['items'][0]
            for key in [
                'object_id',
                'type',
                'title',
                'summary',
                'body_path',
                'excerpt',
                'excerpt_chars',
                'truncated',
                'selection_rationale',
                'source_refs',
                'citations',
                'related',
            ]:
                self.assertIn(key, selected)
            self.assertTrue(selected['selection_rationale'])
            self.assertTrue(selected['source_refs'])
            self.assertIn('citations', result)
            self.assertIn('related', result)

            small = run_agent_context(root, 'agent context', dry_run=True, max_chars=80, max_pages=1)

            self.assertTrue(small['budget']['truncated'])
            self.assertTrue(
                any(item['truncated'] for item in small['items'])
                or small['budget']['omitted_count'] > 0
            )

    def test_agent_context_writes_pack_object_manifest_and_object_index(self):
        from wikify.agent import (
            CONTEXT_PACK_MANIFEST_SCHEMA_VERSION,
            context_pack_dir,
            context_pack_manifest_path,
            run_agent_context,
        )
        from wikify.object_validation import validate_workspace_objects
        from wikify.objects import object_artifacts_dir, object_document_path, object_index_path

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _source_path, source, item = self._write_note_workspace(root)
            self._write_semantic_object_fixtures(root, source, item)

            result = run_agent_context(root, 'agent context', max_chars=800, max_pages=2)

            pack_id = result['id']
            pack_path = context_pack_dir(root) / f'{pack_id}.json'
            object_path = object_document_path(root, 'context_pack', pack_id)
            self.assertEqual(result['schema_version'], 'wikify.context-pack.v1')
            self.assertEqual(result['status'], 'completed')
            self.assertTrue(pack_path.is_file())
            self.assertTrue(object_path.is_file())
            self.assertTrue(context_pack_manifest_path(root).is_file())

            pack = self._read_json(pack_path)
            for key in [
                'schema_version',
                'query',
                'object_ids',
                'source_refs',
                'items',
                'budget',
                'selection',
                'citations',
                'related',
            ]:
                self.assertIn(key, pack)

            manifest = self._read_json(context_pack_manifest_path(root))
            self.assertEqual(manifest['schema_version'], CONTEXT_PACK_MANIFEST_SCHEMA_VERSION)
            self.assertEqual(manifest['latest_pack_id'], pack_id)
            self.assertIn(pack_id, {entry['id'] for entry in manifest['packs']})

            object_index = self._read_json(object_index_path(root))
            context_entries = [
                entry for entry in object_index['objects']
                if entry.get('id') == pack_id and entry.get('type') == 'context_pack'
            ]
            self.assertEqual(len(context_entries), 1)

            validation = validate_workspace_objects(root, path=object_artifacts_dir(root), strict=True, write_report=False)
            self.assertEqual(validation['summary']['error_count'], 0)

    def test_agent_cite_returns_explicit_and_fallback_evidence_without_fabrication(self):
        from wikify.agent import query_agent_citations

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _source_path, source, item = self._write_note_workspace(root)
            page = self._write_semantic_object_fixtures(root, source, item)

            result = query_agent_citations(root, 'Source Title', limit=10)

            self.assertEqual(result['schema_version'], 'wikify.citation-query.v1')
            evidence = result['evidence']
            self.assertGreaterEqual(len(evidence), 2)
            evidence_types = [entry['evidence_type'] for entry in evidence]
            self.assertLess(evidence_types.index('explicit_citation'), evidence_types.index('page_source_ref'))
            first = evidence[0]
            for key in [
                'source_id',
                'item_id',
                'locator',
                'confidence',
                'linked_object_ids',
                'evidence_type',
            ]:
                self.assertIn(key, first)
            self.assertTrue(first.get('snippet') or first.get('span') is not None)
            self.assertIn(page['id'], set(first['linked_object_ids']))

            empty = query_agent_citations(root, 'no supporting evidence', limit=10)

            self.assertEqual(empty['evidence'], [])
            self.assertIn('run_wikify_wikiize_or_add_citations', empty['next_actions'])

    def test_agent_related_returns_ranked_signal_explanations(self):
        from wikify.agent import query_agent_related

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _source_path, source, item = self._write_note_workspace(root)
            page = self._write_semantic_object_fixtures(root, source, item)

            result = query_agent_related(root, 'agent context', limit=5)

            self.assertEqual(result['schema_version'], 'wikify.related-query.v1')
            related = result['related']
            self.assertGreater(len(related), 0)
            self.assertEqual(
                [(entry['score'], entry['id']) for entry in related],
                sorted([(entry['score'], entry['id']) for entry in related], key=lambda item: (-item[0], item[1])),
            )
            signals = related[0]['signals']
            for key in [
                'direct_object_link',
                'graph_edge',
                'shared_source',
                'citation_overlap',
                'common_neighbor',
                'type_affinity',
                'text_match',
            ]:
                self.assertIn(key, signals)

            known = query_agent_related(root, page['id'], limit=5)

            self.assertGreater(len(known['matches']), 0)
            self.assertTrue(
                any(
                    rationale.get('signal') == 'direct_object_id_match'
                    for rationale in known['matches'][0]['rationale']
                )
            )


if __name__ == '__main__':
    unittest.main()
