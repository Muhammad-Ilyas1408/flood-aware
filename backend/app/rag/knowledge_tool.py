"""Production interface between future decision orchestration and government knowledge."""

from backend.app.rag.context_builder import ContextBuilder
from backend.app.rag.models import GroundedAnswer
from backend.app.rag.prompt_builder import PromptBuilder
from backend.app.rag.protocols import ResponseGenerator
from backend.app.rag.retriever import GovernmentRetriever


class KnowledgeTool:
    """Answer a question exclusively from retrieved government disaster evidence."""

    def __init__(
        self,
        retriever: GovernmentRetriever,
        context_builder: ContextBuilder,
        prompt_builder: PromptBuilder,
        generator: ResponseGenerator,
    ) -> None:
        self._retriever = retriever
        self._context_builder = context_builder
        self._prompt_builder = prompt_builder
        self._generator = generator

    def answer(self, question: str, top_k: int = 5) -> GroundedAnswer:
        """Retrieve evidence, generate grounded text, and retain evidence citations."""

        context = self._context_builder.build(self._retriever.retrieve(question, top_k))
        system, user = self._prompt_builder.build(question, context)
        return GroundedAnswer(
            self._generator.generate(system, user).strip(), context.citations
        )
