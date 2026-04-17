---
id: frontend-feature-tools
title: Tools Feature Module
domain: frontend
tags: [tools, crud, tool-types, testing, hooks]
related: [api-tool-endpoints, frontend-feature-agents-editor]
summary: Documents the tools feature types (including TOOL_TYPE_META), service, hooks, ToolListView, ToolCreateView, and ToolDetailView in the new page-based flow.
---

# Tools Feature

## Directory: `src/features/tools/`

## Types (`types/index.ts`)

### Tool

| Field            | Type              | Description                |
|------------------|-------------------|----------------------------|
| `id`             | `string`          | UUID                       |
| `name`           | `string`          | Display name               |
| `description`    | `string`          | Description (visible to LLM)|
| `tool_type`      | `ToolType`        | One of the 5 tool types    |
| `config`         | `Record<string, unknown>` | Type-specific config |
| `input_schema`   | `JsonSchema`      | JSON Schema for input      |
| `output_schema`  | `JsonSchema?`     | JSON Schema for output     |
| `is_active`      | `boolean`         | Whether tool is enabled    |
| `timeout_seconds`| `number`          | Execution timeout          |

### ToolType

`"http_request" | "code_exec" | "db_query" | "web_scrape" | "custom_function"`

### TOOL_TYPE_META

Static metadata map for each tool type:

| Type              | Label           | Icon       | Color   | Description                         |
|-------------------|-----------------|------------|---------|-------------------------------------|
| `http_request`    | HTTP Request    | `globe`    | blue    | Call an external API endpoint        |
| `code_exec`       | Code Executor   | `code`     | violet  | Execute Python code in a sandbox     |
| `db_query`        | Database Query  | `database` | emerald | Query a database with read-only access |
| `web_scrape`      | Web Scraper     | `globe`    | amber   | Extract content from web pages       |
| `custom_function` | Custom Function | `wrench`   | rose    | User-defined Python function         |

### ToolTestResult

`{ success: boolean, result: string?, error: string?, latency_ms: number }`

## Service (`services/toolService.ts`)

| Method   | HTTP Call                        | Returns          |
|----------|----------------------------------|------------------|
| `list`   | `GET /tools`                     | `Tool[]`         |
| `getById`| `GET /tools/${id}`               | `Tool`           |
| `create` | `POST /tools`                    | `Tool`           |
| `update` | `PUT /tools/${id}`               | `Tool`           |
| `delete` | `DELETE /tools/${id}`            | void             |
| `test`   | `POST /tools/${id}/test`         | `ToolTestResult` |

## Hooks (`hooks/useTools.ts`)

| Hook              | Type     | Behavior                                    |
|-------------------|----------|---------------------------------------------|
| `useTools()`      | Query    | Fetches tool list                           |
| `useTool(id)`     | Query    | Fetches single tool, `enabled: !!id`        |
| `useCreateTool()` | Mutation | Creates tool, invalidates list              |
| `useUpdateTool(id)` | Mutation | Updates tool, invalidates detail + list   |
| `useDeleteTool()` | Mutation | Deletes tool, invalidates list              |
| `useTestTool()`   | Mutation | Tests tool with `{ id, inputData }` param  |

## Routing

- `/tools`: Tool list page
- `/tools/new`: Dedicated create page
- `/tools/[toolId]`: Dedicated detail/edit/test page

## ToolListView (`views/ToolListView.tsx`)

List page at `/tools`:
- Toolbar with count and "New Tool" button linking to `/tools/new`
- Search + status/type filters for fast browsing
- Each tool rendered as a `ToolRow` with icon, name, type badge, and active/inactive state
- Click row navigates to `/tools/[toolId]`
- Per-row quick actions: toggle active, open detail page, delete
- Empty state with CTA to `/tools/new`

## ToolCreateView (`views/ToolCreateView.tsx`)

Dedicated page at `/tools/new`:
- Step-based UX on one page: choose tool type first, then edit details
- Full form fields: name, description, timeout, config JSON, input schema JSON
- Type-specific default config and default input schema are prefilled on type change
- Create success redirects to `/tools/[toolId]`

## ToolDetailView (`views/ToolDetailView.tsx`)

Dedicated page at `/tools/[toolId]`:
- Full-page editing (no sheet)
- Name/description/config/input-schema/timeout editable in-place (save on blur)
- Top actions: back to list, toggle active/inactive, delete tool
- Right panel for **Test Tool** with request input, execution state, success/fail, and latency
