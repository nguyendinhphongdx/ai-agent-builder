"""Supervisor orchestrator pattern - một agent điều phối phân công task cho các worker agents.

Kiến trúc:
  Supervisor (LLM quyết định) -> chọn worker -> worker thực thi -> trả kết quả -> Supervisor đánh giá
  -> tiếp tục hoặc trả kết quả cuối cùng.

Sử dụng LangGraph StateGraph để quản lý luồng điều phối.
"""

from __future__ import annotations

from typing import Any, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.modules.integrations.llm.provider import build_llm_from_agent
from app.modules.studio.agents.executor import build_agent_tools

# ─── State ─────────────────────────────────────────────────────────

class SupervisorState(TypedDict, total=False):
    """State cho supervisor graph.

    - messages: lịch sử hội thoại tổng
    - next_worker: tên worker được chọn (hoặc "FINISH")
    - worker_results: kết quả từ từng worker {worker_name: result}
    - iterations: số vòng lặp đã chạy (chống loop vô hạn)
    """
    messages: list[BaseMessage]
    next_worker: str
    worker_results: dict[str, str]
    iterations: int


# ─── Supervisor Node ──────────────────────────────────────────────

SUPERVISOR_SYSTEM_PROMPT = """Bạn là supervisor điều phối một nhóm worker agents.
Các worker có sẵn: {worker_names}

Mô tả từng worker:
{worker_descriptions}

Với mỗi yêu cầu từ user, hãy quyết định giao cho worker nào xử lý.
Trả lời CHÍNH XÁC theo format:
ROUTE: <worker_name>

Nếu task đã hoàn thành hoặc bạn có đủ thông tin để trả lời, trả về:
ROUTE: FINISH

Sau đó đưa ra câu trả lời tổng hợp nếu chọn FINISH."""


def _parse_route(content: str, worker_names: list[str]) -> str:
    """Phân tích phản hồi supervisor để xác định worker tiếp theo."""
    for line in content.strip().split("\n"):
        line = line.strip()
        if line.upper().startswith("ROUTE:"):
            route = line.split(":", 1)[1].strip()
            if route.upper() == "FINISH":
                return "FINISH"
            # Tìm worker khớp tên (case-insensitive)
            for name in worker_names:
                if name.lower() == route.lower():
                    return name
    return "FINISH"


