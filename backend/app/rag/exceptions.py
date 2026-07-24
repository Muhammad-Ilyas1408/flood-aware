"""Domain exceptions for the PDF knowledge-document infrastructure."""


class KnowledgeError(Exception):
    """Base exception for knowledge-document infrastructure failures."""


class KnowledgeLoaderError(KnowledgeError):
    """Raised when a PDF knowledge document cannot be loaded."""


class KnowledgeParserError(KnowledgeError):
    """Raised when a knowledge document cannot be normalized safely."""


class KnowledgeDocumentError(KnowledgeError):
    """Raised when a knowledge-document model is structurally invalid."""


class EmbeddingProviderError(KnowledgeError):
    """Raised when an embedding infrastructure provider cannot complete its work."""


class VectorStoreError(KnowledgeError):
    """Raised when a vector-store infrastructure operation cannot complete."""


class RetrieverError(KnowledgeError):
    """Raised when retrieval infrastructure cannot return canonical chunks."""


class AIRuntimeError(KnowledgeError):
    """Raised when an AI runtime cannot generate a response safely."""
