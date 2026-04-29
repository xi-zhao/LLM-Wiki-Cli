from dataclasses import dataclass, field


@dataclass(frozen=True)
class IngestRequest:
    root: str
    locator: str
    source_id: str | None = None
    adapter_name: str | None = None
    dry_run: bool = False
    write_raw: bool = True
    refresh_views: bool = True


@dataclass(frozen=True)
class IngestAsset:
    kind: str
    locator: str
    path: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class FetchedPayload:
    adapter: str
    original_locator: str
    canonical_locator: str
    html: str = ''
    text: str = ''
    metadata: dict = field(default_factory=dict)
    assets: list[IngestAsset] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class NormalizedDocument:
    item_id: str
    source_id: str | None
    adapter: str
    original_locator: str
    canonical_locator: str
    title: str
    body_text: str
    markdown: str
    captured_at: str
    published_at: str | None
    author: str | None
    raw_paths: dict
    assets: list[dict]
    warnings: list[dict]
    fingerprint: dict
    metadata: dict
