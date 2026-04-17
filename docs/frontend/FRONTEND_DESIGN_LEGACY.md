# Frontend Architecture Design

## Tech Stack
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript (strict mode)
- **Styling**: Tailwind CSS + shadcn/ui
- **State Management**: Zustand (client state)
- **Data Fetching**: TanStack React Query (server state)
- **Form**: React Hook Form + Zod validation
- **Workflow Editor**: React Flow
- **Icons**: Lucide React
- **HTTP Client**: Axios

## Architecture Principles

### 1. Thin App Router
Route files (`page.tsx`, `layout.tsx`) chỉ làm 2 việc:
- SEO metadata (generateMetadata)
- Import và render View component từ feature

```tsx
// app/(dashboard)/agents/page.tsx -- THIN, chỉ có metadata + View
import { Metadata } from "next";
import { AgentListView } from "@/features/agents/views/AgentListView";

export const metadata: Metadata = {
  title: "Agents | AI Agent Builder",
  description: "Manage your AI agents",
};

export default function AgentsPage() {
  return <AgentListView />;
}
```

### 2. Feature-Based Architecture
Mỗi feature là 1 module độc lập, chứa toàn bộ logic liên quan.

### 3. Server vs Client Boundary
- `page.tsx` / `layout.tsx` = Server Component (SEO, metadata)
- Views và Components bên trong features = Client Component (`"use client"`)
- TanStack Query quản lý server state, Zustand chỉ cho UI state

---

## Folder Structure

