from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.config import settings
from app.context import current_user_id
from app.notifications.schemas import SocketConnectionResponse
from app.notifications.service import create_socket_token

router = APIRouter(
    tags=["notifications"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/me/socket", response_model=SocketConnectionResponse)
async def get_socket_connection():
    """Get socket URL + short-lived token for WebSocket connection."""
    user_id = current_user_id()
    rooms = [f"user:{user_id}"]
    token = create_socket_token(str(user_id), rooms)
    return SocketConnectionResponse(
        url=settings.SOCKET_PUBLIC_URL,
        token=token,
    )
