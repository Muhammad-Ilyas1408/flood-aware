"""Government PDF ingestion with immutable, source-preserving records."""

from pathlib import Path

from backend.app.rag.exceptions import KnowledgeLoaderError
from backend.app.rag.models import GovernmentCorpus, KnowledgeDocument, KnowledgeMetadata, KnowledgePage


class GovernmentLoader:
    """Load authoritative government PDFs without interpreting their contents."""

    def load(self, source_path: str | Path) -> KnowledgeDocument:
        """Extract source metadata and page text from one PDF."""

        path = Path(source_path)
        if path.suffix.lower() != ".pdf" or not path.is_file():
            raise KnowledgeLoaderError(f"Government PDF is unavailable: {path}")
        try:
            import fitz

            with fitz.open(path) as pdf:
                pages = tuple(
                    KnowledgePage(number, page.get_text("text"))
                    for number, page in enumerate(pdf, start=1)
                )
                metadata = pdf.metadata or {}
        except Exception as error:
            raise KnowledgeLoaderError(f"Unable to load government PDF: {path}") from error
        return KnowledgeDocument(
            document_id=path.stem,
            name=path.name,
            source_path=path,
            pages=pages,
            metadata=KnowledgeMetadata(
                authority="Government of Pakistan / Government of Khyber Pakhtunkhwa",
                document_type=metadata.get("subject") or "Disaster management document",
            ),
        )

    def load_corpus(self, source_directory: str | Path) -> GovernmentCorpus:
        """Load every configured PDF in deterministic filename order."""

        directory = Path(source_directory)
        if not directory.is_dir():
            raise KnowledgeLoaderError(f"Government corpus directory is unavailable: {directory}")
        documents = tuple(self.load(path) for path in sorted(directory.glob("*.pdf")))
        return GovernmentCorpus(documents)