```
frontend/
├── public/
│   └── images/
├── src/
│   ├── app/                              # THIN App Router - chỉ routing + metadata
│   │   ├── layout.tsx                    # Root layout (providers, fonts)
│   │   ├── (auth)/
│   │   │   ├── layout.tsx                # Auth layout (centered card)
│   │   │   ├── login/page.tsx
│   │   │   └── register/page.tsx
│   │   ├── (dashboard)/
│   │   │   ├── layout.tsx                # Dashboard layout (sidebar + header)
│   │   │   ├── page.tsx                  # Dashboard home
│   │   │   ├── agents/
│   │   │   │   ├── page.tsx              # Agent list
│   │   │   │   ├── new/page.tsx          # Create agent
│   │   │   │   └── [id]/
│   │   │   │       ├── page.tsx          # Agent detail/config
│   │   │   │       └── chat/page.tsx     # Chat with agent
│   │   │   ├── tools/
│   │   │   │   ├── page.tsx
│   │   │   │   └── [id]/page.tsx
│   │   │   ├── knowledge/
│   │   │   │   ├── page.tsx
│   │   │   │   └── [id]/page.tsx
│   │   │   └── workflows/
│   │   │       ├── page.tsx
│   │   │       └── [id]/page.tsx         # Visual workflow editor
│   │   └── api/                          # Next.js API routes (optional, proxy)
│   │
│   ├── features/                         # Feature modules
│   │   ├── auth/
│   │   │   ├── views/
│   │   │   │   ├── LoginView.tsx
│   │   │   │   └── RegisterView.tsx
│   │   │   ├── components/
│   │   │   │   ├── LoginForm.tsx
│   │   │   │   └── RegisterForm.tsx
│   │   │   ├── hooks/
│   │   │   │   └── useAuth.ts
│   │   │   ├── services/
│   │   │   │   └── authService.ts
│   │   │   ├── stores/
│   │   │   │   └── authStore.ts
│   │   │   ├── types/
│   │   │   │   └── index.ts
│   │   │   └── index.ts                  # Public API barrel export
│   │   │
│   │   ├── agents/
│   │   │   ├── views/
│   │   │   │   ├── AgentListView.tsx
│   │   │   │   ├── AgentCreateView.tsx
│   │   │   │   ├── AgentDetailView.tsx
│   │   │   │   └── AgentChatView.tsx
│   │   │   ├── components/
│   │   │   │   ├── AgentCard.tsx
│   │   │   │   ├── AgentForm.tsx
│   │   │   │   ├── AgentToolPicker.tsx
│   │   │   │   ├── AgentKBPicker.tsx
│   │   │   │   ├── LLMConfigPanel.tsx
│   │   │   │   └── SystemPromptEditor.tsx
│   │   │   ├── hooks/
│   │   │   │   ├── useAgents.ts          # TanStack Query hooks
│   │   │   │   ├── useAgent.ts
│   │   │   │   └── useAgentMutations.ts
│   │   │   ├── services/
│   │   │   │   └── agentService.ts       # Axios API calls
│   │   │   ├── types/
│   │   │   │   └── index.ts
│   │   │   └── index.ts
│   │   │
│   │   ├── tools/
│   │   │   ├── views/
│   │   │   │   ├── ToolListView.tsx
│   │   │   │   └── ToolDetailView.tsx
│   │   │   ├── components/
│   │   │   │   ├── ToolCard.tsx
│   │   │   │   ├── ToolForm.tsx
│   │   │   │   ├── ToolTestPanel.tsx
│   │   │   │   ├── config-forms/         # Per tool_type config forms
│   │   │   │   │   ├── HttpRequestForm.tsx
│   │   │   │   │   ├── CodeExecForm.tsx
│   │   │   │   │   ├── DbQueryForm.tsx
│   │   │   │   │   └── WebScrapeForm.tsx
│   │   │   │   └── InputSchemaEditor.tsx  # JSON Schema builder UI
│   │   │   ├── hooks/
│   │   │   │   ├── useTools.ts
│   │   │   │   └── useToolMutations.ts
│   │   │   ├── services/
│   │   │   │   └── toolService.ts
│   │   │   ├── types/
│   │   │   │   └── index.ts
│   │   │   └── index.ts
│   │   │
│   │   ├── knowledge/
│   │   │   ├── views/
│   │   │   │   ├── KBListView.tsx
│   │   │   │   └── KBDetailView.tsx
│   │   │   ├── components/
│   │   │   │   ├── KBCard.tsx
│   │   │   │   ├── KBForm.tsx
│   │   │   │   ├── FileUploadZone.tsx     # Drag & drop upload
│   │   │   │   ├── DocumentList.tsx
│   │   │   │   ├── DocumentStatus.tsx     # Processing status badge
│   │   │   │   └── RetrievalTestPanel.tsx # Test query against KB
│   │   │   ├── hooks/
│   │   │   │   ├── useKnowledgeBases.ts
│   │   │   │   ├── useDocuments.ts
│   │   │   │   └── useFileUpload.ts
│   │   │   ├── services/
│   │   │   │   └── knowledgeService.ts
│   │   │   ├── types/
│   │   │   │   └── index.ts
│   │   │   └── index.ts
│   │   │
│   │   ├── workflows/
│   │   │   ├── views/
│   │   │   │   ├── WorkflowListView.tsx
│   │   │   │   └── WorkflowEditorView.tsx
│   │   │   ├── components/
│   │   │   │   ├── Canvas.tsx             # React Flow wrapper
│   │   │   │   ├── NodePalette.tsx        # Sidebar danh sách node types
│   │   │   │   ├── NodeInspector.tsx      # Config panel for selected node
│   │   │   │   ├── WorkflowToolbar.tsx    # Save, Run, Zoom controls
│   │   │   │   ├── RunStatusPanel.tsx     # Execution progress
│   │   │   │   ├── custom-nodes/          # React Flow custom node components
│   │   │   │   │   ├── LLMNode.tsx
│   │   │   │   │   ├── ToolNode.tsx
│   │   │   │   │   ├── ConditionNode.tsx
│   │   │   │   │   ├── HumanInputNode.tsx
│   │   │   │   │   ├── StartNode.tsx
│   │   │   │   │   └── EndNode.tsx
│   │   │   │   └── custom-edges/
│   │   │   │       └── ConditionalEdge.tsx
│   │   │   ├── hooks/
│   │   │   │   ├── useWorkflows.ts
│   │   │   │   ├── useWorkflowEditor.ts   # Canvas state, drag-drop logic
│   │   │   │   └── useWorkflowExecution.ts
│   │   │   ├── services/
│   │   │   │   └── workflowService.ts
│   │   │   ├── stores/
│   │   │   │   └── workflowEditorStore.ts # Zustand: canvas state, selected node
│   │   │   ├── types/
│   │   │   │   └── index.ts
│   │   │   └── index.ts
│   │   │
│   │   ├── chat/
│   │   │   ├── views/
│   │   │   │   └── ChatView.tsx
│   │   │   ├── components/
│   │   │   │   ├── ChatWindow.tsx
│   │   │   │   ├── MessageList.tsx
│   │   │   │   ├── MessageBubble.tsx
│   │   │   │   ├── StreamingMessage.tsx   # Typewriter effect
│   │   │   │   ├── ToolCallCard.tsx       # Tool execution display
│   │   │   │   ├── ChatInput.tsx          # Input + send button
│   │   │   │   └── ConversationSidebar.tsx
│   │   │   ├── hooks/
│   │   │   │   ├── useChat.ts             # WebSocket chat logic
│   │   │   │   ├── useConversations.ts
│   │   │   │   └── useStreamingMessage.ts
│   │   │   ├── services/
│   │   │   │   ├── chatService.ts
│   │   │   │   └── websocketService.ts
│   │   │   ├── stores/
│   │   │   │   └── chatStore.ts           # Zustand: messages, streaming state
│   │   │   ├── types/
│   │   │   │   └── index.ts
│   │   │   └── index.ts
│   │   │
│   │   └── dashboard/
│   │       ├── views/
│   │       │   └── DashboardView.tsx
│   │       ├── components/
│   │       │   ├── StatsCards.tsx
│   │       │   ├── RecentAgents.tsx
│   │       │   └── RecentConversations.tsx
│   │       └── index.ts
│   │
│   ├── components/                        # Shared components
│   │   ├── ui/                            # shadcn/ui components (auto-generated)
│   │   │   ├── button.tsx
│   │   │   ├── input.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── dropdown-menu.tsx
│   │   │   ├── card.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── toast.tsx
│   │   │   ├── skeleton.tsx
│   │   │   ├── table.tsx
│   │   │   ├── tabs.tsx
│   │   │   ├── textarea.tsx
│   │   │   ├── select.tsx
│   │   │   ├── form.tsx
│   │   │   ├── sheet.tsx
│   │   │   └── ...
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Header.tsx
│   │   │   ├── MobileNav.tsx
│   │   │   └── Breadcrumbs.tsx
│   │   ├── shared/
│   │   │   ├── EmptyState.tsx
│   │   │   ├── LoadingState.tsx
│   │   │   ├── ErrorState.tsx
│   │   │   ├── ConfirmDialog.tsx
│   │   │   ├── SearchInput.tsx
│   │   │   ├── Pagination.tsx
│   │   │   └── JsonEditor.tsx            # Monaco-based JSON editor
│   │   └── providers/
│   │       ├── Providers.tsx              # Compose all providers
│   │       ├── QueryProvider.tsx          # TanStack Query
│   │       ├── ThemeProvider.tsx          # Dark/light mode
│   │       └── AuthProvider.tsx           # Auth guard + redirect
│   │
│   ├── lib/                               # Shared utilities
│   │   ├── api/
│   │   │   ├── client.ts                  # Axios instance + interceptors
│   │   │   └── endpoints.ts               # API URL constants
│   │   ├── ws/
│   │   │   └── client.ts                  # WebSocket client wrapper
│   │   ├── auth/
│   │   │   ├── tokens.ts                  # Token storage (localStorage)
│   │   │   └── guards.ts                  # Auth check helpers
│   │   ├── utils/
│   │   │   ├── cn.ts                      # clsx + twMerge
│   │   │   ├── formatters.ts              # Date, number formatters
│   │   │   └── validators.ts              # Shared Zod schemas
│   │   └── constants.ts
│   │
│   ├── hooks/                             # Shared hooks
│   │   ├── useDebounce.ts
│   │   ├── useMediaQuery.ts
│   │   └── useLocalStorage.ts
│   │
│   └── styles/
│       └── globals.css                    # Tailwind base + shadcn theme
│
├── .env.local
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── components.json                        # shadcn/ui config
└── package.json
```

