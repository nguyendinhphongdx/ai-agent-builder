export const MODEL_OPTIONS: Record<
  string,
  { label: string; models: { value: string; label: string; context: string }[] }
> = {
  openai: {
    label: "OpenAI",
    models: [
      { value: "gpt-4o", label: "GPT-4o", context: "128K" },
      { value: "gpt-4o-mini", label: "GPT-4o Mini", context: "128K" },
      { value: "gpt-4-turbo", label: "GPT-4 Turbo", context: "128K" },
      { value: "o3-mini", label: "o3-mini", context: "200K" },
    ],
  },
  anthropic: {
    label: "Anthropic",
    models: [
      { value: "claude-sonnet-4-20250514", label: "Claude Sonnet 4", context: "200K" },
      { value: "claude-opus-4-20250514", label: "Claude Opus 4", context: "200K" },
      { value: "claude-haiku-4-5-20251001", label: "Claude Haiku 4.5", context: "200K" },
    ],
  },
  google: {
    label: "Google",
    models: [
      { value: "gemini-2.5-pro", label: "Gemini 2.5 Pro", context: "1M" },
      { value: "gemini-2.5-flash", label: "Gemini 2.5 Flash", context: "1M" },
      { value: "gemini-2.0-flash", label: "Gemini 2.0 Flash", context: "1M" },
      { value: "gemini-1.5-pro", label: "Gemini 1.5 Pro", context: "2M" },
    ],
  },
  ollama: {
    label: "Ollama (Local)",
    models: [
      { value: "llama3.1", label: "Llama 3.1", context: "128K" },
      { value: "mistral", label: "Mistral", context: "32K" },
      { value: "codellama", label: "Code Llama", context: "16K" },
    ],
  },
};
