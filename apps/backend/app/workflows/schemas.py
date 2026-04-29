"""Pydantic schemas cho Workflow CRUD và execution."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

# ─── Node & Edge schemas ───────────────────────────────────────────

class NodeConfig(BaseModel):
    """Cấu hình linh hoạt cho từng loại node, truyền qua JSONB."""
    # LLM node
    model_id: str | None = None          # "provider/model"
    credential_id: uuid.UUID | None = None
    system_prompt: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None

    # Tool node
    tool_id: str | None = None

    # Condition node
    condition_expression: str | None = None  # Biểu thức điều kiện (Python expression)
    branches: list[dict] | None = None       # [{"label": "yes", "handle": "true"}, ...]

    # Human-input node
    prompt_message: str | None = None  # Câu hỏi hiển thị cho user
    input_type: str | None = None      # "text", "select", "confirm"
    options: list[str] | None = None   # Lựa chọn cho input_type="select"

    model_config = {"extra": "allow"}  # Cho phép thêm trường tùy ý


class WorkflowNodeCreate(BaseModel):
    """Schema tạo node mới trong workflow."""
    id: uuid.UUID
    node_type: str  # "input", "output", "llm", "tool", "condition", "human_input"
    label: str | None = None
    config: dict = {}
    position_x: float = 0
    position_y: float = 0
    width: float | None = None
    height: float | None = None


class WorkflowNodeUpdate(BaseModel):
    """Schema cập nhật node."""
    label: str | None = None
    config: dict | None = None
    position_x: float | None = None
    position_y: float | None = None
    width: float | None = None
    height: float | None = None


class WorkflowNodeResponse(BaseModel):
    """Schema trả về thông tin node."""
    id: uuid.UUID
    workflow_id: uuid.UUID
    node_type: str
    label: str | None
    config: dict
    position_x: float
    position_y: float
    width: float | None
    height: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkflowEdgeCreate(BaseModel):
    """Schema tạo edge nối giữa hai node."""
    id: uuid.UUID
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    source_handle: str | None = None  # Handle/port trên node nguồn
    target_handle: str | None = None  # Handle/port trên node đích
    label: str | None = None
    style: dict = {}


class WorkflowEdgeResponse(BaseModel):
    """Schema trả về thông tin edge."""
    id: uuid.UUID
    workflow_id: uuid.UUID
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    source_handle: str | None
    target_handle: str | None
    label: str | None
    style: dict
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Workflow schemas ──────────────────────────────────────────────

class WorkflowCreate(BaseModel):
    """Schema tạo workflow mới."""
    name: str
    description: str | None = None
    agent_id: uuid.UUID | None = None


class WorkflowUpdate(BaseModel):
    """Schema cập nhật workflow (bao gồm lưu toàn bộ graph)."""
    name: str | None = None
    description: str | None = None
    agent_id: uuid.UUID | None = None
    is_active: bool | None = None
    viewport: dict | None = None
    # Lưu toàn bộ graph nodes + edges cùng lúc
    nodes: list[WorkflowNodeCreate] | None = None
    edges: list[WorkflowEdgeCreate] | None = None


class WorkflowResponse(BaseModel):
    """Schema trả về chi tiết workflow kèm nodes và edges."""
    id: uuid.UUID
    user_id: uuid.UUID
    agent_id: uuid.UUID | None
    name: str
    description: str | None
    version: int
    is_active: bool
    viewport: dict
    webhook_token: str
    nodes: list[WorkflowNodeResponse] = []
    edges: list[WorkflowEdgeResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkflowListResponse(BaseModel):
    """Schema trả về danh sách workflow (rút gọn)."""
    id: uuid.UUID
    name: str
    description: str | None
    agent_id: uuid.UUID | None
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Execution schemas ─────────────────────────────────────────────

class WorkflowExecuteRequest(BaseModel):
    """Schema yêu cầu chạy workflow."""
    input_data: dict  # Dữ liệu đầu vào cho node "input"
    conversation_id: uuid.UUID | None = None  # Liên kết với conversation (tùy chọn)


class NodeExecuteRequest(BaseModel):
    """Schema yêu cầu chạy đơn lẻ một node (NDV "Execute Step").

    `input_items` thay cho output của upstream node. Nếu rỗng thì node sẽ
    nhận list rỗng — phù hợp với nodes không phụ thuộc input (vd. webhook
    trigger, set-variable). `config_overrides` cho phép test config chưa save.
    """
    input_items: list[dict] = []
    config_overrides: dict | None = None


class NodeExecutionLog(BaseModel):
    """Log thực thi của một node.

    Field names mirror ``NodeExecution`` dataclass written by the runner —
    n8n-style item lists.
    """
    node_id: str
    node_type: str
    label: str | None = None
    status: str  # "running", "completed", "failed", "skipped"
    input_items: list[dict] | None = None
    output_items: list[dict] | None = None
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    tokens_used: int = 0


class WorkflowRunResponse(BaseModel):
    """Schema trả về kết quả chạy workflow."""
    id: uuid.UUID
    workflow_id: uuid.UUID
    user_id: uuid.UUID
    conversation_id: uuid.UUID | None
    status: str
    is_partial: bool = False
    input_data: dict
    # Workflow output follows n8n's item model: a list of item dicts. Kept as
    # `dict | list | None` so legacy runs that stored a single dict still load.
    output_data: dict | list | None
    error_message: str | None
    node_executions: list[dict]
    total_tokens: int
    total_cost: Decimal
    started_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}