---

## Feature Module Pattern

Mỗi feature tuân theo cấu trúc:

```
features/{feature}/
├── views/           # Page-level components (1 view = 1 page)
├── components/      # UI components specific to this feature
├── hooks/           # Custom hooks (TanStack Query + logic)
├── services/        # API call functions (Axios)
├── stores/          # Zustand stores (chỉ khi cần client state)
├── types/           # TypeScript interfaces
└── index.ts         # Barrel export (public API)
```

### Rules
1. **Views** = top-level component cho 1 page, compose từ components + hooks
2. **Components** = UI thuần, nhận props, không gọi API trực tiếp
3. **Hooks** = business logic, TanStack Query wrappers, WebSocket handlers
4. **Services** = pure functions gọi API qua Axios, return typed data
5. **Stores** = Zustand, chỉ dùng cho UI state (không dùng cho server state)
6. **index.ts** = chỉ export views + types cần thiết, encapsulate nội bộ

### Import Rules
```
app/ -> features/ (chỉ qua index.ts)
features/ -> components/ (shared UI)
features/ -> lib/ (utilities)
features/ -> hooks/ (shared hooks)
features/ ✗ features/ (KHÔNG cross-import giữa features, trừ qua shared)
```

---

## Data Flow

```
                    ┌─────────────────────────────────────────┐
                    │              Next.js Page                │
                    │  (Server Component - metadata + SEO)    │
                    │         imports <FeatureView />          │
                    └──────────────┬──────────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────────┐
                    │            Feature View                  │
                    │       (Client Component)                 │
                    │  uses hooks + composes components        │
                    └──────────────┬──────────────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                     │
   ┌──────────▼───────┐  ┌───────▼────────┐  ┌────────▼────────┐
   │  TanStack Query   │  │ Zustand Store   │  │   Components    │
   │  (server state)   │  │ (UI state)      │  │   (presentational)
   │                   │  │                 │  │                 │
   │  useQuery()       │  │  sidebar open   │  │  AgentCard      │
   │  useMutation()    │  │  selected node  │  │  ToolForm       │
   │  invalidation     │  │  streaming msg  │  │  ChatBubble     │
   └────────┬──────────┘  └─────────────────┘  └─────────────────┘
            │
   ┌────────▼──────────┐
   │    Service Layer   │
   │  (Axios calls)     │
   │                    │
   │  agentService.ts   │
   │  toolService.ts    │
   └────────┬──────────┘
            │
   ┌────────▼──────────┐
   │   Axios Instance   │
   │  (interceptors)    │
   │  + JWT auto-attach │
   │  + error handling  │
   │  + refresh token   │
   └────────────────────┘
```

