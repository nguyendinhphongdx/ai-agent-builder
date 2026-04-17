from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.config import settings
from app.models.user import User
from app.notifications.schemas import SocketConnectionResponse
from app.notifications.service import create_socket_token

router = APIRouter(tags=["notifications"])


@router.get("/me/socket", response_model=SocketConnectionResponse)
async def get_socket_connection(
    current_user: User = Depends(get_current_user),
):
    """Get socket URL + short-lived token for WebSocket connection."""
    rooms = [f"user:{current_user.id}"]
    token = create_socket_token(str(current_user.id), rooms)
    return SocketConnectionResponse(
        url=settings.SOCKET_PUBLIC_URL,
        token=token,
    )
