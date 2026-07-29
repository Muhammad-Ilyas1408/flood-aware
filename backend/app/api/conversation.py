"""Conversation API endpoint."""

from fastapi import APIRouter, Depends, status

from backend.app.config.graph_dependencies import get_conversation_orchestrator
from backend.app.conversation.orchestrator import ConversationOrchestrator
from backend.app.schemas.conversation import ConversationRequest, ConversationResponse
from backend.app.schemas.errors import ErrorResponse

router = APIRouter(tags=["Conversation"])


@router.post(
    "/conversation",
    response_model=ConversationResponse,
    status_code=status.HTTP_200_OK,
    summary="Handle one grounded conversation turn",
    description=(
        "Execute or continue a flood-decision conversation turn and return "
        "the grounded decision."
    ),
    operation_id="postConversation",
    responses={
        status.HTTP_200_OK: {
            "description": "Grounded decision returned for the conversation turn."
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "The request failed validation.",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "The application could not complete the request.",
        },
    },
)
async def post_conversation(
    request: ConversationRequest,
    orchestrator: ConversationOrchestrator = Depends(get_conversation_orchestrator),
) -> ConversationResponse:
    """Handle one conversation turn and return its grounded public decision."""
    session_id, decision = await orchestrator.handle_turn(
        request.session_id, request.to_user_request()
    )
    return ConversationResponse.from_decision(session_id, decision)
