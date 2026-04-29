import tempfile
import unittest
from pathlib import Path


class ObjectModelTests(unittest.TestCase):
    def test_schema_versions_object_types_and_vocabularies(self):
        from wikify.objects import GRAPH_PROVENANCE_VALUES, OBJECT_TYPES, REVIEW_STATUSES, SCHEMA_VERSIONS

        self.assertEqual(
            SCHEMA_VERSIONS,
            {
                'object_index': 'wikify.object-index.v1',
                'wiki_page': 'wikify.wiki-page.v1',
                'topic': 'wikify.topic.v1',
                'project': 'wikify.project.v1',
                'person': 'wikify.person.v1',
                'decision': 'wikify.decision.v1',
                'timeline_entry': 'wikify.timeline-entry.v1',
                'citation': 'wikify.citation.v1',
                'graph_edge': 'wikify.graph-edge.v1',
                'context_pack': 'wikify.context-pack.v1',
                'object_validation': 'wikify.object-validation.v1',
            },
        )
        self.assertEqual(
            OBJECT_TYPES,
            {
                'source',
                'source_item',
                'wiki_page',
                'topic',
                'project',
                'person',
                'decision',
                'timeline_entry',
                'citation',
                'graph_edge',
                'context_pack',
            },
        )
        self.assertEqual(REVIEW_STATUSES, {'generated', 'needs_review', 'approved', 'rejected', 'stale'})
        self.assertEqual(GRAPH_PROVENANCE_VALUES, {'EXTRACTED', 'INFERRED', 'AMBIGUOUS'})

    def test_required_fields_include_wiki_page_contract(self):
        from wikify.objects import REQUIRED_FIELDS

        self.assertTrue(
            {
                'schema_version',
                'id',
                'type',
                'title',
                'summary',
                'body_path',
                'source_refs',
                'outbound_links',
                'backlinks',
                'created_at',
                'updated_at',
                'confidence',
                'review_status',
            }.issubset(REQUIRED_FIELDS['wiki_page']),
        )

    def test_stable_object_ids_are_deterministic_and_prefixed(self):
        from wikify.objects import stable_object_id

        first = stable_object_id('wiki_page', 'topics/Agent Loop.md')
        second = stable_object_id('wiki_page', 'topics/Agent Loop.md')
        other = stable_object_id('wiki_page', 'topics/Other.md')

        self.assertEqual(first, second)
        self.assertNotEqual(first, other)
        self.assertTrue(first.startswith('page_'))
        self.assertNotIn(' ', first)

        expected_prefixes = {
            'wiki_page': 'page_',
            'topic': 'topic_',
            'project': 'project_',
            'person': 'person_',
            'decision': 'decision_',
            'timeline_entry': 'timeline_',
            'citation': 'citation_',
            'graph_edge': 'edge_',
            'context_pack': 'ctx_',
        }
        for object_type, prefix in expected_prefixes.items():
            self.assertTrue(stable_object_id(object_type, 'example').startswith(prefix))

    def test_object_artifact_paths_and_legacy_scope_mapping(self):
        from wikify.objects import (
            legacy_scope_to_object_type,
            object_artifacts_dir,
            object_document_path,
            object_index_path,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            self.assertEqual(object_artifacts_dir(root), root / 'artifacts' / 'objects')
            self.assertEqual(object_index_path(root), root / 'artifacts' / 'objects' / 'object-index.json')
            self.assertEqual(
                object_document_path(root, 'wiki_page', 'page_abc'),
                root / 'artifacts' / 'objects' / 'wiki_pages' / 'page_abc.json',
            )

        self.assertEqual(legacy_scope_to_object_type('topics'), 'topic')
        self.assertEqual(legacy_scope_to_object_type('timelines'), 'timeline_entry')
        self.assertEqual(legacy_scope_to_object_type('briefs'), 'wiki_page')
        self.assertEqual(legacy_scope_to_object_type('parsed'), 'wiki_page')
        self.assertEqual(legacy_scope_to_object_type('sorted'), 'wiki_page')
        self.assertEqual(legacy_scope_to_object_type('sources'), 'source')

    def test_wiki_page_citation_and_graph_edge_constructors(self):
        from wikify.objects import make_citation_object, make_graph_edge_object, make_wiki_page_object

        page = make_wiki_page_object(
            object_id='page_intro',
            title='Intro',
            summary='Intro summary',
            body_path='topics/intro.md',
            source_refs=[{'source_id': 'src_1', 'item_id': 'item_1', 'confidence': 0.9}],
            outbound_links=['page_other'],
            backlinks=['page_back'],
            created_at='2026-04-29T00:00:00Z',
            updated_at='2026-04-29T00:00:00Z',
            confidence=0.8,
            review_status='generated',
            relative_path='topics/intro.md',
        )

        self.assertEqual(page['schema_version'], 'wikify.wiki-page.v1')
        self.assertEqual(page['id'], 'page_intro')
        self.assertEqual(page['type'], 'wiki_page')
        self.assertEqual(page['source_refs'][0]['source_id'], 'src_1')
        self.assertEqual(page['outbound_links'], ['page_other'])
        self.assertEqual(page['backlinks'], ['page_back'])
        self.assertIsInstance(page['confidence'], float)

        citation = make_citation_object(
            object_id='citation_intro',
            source_id='src_1',
            item_id='item_1',
            locator='sources/intro.md',
            span={'start_line': 1, 'end_line': 3},
            confidence=0.7,
        )
        self.assertEqual(citation['schema_version'], 'wikify.citation.v1')
        self.assertEqual(citation['type'], 'citation')
        self.assertEqual(citation['source_id'], 'src_1')
        self.assertEqual(citation['item_id'], 'item_1')
        self.assertEqual(citation['locator'], 'sources/intro.md')
        self.assertEqual(citation['span'], {'start_line': 1, 'end_line': 3})
        self.assertNotIn('raw_content', citation)

        edge = make_graph_edge_object(
            object_id='edge_intro',
            source='page_intro',
            target='page_other',
            edge_type='wikilink',
            provenance='EXTRACTED',
            confidence=1.0,
            source_path='topics/intro.md',
            line=7,
            label='links_to',
        )
        self.assertEqual(edge['schema_version'], 'wikify.graph-edge.v1')
        self.assertEqual(edge['type'], 'wikilink')
        for key in ['source', 'target', 'type', 'provenance', 'confidence', 'source_path', 'line', 'label']:
            self.assertIn(key, edge)

    def test_source_and_source_item_adapters(self):
        from wikify.objects import make_object_index, source_item_record_to_object, source_record_to_object

        source = {
            'schema_version': 'wikify.source-registry.v1',
            'source_id': 'src_1',
            'type': 'file',
            'locator': '/tmp/source.md',
            'title': 'Source',
        }
        item = {
            'schema_version': 'wikify.source-items.v1',
            'item_id': 'item_1',
            'source_id': 'src_1',
            'relative_path': 'source.md',
        }

        source_object = source_record_to_object(source)
        self.assertEqual(source_object['id'], 'src_1')
        self.assertEqual(source_object['type'], 'source')
        self.assertEqual(source_object['source'], source)

        item_object = source_item_record_to_object(item)
        self.assertEqual(item_object['id'], 'item_1')
        self.assertEqual(item_object['type'], 'source_item')
        self.assertEqual(item_object['source_item'], item)

        index = make_object_index('/tmp/wiki', [source_object, item_object], generated_at='2026-04-29T00:00:00Z')
        self.assertEqual(index['schema_version'], 'wikify.object-index.v1')
        self.assertEqual(index['summary']['object_count'], 2)
        self.assertEqual([entry['id'] for entry in index['objects']], ['src_1', 'item_1'])


if __name__ == '__main__':
    unittest.main()
