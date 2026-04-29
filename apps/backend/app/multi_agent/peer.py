"""Peer collaboration pattern - các agent truyền tin nhắn tuần tự (debate/review chain).

Kiến trúc:
  User message -> Agent A -> Agent B -> Agent C -> ... -> Tổng hợp kết quả
  Mỗi agent nhận output của agent trước đó làm context bổ sung.

Use cases:
  - Debate: các agent tranh luận quan điểm khác nhau
  - Review chain: agent viết -> agent review -> agent sửa
  - Pipeline: mỗi agent xử lý một bước khác nhau
"""

from __future__ import annotations

from typing import Any, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.executor import build_agent_tools
from app.llm.provider import build_llm_from_agent
from app.models.agent import Agent

# ─── State ─────────────────────────────────────────────────────────

class PeerState(TypedDict, total=False):
    """State cho peer collaboration graph.

    - messages: lịch sử hội thoại chung
    - agent_outputs: kết quả từng agent theo thứ tự {agent_name: output}
    - current_round: vòng lặp hiện tại (cho multi-round debate)
    """
    messages: list[BaseMessage]
    agent_outputs: dict[str, str]
    current_round: int


# ─── Builder ──────────────────────────────────────────────────────

async def build_peer_graph(
    agents: list[Agent],
    db: AsyncSession,
    rounds: int = 1,
    synthesis_prompt: str | None = None,
) -> Any:
    """Xây dựng LangGraph graph cho peer collaboration.

    Args:
        agents: Danh sách agent tham gia (thứ tự quan trọng)
        db: Database session
        rounds: Số vòng lặp (>1 cho debate multi-round)
        synthesis_prompt: Prompt tổng hợp kết quả cuối (tùy chọn).
                         Nếu None, trả kết quả agent cuối cùng.

    Returns:
        Compiled LangGraph graph
    """
    # Build LLMs và tools cho mỗi agent
    agent_llms: dict[str, Any] = {}
    agent_tools_map: dict[str, list] = {}
    for agent in agents:
        agent_llms[agent.name] = build_llm_from_agent(agent)
        agent_tools_map[agent.name] = await build_agent_tools(agent, db)

    graph = StateGraph(PeerState)

    # ── Tạo node cho mỗi agent ─────────────────────────────────

    for i, agent in enumerate(agents):
        _agent = agent
        _llm = agent_llms[agent.name]
        _tools = agent_tools_map[agent.name]
        _is_first = (i == 0)

        async def make_peer_node(
            state: PeerState,
            *,
            ag=_agent,
            llm=_llm,
            tools=_tools,
            is_first=_is_first,
        ) -> PeerState:
            """Node agent: nhận context từ agent trước, thực thi và trả kết quả."""
            peer_messages = []
            if ag.system_prompt:
                peer_messages.append(SystemMessage(content=ag.system_prompt))

            if is_first:
                # Agent đầu tiên: nhận trực tiếp user message
                peer_messages.extend(state["messages"])
            else:
                # Các agent sau: nhận user message + context từ agent trước
                peer_messages.append(state["messages"][0])  # User message gốc

                # Thêm output của các agent trước làm context
                agent_outputs = state.get("agent_outputs", {})
                if agent_outputs:
                    context = "\n\n".join(
                        f"[{name}]:\n{output}" for name, output in agent_outputs.items()
                    )
                    peer_messages.append(HumanMessage(
                        content=f"Phản hồi từ các agent trước:\n{context}\n\nHãy đưa ra quan điểm/xử lý của bạn."
                    ))

            # Thực thi agent
            if tools:
                from langgraph.prebuilt import create_react_agent
                agent_graph = create_react_agent(llm, tools)
                result = await agent_graph.ainvoke({"messages": peer_messages})
                final_messages = result.get("messages", [])
                response_content = final_messages[-1].content if final_messages else ""
            else:
                response = await llm.ainvoke(peer_messages)
                response_content = response.content

            # Lưu kết quả
            agent_outputs = state.get("agent_outputs", {})
            agent_outputs[ag.name] = response_content
            state["agent_outputs"] = agent_outputs
            state["messages"].append(
                AIMessage(content=f"[{ag.name}]: {response_content}")
            )

            return state

        graph.add_node(agent.name, make_peer_node)

    # ── Node tổng hợp (nếu có synthesis_prompt) ───────────────

    if synthesis_prompt:
        _synth_llm = agent_llms[agents[0].name]  # Dùng LLM của agent đầu tiên

        async def synthesis_node(state: PeerState) -> PeerState:
            """Tổng hợp kết quả từ tất cả agent thành câu trả lời cuối."""
            outputs = state.get("agent_outputs", {})
            context = "\n\n".join(
                f"[{name}]:\n{output}" for name, output in outputs.items()
            )

            messages = [
                SystemMessage(content=synthesis_prompt),
                HumanMessage(content=f"User hỏi: {state['messages'][0].content}\n\n"
                             f"Các phản hồi:\n{context}\n\nHãy tổng hợp."),
            ]

            response = await _synth_llm.ainvoke(messages)
            state["messages"].append(AIMessage(content=response.content))
            state["agent_outputs"]["_synthesis"] = response.content
            return state

        graph.add_node("synthesis", synthesis_node)

    # ── Edges: nối tuần tự ─────────────────────────────────────

    # Agent 1 -> Agent 2 -> ... -> Agent N
    for i in range(len(agents) - 1):
        graph.add_edge(agents[i].name, agents[i + 1].name)

    # Agent cuối -> synthesis (nếu có) hoặc END
    if synthesis_prompt:
        graph.add_edge(agents[-1].name, "synthesis")
        graph.add_edge("synthesis", END)
    else:
        graph.add_edge(agents[-1].name, END)

    graph.set_entry_point(agents[0].name)

    return graph.compile()


async def run_peer_collaboration(
    agents: list[Agent],
    user_message: str,
    db: AsyncSession,
    rounds: int = 1,
    synthesis_prompt: str | None = None,
) -> dict:
    """Chạy peer collaboration và trả về kết quả.

    Returns:
        {"response": str, "agent_outputs": dict}
    """
    graph = await build_peer_graph(agents, db, rounds, synthesis_prompt)

    initial_state: PeerState = {
        "messages": [HumanMessage(content=user_message)],
        "agent_outputs": {},
        "current_round": 0,
    }

    final_state = await graph.ainvoke(initial_state)

    # Lấy phản hồi cuối cùng
    agent_outputs = final_state.get("agent_outputs", {})
    if "_synthesis" in agent_outputs:
        response = agent_outputs["_synthesis"]
    else:
        # Lấy output agent cuối cùng
        messages = final_state.get("messages", [])
        response = messages[-1].content if messages else ""

    return {
        "response": response,
        "agent_outputs": {k: v for k, v in agent_outputs.items() if k != "_synthesis"},
    }
