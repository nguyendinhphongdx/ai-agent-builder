import { z } from "zod/v4";

export const agentEditorSchema = z.object({
  name: z.string().min(1, "Ten agent la bat buoc"),
  description: z.string().optional(),
  system_prompt: z.string().min(1, "System prompt la bat buoc"),
  llm_provider: z.string().min(1),
  llm_model: z.string().min(1),
  welcome_message: z.string().optional(),
  temperature: z.number().min(0).max(2).optional(),
  max_tokens: z.number().min(1).max(128000).optional(),
  max_turns: z.number().min(1).max(200).optional(),
  is_published: z.boolean().optional(),
});

export type AgentEditorFormValues = z.infer<typeof agentEditorSchema>;
