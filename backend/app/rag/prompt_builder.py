"""Provider-independent grounded prompt construction."""

from backend.app.rag.models import EvidenceContext


class PromptBuilder:
    """Build evidence-only prompts for government disaster knowledge questions."""

    SYSTEM_PROMPT = "You are Flood-Aware's Government Disaster Knowledge Engine. Answer only from supplied government evidence. If evidence is insufficient, say so. Cite document name and page for every factual claim."

    def build(self, question: str, context: EvidenceContext) -> tuple[str, str]:
        """Return system and user prompt strings without provider coupling."""

        return (
            self.SYSTEM_PROMPT,
            f"Question:\n{question}\n\nGovernment evidence:\n{context.text}",
        )
