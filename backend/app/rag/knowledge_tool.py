"""Production interface between future decision orchestration and government knowledge."""

from backend.app.rag.context_builder import ContextBuilder
from backend.app.rag.models import GroundedAnswer
from backend.app.rag.prompt_builder import PromptBuilder
from backend.app.rag.protocols import ResponseGenerator
from backend.app.rag.retriever import GovernmentRetriever

_NO_RELEVANT_GUIDANCE_TEXT = (
    "No sufficiently relevant government guidance was found for this question."
)


class KnowledgeTool:
    """Answer a question exclusively from retrieved government disaster evidence."""

    def __init__(
        self,
        retriever: GovernmentRetriever,
        context_builder: ContextBuilder,
        prompt_builder: PromptBuilder,
        generator: ResponseGenerator,
        score_threshold: float | None = None,
    ) -> None:
        self._retriever = retriever
        self._context_builder = context_builder
        self._prompt_builder = prompt_builder
        self._generator = generator
        self._score_threshold = score_threshold

    def answer(self, question: str, top_k: int = 5) -> GroundedAnswer:
        """Retrieve evidence, generate grounded text, and retain evidence citations.

        Returns an honest no-guidance answer without calling the generator if no
        retrieved chunk clears the configured relevance threshold, rather than
        grounding a response in weak or irrelevant evidence.
        """

        chunks = self._retriever.retrieve(
            question, top_k, score_threshold=self._score_threshold
        )
        if not chunks:
            return GroundedAnswer(_NO_RELEVANT_GUIDANCE_TEXT, ())
        context = self._context_builder.build(chunks)
        system, user = self._prompt_builder.build(question, context)
        return GroundedAnswer(
            self._generator.generate(system, user).strip(), context.citations
        )
