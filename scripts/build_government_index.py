"""Offline deterministic builder for the Flood-Aware Government Knowledge Base."""

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.rag.embedding_service import OpenAIEmbeddingService
from backend.app.rag.government_loader import GovernmentLoader
from backend.app.rag.pdf_cleaner import PDFCleaner
from backend.app.rag.semantic_chunker import SemanticChunker
from backend.app.rag.settings import GovernmentKnowledgeSettings
from backend.app.rag.vector_store import ChromaVectorStore


def main() -> None:
    """Rebuild the persistent government-document vector index offline."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = GovernmentKnowledgeSettings()
    corpus = GovernmentLoader().load_corpus(settings.pdf_directory)
    cleaner = PDFCleaner()
    chunker = SemanticChunker(settings.semantic_chunk_max_characters)
    chunks = tuple(chunk for document in corpus.documents for chunk in chunker.chunk(cleaner.clean(document)))
    embeddings = OpenAIEmbeddingService(api_key=settings.openai_api_key, model=settings.embedding_model).embed(tuple(chunk.text for chunk in chunks))
    store = ChromaVectorStore(settings.chroma_directory, settings.collection_name)
    store.clear()
    store.index(chunks, embeddings)
    store.close()
    logging.info("Indexed %s documents and %s semantic chunks into %s.", len(corpus.documents), len(chunks), settings.chroma_directory)


if __name__ == "__main__":
    main()
