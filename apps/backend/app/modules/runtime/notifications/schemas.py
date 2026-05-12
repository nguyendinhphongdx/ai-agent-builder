from pydantic import BaseModel


class SocketConnectionResponse(BaseModel):
    url: str
    token: str
