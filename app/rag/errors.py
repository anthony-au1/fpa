class RagError(RuntimeError):
    """Base error for explicit RAG failures."""


class CorpusValidationError(RagError):
    pass


class IndexNotBuiltError(RagError):
    pass


class IndexCompatibilityError(RagError):
    pass


class RetrievalTimeoutError(RagError):
    pass
