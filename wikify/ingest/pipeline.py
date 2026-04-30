from dataclasses import replace
from pathlib import Path

from wikify.ingest.adapters import resolve_adapter
from wikify.ingest.artifacts import (
    INGEST_ITEM_SCHEMA_VERSION,
    INGEST_RUN_SCHEMA_VERSION,
    ingest_item_path,
    ingest_run_path,
    raw_item_dir,
    relative_to_root,
    source_item_from_normalized,
    unique_ingest_run_id,
    upsert_ingest_queue_entry,
    upsert_source_item,
    utc_now,
    validate_existing_control_artifacts,
    write_json_atomic,
    write_source_item_object,
    write_text_atomic,
)
from wikify.ingest.documents import FetchedPayload, IngestRequest, NormalizedDocument
from wikify.ingest.errors import IngestError
from wikify.workspace import load_workspace


def run_ingest(
    base: Path | str,
    locator: str,
    *,
    source_id: str | None = None,
    adapter_name: str | None = None,
    dry_run: bool = False,
    write_raw: bool = True,
    refresh_views: bool = True,
    fetch_payload: dict | None = None,
) -> dict:
    root = Path(base).expanduser().resolve()
    workspace = load_workspace(root)
    workspace_id = workspace['workspace']['workspace_id']
    adapter = resolve_adapter(locator, adapter_name=adapter_name)
    canonical_locator = adapter.canonicalize(locator)
    now = utc_now()
    run_id = unique_ingest_run_id(adapter.name, canonical_locator)

    if dry_run:
        item_id = _planned_item_id(adapter.name, canonical_locator)
        return {
            'schema_version': INGEST_RUN_SCHEMA_VERSION,
            'status': 'planned',
            'dry_run': True,
            'run': {
                'run_id': run_id,
                'workspace_id': workspace_id,
                'adapter': adapter.name,
                'source_id': source_id,
                'locator': locator,
                'canonical_locator': canonical_locator,
                'created_at': now,
                'refresh_views': refresh_views,
            },
            'item': {
                'item_id': item_id,
                'source_id': source_id or f'ingest:{adapter.name}',
                'adapter': adapter.name,
                'locator': canonical_locator,
                'status': 'planned',
            },
            'artifacts': {},
            'next_actions': [],
        }

    if not write_raw:
        raise IngestError(
            'Raw ingest document is required for source-backed wikiization',
            code='ingest_raw_required',
            details={'locator': locator, 'adapter': adapter.name},
        )

    validate_existing_control_artifacts(root, workspace_id, now)

    request = IngestRequest(
        root=str(root),
        locator=locator,
        source_id=source_id,
        adapter_name=adapter_name,
        dry_run=dry_run,
        write_raw=write_raw,
        refresh_views=refresh_views,
    )
    fetched = _fetched_payload(adapter.name, locator, canonical_locator, fetch_payload)
    if fetched is None:
        fetched = adapter.fetch(request)

    document = adapter.normalize(fetched, source_id=source_id)
    raw_paths = _write_raw_document(root, document)
    document = replace(document, raw_paths=raw_paths)
    item = source_item_from_normalized(document, status='new')

    upsert_source_item(root, workspace_id, item, now)
    queue_entry = upsert_ingest_queue_entry(root, workspace_id, item, now)
    source_item_object_path = write_source_item_object(root, item)
    item_record_path = _write_ingest_item_record(root, workspace_id, document, item, queue_entry, now)
    run_record_path = _write_ingest_run_record(
        root,
        workspace_id,
        run_id,
        request,
        document,
        item,
        queue_entry,
        refresh_views,
        now,
    )

    return {
        'schema_version': INGEST_RUN_SCHEMA_VERSION,
        'status': 'completed',
        'dry_run': False,
        'run': {
            'run_id': run_id,
            'workspace_id': workspace_id,
            'adapter': adapter.name,
            'source_id': source_id,
            'locator': locator,
            'canonical_locator': canonical_locator,
            'created_at': now,
            'refresh_views': refresh_views,
        },
        'item': item,
        'queue_entry': queue_entry,
        'artifacts': {
            'run': relative_to_root(root, run_record_path),
            'item': relative_to_root(root, item_record_path),
            'source_item_object': relative_to_root(root, source_item_object_path),
            'raw_document': raw_paths['document'],
        },
        'next_actions': [
            f'wikify wikiize --item {item["item_id"]}',
            'wikify views',
        ],
    }


