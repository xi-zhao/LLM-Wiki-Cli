class IngestError(ValueError):
    def __init__(
        self,
        message: str,
        code: str = 'ingest_failed',
        details: dict | None = None,
        retryable: bool = False,
    ):
        self.code = code
        self.details = details or {}
        self.retryable = retryable
        super().__init__(message)