---

## Pattern Examples

### Service Layer
```tsx
// features/agents/services/agentService.ts
import { apiClient } from "@/lib/api/client";
import type { Agent, CreateAgentInput, UpdateAgentInput } from "../types";

export const agentService = {
  list: () =>
    apiClient.get<Agent[]>("/agents").then((r) => r.data),

  getById: (id: string) =>
    apiClient.get<Agent>(`/agents/${id}`).then((r) => r.data),

  create: (data: CreateAgentInput) =>
    apiClient.post<Agent>("/agents", data).then((r) => r.data),

  update: (id: string, data: UpdateAgentInput) =>
    apiClient.put<Agent>(`/agents/${id}`, data).then((r) => r.data),

  delete: (id: string) =>
    apiClient.delete(`/agents/${id}`),

  attachTool: (agentId: string, toolId: string) =>
    apiClient.post(`/agents/${agentId}/tools/${toolId}`),

  detachTool: (agentId: string, toolId: string) =>
    apiClient.delete(`/agents/${agentId}/tools/${toolId}`),
};
```

### TanStack Query Hooks
```tsx
// features/agents/hooks/useAgents.ts
import { useQuery } from "@tanstack/react-query";
import { agentService } from "../services/agentService";

export const agentKeys = {
  all: ["agents"] as const,
  list: () => [...agentKeys.all, "list"] as const,
  detail: (id: string) => [...agentKeys.all, "detail", id] as const,
};

export function useAgents() {
  return useQuery({
    queryKey: agentKeys.list(),
    queryFn: agentService.list,
  });
}

export function useAgent(id: string) {
  return useQuery({
    queryKey: agentKeys.detail(id),
    queryFn: () => agentService.getById(id),
    enabled: !!id,
  });
}
```

