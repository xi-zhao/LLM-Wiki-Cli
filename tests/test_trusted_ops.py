import json
import tempfile
import unittest
from pathlib import Path


class TrustedOperationTests(unittest.TestCase):
    def test_begin_complete_and_rollback_restore_modified_deleted_and_created_files(self):
        from wikify.trusted_ops import begin_trusted_operation, complete_trusted_operation, rollback_trusted_operation

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / 'wiki' / 'pages').mkdir(parents=True)
            modified = root / 'wiki' / 'pages' / 'modified.md'
            deleted = root / 'wiki' / 'pages' / 'deleted.md'
            created = root / 'wiki' / 'pages' / 'created.md'
            modified.write_text('before modified\n', encoding='utf-8')
            deleted.write_text('before deleted\n', encoding='utf-8')

            begun = begin_trusted_operation(
                root,
                paths=[
                    'wiki/pages/modified.md',
                    'wiki/pages/deleted.md',
                    'wiki/pages/created.md',
                ],
                reason='merge imported article into existing wiki pages',
            )

            operation_path = begun['artifacts']['operation']
            self.assertEqual(begun['schema_version'], 'wikify.trusted-operation.v1')
            self.assertEqual(begun['status'], 'begun')
            self.assertEqual(begun['rollback']['status'], 'pending_completion')
            self.assertTrue(Path(operation_path).exists())
            record = json.loads(Path(operation_path).read_text(encoding='utf-8'))
            snapshots = {snapshot['path']: snapshot for snapshot in record['snapshots']}
            self.assertTrue(snapshots['wiki/pages/modified.md']['before']['exists'])
            self.assertTrue(snapshots['wiki/pages/deleted.md']['before']['exists'])
            self.assertFalse(snapshots['wiki/pages/created.md']['before']['exists'])

            modified.write_text('after modified\n', encoding='utf-8')
            deleted.unlink()
            created.write_text('new file\n', encoding='utf-8')

            completed = complete_trusted_operation(root, operation_path)
            self.assertEqual(completed['status'], 'completed')
            self.assertEqual(completed['rollback']['status'], 'available')
            after = {snapshot['path']: snapshot for snapshot in completed['after_snapshots']}
            self.assertTrue(after['wiki/pages/modified.md']['after']['exists'])
            self.assertFalse(after['wiki/pages/deleted.md']['after']['exists'])
            self.assertTrue(after['wiki/pages/created.md']['after']['exists'])

            dry_run = rollback_trusted_operation(root, operation_path, dry_run=True)
            self.assertEqual(dry_run['status'], 'dry_run')
            self.assertEqual(modified.read_text(encoding='utf-8'), 'after modified\n')
            self.assertFalse(deleted.exists())
            self.assertTrue(created.exists())

            rolled_back = rollback_trusted_operation(root, operation_path)
            self.assertEqual(rolled_back['status'], 'rolled_back')
            self.assertEqual(modified.read_text(encoding='utf-8'), 'before modified\n')
            self.assertEqual(deleted.read_text(encoding='utf-8'), 'before deleted\n')
            self.assertFalse(created.exists())

            final_record = json.loads(Path(operation_path).read_text(encoding='utf-8'))
            self.assertEqual(final_record['status'], 'rolled_back')
            self.assertEqual(final_record['rollback']['status'], 'completed')

    def test_rollback_rejects_drifted_content(self):
        from wikify.trusted_ops import (
            TrustedOperationError,
            begin_trusted_operation,
            complete_trusted_operation,
            rollback_trusted_operation,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / 'wiki' / 'pages' / 'page.md'
            target.parent.mkdir(parents=True)
            target.write_text('before\n', encoding='utf-8')
            begun = begin_trusted_operation(root, paths=['wiki/pages/page.md'], reason='rewrite page')
            target.write_text('after\n', encoding='utf-8')
            complete_trusted_operation(root, begun['artifacts']['operation'])
            target.write_text('drifted\n', encoding='utf-8')

            with self.assertRaises(TrustedOperationError) as raised:
                rollback_trusted_operation(root, begun['artifacts']['operation'])

            self.assertEqual(raised.exception.code, 'trusted_operation_rollback_hash_mismatch')
            self.assertEqual(target.read_text(encoding='utf-8'), 'drifted\n')

    def test_begin_rejects_unsafe_paths(self):
        from wikify.trusted_ops import TrustedOperationError, begin_trusted_operation

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            with self.assertRaises(TrustedOperationError) as raised:
                begin_trusted_operation(root, paths=['../outside.md'], reason='bad path')

            self.assertEqual(raised.exception.code, 'trusted_operation_path_invalid')

    def test_begin_dry_run_writes_no_record(self):
        from wikify.trusted_ops import begin_trusted_operation

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / 'wiki' / 'pages' / 'page.md'
            target.parent.mkdir(parents=True)
            target.write_text('before\n', encoding='utf-8')

            result = begin_trusted_operation(root, paths=['wiki/pages/page.md'], reason='rewrite page', dry_run=True)

            self.assertEqual(result['status'], 'dry_run')
            self.assertTrue(result['dry_run'])
            self.assertFalse((root / '.wikify' / 'trusted-operations').exists())

    def test_repeated_begin_uses_distinct_operation_records(self):
        from wikify.trusted_ops import begin_trusted_operation

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / 'wiki' / 'pages' / 'page.md'
            target.parent.mkdir(parents=True)
            target.write_text('before\n', encoding='utf-8')

            first = begin_trusted_operation(root, paths=['wiki/pages/page.md'], reason='rewrite page')
            second = begin_trusted_operation(root, paths=['wiki/pages/page.md'], reason='rewrite page')

            self.assertNotEqual(first['operation_id'], second['operation_id'])
            self.assertNotEqual(first['artifacts']['operation'], second['artifacts']['operation'])
            self.assertTrue(Path(first['artifacts']['operation']).exists())
            self.assertTrue(Path(second['artifacts']['operation']).exists())
