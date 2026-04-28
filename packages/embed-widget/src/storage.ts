/**
 * Per-token conversation persistence. Lets the widget pick up where it
 * left off after a refresh without leaking threads across different agents
 * embedded on the same page.
 */

const KEY = (token: string) => `agentforge:conv:${token}`;

export const storage = {
  loadConversationId(token: string): string | null {
    try {
      return localStorage.getItem(KEY(token));
    } catch {
      // Private browsing / disabled storage — degrade gracefully.
      return null;
    }
  },
  saveConversationId(token: string, id: string): void {
    try {
      localStorage.setItem(KEY(token), id);
    } catch {
      // No-op on failure.
    }
  },
  clearConversation(token: string): void {
    try {
      localStorage.removeItem(KEY(token));
    } catch {
      // No-op.
    }
  },
};
