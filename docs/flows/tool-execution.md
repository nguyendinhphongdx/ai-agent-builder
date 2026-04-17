---
id: flows-tool-execution
title: Tool Execution Flow
domain: flows
tags: [tools, execution, registry, langchain, structured-tool]
related: [api-tool-endpoints, frontend-feature-tools, flows-chat-with-agent]
summary: End-to-end flow from agent deciding to call a tool through registry.build(), execution, and result return to the LLM.
---

# Tool Execution Flow

## Overview

During a chat conversation, the LLM decides to use a tool. The tool registry builds a callable LangChain StructuredTool from the DB definition, executes it, and returns the result to the LLM for response synthesis.

## Step-by-Step

### 1. Agent Decides to Use Tool

During `execute_agent_stream()`, the LangGraph ReAct agent's LLM output includes a tool call. LangGraph's `create_react_agent` automatically routes to tool execution.

### 2. Build Agent Tools

`build_agent_tools(agent, db)` prepares all callable tools:

**Custom tools** (from `agent.tools`):
```python
tools = tool_registry.build_many(agent.tools)  # only active tools
```

**Knowledge base tool** (if `agent.knowledge_bases` exists):
- Creates a `search_knowledge_base` tool function
- Calls `KnowledgeRetriever.retrieve(query, kb_ids)` for pgvector similarity search
- Returns concatenated chunk contents

### 3. Tool Registry Builds StructuredTool

`tool_registry.build(tool_def)` dispatches to the appropriate builder:

| tool_type     | Builder                  | Execution Method                 |
|---------------|--------------------------|----------------------------------|
| `http_request`| `HTTPRequestToolBuilder` | httpx async HTTP request         |
| `code_exec`   | `CodeExecToolBuilder`    | subprocess Python execution      |
| `db_query`    | `DBQueryToolBuilder`     | asyncpg SELECT-only query        |
| `web_scrape`  | `WebScrapeToolBuilder`   | httpx GET + text extraction      |

Each builder:

1. Reads `config` from the tool definition (URL, method, headers, code template, etc.)
2. Converts `input_schema` JSON Schema to a Pydantic model via `json_schema_to_pydantic()`
3. Creates `StructuredTool.from_function()` with the async execution function and generated args schema

### 4. Input Schema Conversion

`json_schema_to_pydantic(schema)`:
- Maps JSON Schema types to Python types: string->str, integer->int, number->float, etc.
- Handles required vs optional fields (optional get `None` default)
- Creates a dynamic Pydantic model named `DynamicToolInput`

### 5. Tool Executes

Each tool type has specific execution logic:

**HTTP Request:**
- Substitutes `{param}` placeholders in URL and body template with input values
- Sends request via httpx with configured method, headers, and timeout
- Returns response text (truncated to 4000 chars)

**Code Executor:**
- Substitutes placeholders in code template
- Writes to temp `.py` file
- Runs via `subprocess.run()` with timeout
- Returns stdout or stderr (truncated to 4000 chars)

**Database Query:**
- Security check: only SELECT allowed; blocks INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, GRANT, REVOKE
- Connects via asyncpg, executes query, returns JSON-serialized rows (max `max_rows`)

**Web Scraper:**
- Substitutes URL template placeholders
- Fetches via httpx GET
- Returns text content (truncated to `max_length`, default 5000)

### 6. Result Returned to LLM

LangGraph receives the tool result and:
1. Emits `tool_end` event (streamed to client)
2. Passes result back to the LLM as a `ToolMessage`
3. LLM generates a final response incorporating the tool result
4. Response tokens stream to the client

### 7. Testing Tools Independently

Via `POST /api/tools/{id}/test`:
1. `tool_registry.build(tool)` creates the StructuredTool
2. `await lc_tool.ainvoke(input_data)` executes it
3. Returns `{ success, result/error, latency_ms }`

## Security Considerations

- DB queries restricted to SELECT only (keyword blocklist)
- Code execution via subprocess with timeout
- HTTP requests respect tool `timeout_seconds`
- Tool results truncated to prevent context overflow