async def build_supervisor_graph(
    supervisor_agent: Agent,
    worker_agents: list[Agent],
    db: AsyncSession,
    max_iterations: int = 10,
) -> Any:
    """Xây dựng LangGraph graph cho supervisor pattern.

    Args:
        supervisor_agent: Agent đóng vai supervisor (quyết định routing)
        worker_agents: Danh sách agent worker
        db: Database session
        max_iterations: Giới hạn số vòng lặp tối đa

    Returns:
        Compiled LangGraph graph
    """
    supervisor_llm = build_llm_from_agent(supervisor_agent)
    worker_names = [a.name for a in worker_agents]
    worker_descriptions = "\n".join(
        f"- {a.name}: {a.description or a.system_prompt[:100]}"
        for a in worker_agents
    )

    # Build tools cho mỗi worker
    worker_tools: dict[str, list] = {}
    worker_llms: dict[str, Any] = {}
    for agent in worker_agents:
        worker_tools[agent.name] = await build_agent_tools(agent, db)
        worker_llms[agent.name] = build_llm_from_agent(agent)

    # ── Graph nodes ────────────────────────────────────────────

    async def supervisor_node(state: SupervisorState) -> SupervisorState:
        """Supervisor quyết định giao task cho worker nào."""
        system_prompt = SUPERVISOR_SYSTEM_PROMPT.format(
            worker_names=", ".join(worker_names),
            worker_descriptions=worker_descriptions,
        )

        messages = [SystemMessage(content=system_prompt)] + state["messages"]

        # Thêm kết quả worker trước đó (nếu có)
        if state.get("worker_results"):
            results_summary = "\n".join(
                f"[{name}]: {result[:500]}"
                for name, result in state["worker_results"].items()
            )
            messages.append(HumanMessage(
                content=f"Kết quả từ workers:\n{results_summary}\n\nHãy quyết định tiếp."
            ))

        response = await supervisor_llm.ainvoke(messages)
        route = _parse_route(response.content, worker_names)

        state["next_worker"] = route
        state["messages"].append(response)
        state["iterations"] = state.get("iterations", 0) + 1

        return state

    async def make_worker_node(agent: Agent):
        """Tạo node cho một worker agent."""
        name = agent.name
        llm = worker_llms[name]
        tools = worker_tools[name]

        async def worker_node(state: SupervisorState) -> SupervisorState:
            """Worker thực thi task và trả kết quả."""
            # Xây dựng prompt cho worker
            worker_messages = []
            if agent.system_prompt:
                worker_messages.append(SystemMessage(content=agent.system_prompt))

            # Lấy task từ tin nhắn cuối cùng
            last_msg = state["messages"][-1] if state["messages"] else None
            task = last_msg.content if last_msg else ""
            worker_messages.append(HumanMessage(content=task))

            # Thực thi worker (có hoặc không có tools)
            if tools:
                from langgraph.prebuilt import create_react_agent
                worker_graph = create_react_agent(llm, tools)
                result = await worker_graph.ainvoke({"messages": worker_messages})
                # Lấy phản hồi cuối cùng
                final_messages = result.get("messages", [])
                response_content = final_messages[-1].content if final_messages else ""
            else:
                response = await llm.ainvoke(worker_messages)
                response_content = response.content

            # Lưu kết quả worker
            worker_results = state.get("worker_results", {})
            worker_results[name] = response_content
            state["worker_results"] = worker_results
            state["messages"].append(
                AIMessage(content=f"[Worker {name}]: {response_content}")
            )

            return state

        return worker_node

    # ── Build graph ────────────────────────────────────────────

    graph = StateGraph(SupervisorState)

    # Thêm supervisor node
    graph.add_node("supervisor", supervisor_node)

    # Thêm worker nodes
    for agent in worker_agents:
        node_fn = await make_worker_node(agent)
        graph.add_node(agent.name, node_fn)

    # Routing: supervisor -> worker hoặc END
    def route_from_supervisor(state: SupervisorState) -> str:
        """Xác định node tiếp theo dựa trên quyết định của supervisor."""
        next_worker = state.get("next_worker", "FINISH")
        iterations = state.get("iterations", 0)

        # Chống loop vô hạn
        if iterations >= max_iterations:
            return END

        if next_worker == "FINISH":
            return END

        if next_worker in worker_names:
            return next_worker

        return END

    # Conditional edges từ supervisor
    path_map = {name: name for name in worker_names}
    path_map[END] = END
    graph.add_conditional_edges("supervisor", route_from_supervisor, path_map)

    # Mỗi worker xong -> quay lại supervisor
    for agent in worker_agents:
        graph.add_edge(agent.name, "supervisor")

    graph.set_entry_point("supervisor")

    return graph.compile()


async def run_supervisor(
    supervisor_agent: Agent,
    worker_agents: list[Agent],
    user_message: str,
    db: AsyncSession,
    max_iterations: int = 10,
) -> dict:
    """Chạy supervisor pattern và trả về kết quả.

    Returns:
        {"response": str, "worker_results": dict, "iterations": int}
    """
    graph = await build_supervisor_graph(
        supervisor_agent, worker_agents, db, max_iterations
    )

    initial_state: SupervisorState = {
        "messages": [HumanMessage(content=user_message)],
        "next_worker": "",
        "worker_results": {},
        "iterations": 0,
    }

    final_state = await graph.ainvoke(initial_state)

    # Lấy phản hồi cuối cùng từ supervisor
    messages = final_state.get("messages", [])
    response = messages[-1].content if messages else ""

    return {
        "response": response,
        "worker_results": final_state.get("worker_results", {}),
        "iterations": final_state.get("iterations", 0),
    }
