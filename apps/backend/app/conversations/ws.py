import time
import uuid

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.executor import execute_agent_stream
from app.agents.service import get_agent
from app.api_keys.service import get_plaintext_key_for_provider
from app.conversations.service import get_conversation, get_messages, save_message


async def chat_websocket(
    ws: WebSocket,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
):
    """Handle WebSocket chat with LangGraph agent streaming."""
    await ws.accept()

    try:
        conv = await get_conversation(db, conversation_id, user_id)
        if not conv:
            await ws.send_json({"type": "error", "message": "Conversation not found"})
            await ws.close()
            return

        agent = await get_agent(db, conv.agent_id, user_id)
        if not agent:
            await ws.send_json({"type": "error", "message": "Agent not found"})
            await ws.close()
            return

        # Resolve user's API key for this agent's provider
        api_key = await get_plaintext_key_for_provider(db, user_id, agent.llm_provider)

        while True:
            data = await ws.receive_json()
            user_content = data.get("content", "")
            if not user_content:
                continue

            await save_message(db, conversation_id, role="user", content=user_content)
            await db.commit()

            start_time = time.time()

            try:
                # Load conversation history
                history = await get_messages(db, conversation_id, limit=50)

                # Stream agent response via LangGraph
                full_response = ""
                async for event in execute_agent_stream(agent, history, db, api_key=api_key):
                    event_dict = event.to_dict()

                    if event.type == "token":
                        full_response += event_dict.get("content", "")
                        await ws.send_json(event_dict)
                    elif event.type in ("tool_start", "tool_end"):
                        await ws.send_json(event_dict)
                    elif event.type == "done":
                        pass  # Handle below

                latency_ms = int((time.time() - start_time) * 1000)

                # Save assistant response
                if full_response:
                    await save_message(
                        db,
                        conversation_id,
                        role="assistant",
                        content=full_response,
                        llm_model=agent.llm_model,
                        latency_ms=latency_ms,
                    )
                    await db.commit()

                await ws.send_json({"type": "done"})

            except Exception as e:
                await ws.send_json({"type": "error", "message": str(e)})

    except WebSocketDisconnect:
        pass