```tsx
// features/agents/hooks/useAgentMutations.ts
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { agentService } from "../services/agentService";
import { agentKeys } from "./useAgents";

export function useCreateAgent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: agentService.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.list() });
    },
  });
}

export function useUpdateAgent(id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UpdateAgentInput) => agentService.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: agentKeys.list() });
    },
  });
}
```

### Zustand Store (UI state only)
```tsx
// features/chat/stores/chatStore.ts
import { create } from "zustand";

interface ChatState {
  isStreaming: boolean;
  streamingContent: string;
  selectedConversationId: string | null;

  setStreaming: (streaming: boolean) => void;
  appendStreamContent: (chunk: string) => void;
  resetStream: () => void;
  selectConversation: (id: string | null) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  isStreaming: false,
  streamingContent: "",
  selectedConversationId: null,

  setStreaming: (streaming) => set({ isStreaming: streaming }),
  appendStreamContent: (chunk) =>
    set((s) => ({ streamingContent: s.streamingContent + chunk })),
  resetStream: () => set({ streamingContent: "", isStreaming: false }),
  selectConversation: (id) => set({ selectedConversationId: id }),
}));
```

### View Component
```tsx
// features/agents/views/AgentListView.tsx
"use client";

import { useAgents } from "../hooks/useAgents";
import { useCreateAgent } from "../hooks/useAgentMutations";
import { AgentCard } from "../components/AgentCard";
import { Button } from "@/components/ui/button";
import { LoadingState } from "@/components/shared/LoadingState";
import { EmptyState } from "@/components/shared/EmptyState";
import { Plus } from "lucide-react";

export function AgentListView() {
  const { data: agents, isLoading } = useAgents();

  if (isLoading) return <LoadingState />;
  if (!agents?.length) return <EmptyState title="No agents yet" />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Agents</h1>
        <Button asChild>
          <a href="/agents/new"><Plus className="mr-2 h-4 w-4" /> New Agent</a>
        </Button>
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {agents.map((agent) => (
          <AgentCard key={agent.id} agent={agent} />
        ))}
      </div>
    </div>
  );
}
```

### Thin Page (App Router)
```tsx
// app/(dashboard)/agents/page.tsx
import { Metadata } from "next";
import { AgentListView } from "@/features/agents";

export const metadata: Metadata = {
  title: "Agents | AI Agent Builder",
  description: "Create and manage your AI agents with custom tools and knowledge bases",
  openGraph: {
    title: "Agents | AI Agent Builder",
    description: "Create and manage your AI agents",
  },
};

export default function AgentsPage() {
  return <AgentListView />;
}
```

---

## Providers Setup

