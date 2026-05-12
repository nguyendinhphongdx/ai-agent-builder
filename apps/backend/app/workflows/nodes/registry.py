"""Executor registry — maps node_type strings to executor instances."""

from app.workflows.nodes.ai import AgentExecutor, LLMExecutor
from app.workflows.nodes.core import (
    CronTriggerExecutor,
    EndExecutor,
    NoteExecutor,
    StartExecutor,
    WebhookTriggerExecutor,
)
from app.workflows.nodes.data import (
    CodeExecutor,
    KnowledgeRetrievalExecutor,
    SetVariableExecutor,
    TemplateExecutor,
)
from app.workflows.nodes.integration import HTTPRequestExecutor, ToolExecutor
from app.workflows.nodes.logic import (
    ConditionExecutor,
    DelayExecutor,
    FilterExecutor,
    HumanInputExecutor,
    LoopExecutor,
    MergeExecutor,
    SubWorkflowExecutor,
    SwitchExecutor,
)

EXECUTORS: dict = {
    # Core
    "start": StartExecutor(),
    "input": StartExecutor(),
    "end": EndExecutor(),
    "output": EndExecutor(),
    "note": NoteExecutor(),
    # Triggers
    "webhook_trigger": WebhookTriggerExecutor(),
    "cron_trigger": CronTriggerExecutor(),
    # AI
    "llm": LLMExecutor(),
    "agent": AgentExecutor(),
    # Integration
    "tool": ToolExecutor(),
    "http_request": HTTPRequestExecutor(),
    # Logic
    "condition": ConditionExecutor(),
    "switch": SwitchExecutor(),
    "filter": FilterExecutor(),
    "merge": MergeExecutor(),
    "loop": LoopExecutor(),
    "delay": DelayExecutor(),
    "human_input": HumanInputExecutor(),
    "sub_workflow": SubWorkflowExecutor(),
    # Data
    "template": TemplateExecutor(),
    "set_variable": SetVariableExecutor(),
    "code": CodeExecutor(),
    "knowledge_retrieval": KnowledgeRetrievalExecutor(),
}


def get_executor(node_type: str):
    """Return the executor for *node_type*, or raise KeyError if unknown."""
    executor = EXECUTORS.get(node_type)
    if executor is None:
        raise KeyError(f"No executor registered for node_type '{node_type}'")
    return executor
