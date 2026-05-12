"""Pydantic schemas cho Multi-Agent API."""

import uuid

from pydantic import BaseModel


class MultiAgentRequest(BaseModel):
    """Schema yêu cầu chạy multi-agent."""
    message: str  # Tin nhắn user
    agent_ids: list[uuid.UUID]  # Danh sách agent tham gia
    max_iterations: int = 10  # Giới hạn vòng lặp (supervisor)


class SupervisorRequest(MultiAgentRequest):
    """Schema yêu cầu chạy supervisor pattern.

    agent_ids[0] = supervisor, agent_ids[1:] = workers
    """
    pass


class PeerRequest(MultiAgentRequest):
    """Schema yêu cầu chạy peer collaboration."""
    synthesis_prompt: str | None = None  # Prompt tổng hợp (tùy chọn)
    rounds: int = 1  # Số vòng debate


class AgentOutput(BaseModel):
    """Kết quả từ một agent."""
    agent_name: str
    output: str


class MultiAgentResponse(BaseModel):
    """Schema trả về kết quả multi-agent."""
    response: str  # Câu trả lời cuối cùng
    agent_outputs: dict[str, str]  # Kết quả từng agent
    pattern: str  # "supervisor" hoặc "peer"
    iterations: int | None = None  # Số vòng lặp (supervisor)
