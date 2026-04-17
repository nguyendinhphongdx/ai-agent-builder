export const API = {
  auth: {
    register: "/auth/register",
    login: "/auth/login",
    logout: "/auth/logout",
    refresh: "/auth/refresh",
    me: "/auth/me",
  },
  agents: {
    list: "/agents",
    create: "/agents",
    detail: (id: string) => `/agents/${id}`,
    attachTool: (agentId: string, toolId: string) =>
      `/agents/${agentId}/tools/${toolId}`,
    attachKB: (agentId: string, kbId: string) =>
      `/agents/${agentId}/knowledge-bases/${kbId}`,
  },
  tools: {
    list: "/tools",
    create: "/tools",
    detail: (id: string) => `/tools/${id}`,
    test: (id: string) => `/tools/${id}/test`,
  },
  knowledgeBases: {
    list: "/knowledge-bases",
    create: "/knowledge-bases",
    detail: (id: string) => `/knowledge-bases/${id}`,
    documents: (id: string) => `/knowledge-bases/${id}/documents`,
    query: (id: string) => `/knowledge-bases/${id}/query`,
  },
  workflows: {
    list: "/workflows",
    create: "/workflows",
    detail: (id: string) => `/workflows/${id}`,
    execute: (id: string) => `/workflows/${id}/execute`,
  },
  conversations: {
    list: "/conversations",
    create: "/conversations",
    detail: (id: string) => `/conversations/${id}`,
    messages: (id: string) => `/conversations/${id}/messages`,
  },
} as const;
