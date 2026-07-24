"""Conservative government-PDF cleanup that preserves paragraphs and lists."""

import re

from backend.app.rag.models import KnowledgeDocument, KnowledgePage


class PDFCleaner:
    """Remove repeated PDF noise while retaining meaningful document structure."""

    def clean(self, document: KnowledgeDocument) -> KnowledgeDocument:
        """Return a page-preserving cleaned document."""

        repeated = self._repeated_edge_lines(document)
        pages = tuple(KnowledgePage(page.page_number, self._clean(page.text, repeated)) for page in document.pages)
        return KnowledgeDocument(document.document_id, document.name, document.source_path, pages, document.metadata)

    @staticmethod
    def _repeated_edge_lines(document: KnowledgeDocument) -> set[str]:
        edges: dict[str, int] = {}
        for page in document.pages:
            lines = [line.strip() for line in page.text.splitlines() if line.strip()]
            for line in (lines[:2] + lines[-2:]):
                edges[line] = edges.get(line, 0) + 1
        return {line for line, count in edges.items() if count >= 2}

    @staticmethod
    def _clean(text: str, repeated: set[str]) -> str:
        lines = []
        for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            if line.strip() in repeated or re.fullmatch(r"\s*\d+\s*", line):
                continue
            lines.append(re.sub(r"[ \t]+", " ", line).rstrip())
        value = "\n".join(lines)
        value = re.sub(r"(?<!\n)\n(?!\n|\s*[-•\d])", " ", value)
        return re.sub(r"\n{3,}", "\n\n", value).strip()