def _planned_item_id(adapter_name: str, canonical_locator: str) -> str:
    from wikify.ingest.artifacts import ingest_item_id

    return ingest_item_id(adapter_name, canonical_locator)


def _fetched_payload(
    adapter_name: str,
    original_locator: str,
    canonical_locator: str,
    payload: dict | None,
) -> FetchedPayload | None:
    if payload is None:
        return None
    return FetchedPayload(
        adapter=adapter_name,
        original_locator=original_locator,
        canonical_locator=canonical_locator,
        html=payload.get('html') or '',
        text=payload.get('text') or '',
        metadata=dict(payload.get('metadata') or {}),
        warnings=list(payload.get('warnings') or []),
    )


def _write_raw_document(root: Path, document: NormalizedDocument) -> dict:
    directory = raw_item_dir(root, document.adapter, document.item_id)
    document_path = directory / 'document.md'
    text_path = directory / 'text.txt'
    metadata_path = directory / 'metadata.json'
    metadata = {
        'schema_version': 'wikify.raw-document-metadata.v1',
        'item_id': document.item_id,
        'source_id': document.source_id,
        'adapter': document.adapter,
        'original_locator': document.original_locator,
        'canonical_locator': document.canonical_locator,
        'title': document.title,
        'author': document.author,
        'published_at': document.published_at,
        'captured_at': document.captured_at,
        'fingerprint': dict(document.fingerprint or {}),
        'metadata': dict(document.metadata or {}),
        'assets': list(document.assets or []),
        'warnings': list(document.warnings or []),
    }

    write_text_atomic(document_path, document.markdown)
    write_text_atomic(text_path, document.body_text)
    write_json_atomic(metadata_path, metadata)
    return {
        'document': relative_to_root(root, document_path),
        'document_path': str(document_path),
        'text': relative_to_root(root, text_path),
        'text_path': str(text_path),
        'metadata': relative_to_root(root, metadata_path),
        'metadata_path': str(metadata_path),
    }


def _write_ingest_item_record(
    root: Path,
    workspace_id: str,
    document: NormalizedDocument,
    item: dict,
    queue_entry: dict,
    now: str,
) -> Path:
    path = ingest_item_path(root, document.item_id)
    write_json_atomic(path, {
        'schema_version': INGEST_ITEM_SCHEMA_VERSION,
        'workspace_id': workspace_id,
        'item_id': document.item_id,
        'adapter': document.adapter,
        'source_id': item.get('source_id'),
        'locator': document.canonical_locator,
        'status': item.get('status'),
        'source_item': item,
        'queue_entry': queue_entry,
        'raw_paths': dict(document.raw_paths or {}),
        'created_at': now,
        'updated_at': now,
    })
    return path


def _write_ingest_run_record(
    root: Path,
    workspace_id: str,
    run_id: str,
    request: IngestRequest,
    document: NormalizedDocument,
    item: dict,
    queue_entry: dict,
    refresh_views: bool,
    now: str,
) -> Path:
    path = ingest_run_path(root, run_id)
    write_json_atomic(path, {
        'schema_version': INGEST_RUN_SCHEMA_VERSION,
        'workspace_id': workspace_id,
        'run_id': run_id,
        'status': 'completed',
        'dry_run': False,
        'request': {
            'locator': request.locator,
            'source_id': request.source_id,
            'adapter_name': request.adapter_name,
            'write_raw': request.write_raw,
            'refresh_views': refresh_views,
        },
        'item_id': document.item_id,
        'source_item_id': item['item_id'],
        'queue_id': queue_entry['queue_id'],
        'artifacts': {
            'item': relative_to_root(root, ingest_item_path(root, document.item_id)),
            'raw_document': document.raw_paths.get('document'),
        },
        'created_at': now,
        'updated_at': now,
    })
    return path
