import { create } from "zustand";
import type { Message } from "../types";

interface ChatState {
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;
  activeToolName: string | null;

  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  setStreaming: (streaming: boolean) => void;
  appendStreamContent: (chunk: string) => void;
  setActiveTool: (name: string | null) => void;
  resetStream: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isStreaming: false,
  streamingContent: "",
  activeToolName: null,

  setMessages: (messages) => set({ messages }),
  addMessage: (message) =>
    set((s) => ({ messages: [...s.messages, message] })),
  setStreaming: (streaming) => set({ isStreaming: streaming }),
  appendStreamContent: (chunk) =>
    set((s) => ({ streamingContent: s.streamingContent + chunk })),
  setActiveTool: (name) => set({ activeToolName: name }),
  resetStream: () =>
    set({ streamingContent: "", isStreaming: false, activeToolName: null }),
}));
