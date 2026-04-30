from typing import Protocol
from urllib.parse import urlsplit

from wikify.ingest.documents import FetchedPayload, IngestRequest, NormalizedDocument
from wikify.ingest.errors import IngestError
from wikify.ingest.wechat import WeChatUrlAdapter


class IngestAdapter(Protocol):
    name: str

    def can_handle(self, locator: str, source=None) -> bool:
        ...

    def canonicalize(self, locator: str) -> str:
        ...

    def fetch(self, request: IngestRequest) -> FetchedPayload:
        ...

    def normalize(self, payload: FetchedPayload, source_id: str | None = None) -> NormalizedDocument:
        ...


_ADAPTERS: tuple[IngestAdapter, ...] = (
    WeChatUrlAdapter(),
)


def resolve_adapter(locator: str, source=None, adapter_name: str | None = None) -> IngestAdapter:
    if adapter_name:
        for adapter in _ADAPTERS:
            if adapter.name == adapter_name:
                if not adapter.can_handle(locator, source=source):
                    raise IngestError(
                        f'Ingest adapter cannot handle locator: {adapter_name}',
                        code='ingest_adapter_not_found',
                        details={
                            'adapter': adapter_name,
                            'locator': locator,
                        },
                    )
                return adapter
        raise IngestError(
            f'Ingest adapter not found: {adapter_name}',
            code='ingest_adapter_not_found',
            details={'adapter': adapter_name},
        )

    for adapter in _ADAPTERS:
        if adapter.can_handle(locator, source=source):
            return adapter

    parsed = urlsplit(locator.strip())
    raise IngestError(
        f'No ingest adapter found for locator: {locator}',
        code='ingest_adapter_not_found',
        details={
            'locator': locator,
            'scheme': parsed.scheme,
            'host': parsed.netloc,
        },
    )