```tsx
// components/providers/Providers.tsx
"use client";

import { QueryProvider } from "./QueryProvider";
import { ThemeProvider } from "./ThemeProvider";
import { AuthProvider } from "./AuthProvider";
import { Toaster } from "@/components/ui/toaster";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryProvider>
      <ThemeProvider defaultTheme="dark" storageKey="agent-builder-theme">
        <AuthProvider>
          {children}
          <Toaster />
        </AuthProvider>
      </ThemeProvider>
    </QueryProvider>
  );
}
```

```tsx
// app/layout.tsx
import { Providers } from "@/components/providers/Providers";
import { Inter } from "next/font/google";
import "@/styles/globals.css";

const inter = Inter({ subsets: ["latin"] });

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

---

## API Client Setup

```tsx
// lib/api/client.ts
import axios from "axios";
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from "@/lib/auth/tokens";

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api",
  headers: { "Content-Type": "application/json" },
});

// Auto-attach JWT
apiClient.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auto-refresh on 401
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      try {
        const refresh = getRefreshToken();
        const { data } = await axios.post(
          `${apiClient.defaults.baseURL}/auth/refresh`,
          { refresh_token: refresh }
        );
        setTokens(data.access_token, data.refresh_token);
        original.headers.Authorization = `Bearer ${data.access_token}`;
        return apiClient(original);
      } catch {
        clearTokens();
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);
```

---

## WebSocket Client

```tsx
// lib/ws/client.ts
import { getAccessToken } from "@/lib/auth/tokens";

type WSMessage =
  | { type: "token"; content: string }
  | { type: "tool_start"; name: string }
  | { type: "tool_end"; name: string; result: string }
  | { type: "done" }
  | { type: "error"; message: string };

interface ChatWSOptions {
  conversationId: string;
  onToken: (content: string) => void;
  onToolStart: (name: string) => void;
  onToolEnd: (name: string, result: string) => void;
  onDone: () => void;
  onError: (message: string) => void;
}

export function createChatWS(options: ChatWSOptions) {
  const token = getAccessToken();
  const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL}/ws/chat/${options.conversationId}?token=${token}`;
  const ws = new WebSocket(wsUrl);

  ws.onmessage = (event) => {
    const msg: WSMessage = JSON.parse(event.data);
    switch (msg.type) {
      case "token":     options.onToken(msg.content); break;
      case "tool_start": options.onToolStart(msg.name); break;
      case "tool_end":  options.onToolEnd(msg.name, msg.result); break;
      case "done":      options.onDone(); break;
      case "error":     options.onError(msg.message); break;
    }
  };

  return {
    send: (content: string) => ws.send(JSON.stringify({ content })),
    close: () => ws.close(),
  };
}
```

---

## SEO Strategy

| Route | SEO Approach |
|-------|-------------|
| `/login`, `/register` | Static metadata in `page.tsx` |
| `/agents` | Static metadata, list rendered client-side (auth-gated, no need for SSR SEO) |
| `/agents/[id]` | `generateMetadata()` fetch agent name for title (optional, since auth-gated) |
| `/workflows/[id]` | Static metadata per page |

Since this is a **dashboard app behind auth**, SEO is mainly for:
- Page titles (browser tab)
- OpenGraph tags (link sharing)
- Structured metadata

Public-facing pages (landing, docs) would be separate and fully SSR.

---

## Key Libraries

```json
{
  "dependencies": {
    "next": "^14.2",
    "react": "^18.3",
    "typescript": "^5.4",
    "@tanstack/react-query": "^5",
    "zustand": "^4",
    "axios": "^1",
    "react-hook-form": "^7",
    "@hookform/resolvers": "^3",
    "zod": "^3",
    "reactflow": "^11",
    "lucide-react": "^0.400",
    "tailwindcss": "^3.4",
    "class-variance-authority": "^0.7",
    "clsx": "^2",
    "tailwind-merge": "^2",
    "@radix-ui/react-*": "shadcn dependencies",
    "next-themes": "^0.3",
    "@monaco-editor/react": "^4"
  }
}
```
