import { z } from "zod/v4";

export const agentEditorSchema = z.object({
  name: z.string().min(1, "Ten agent la bat buoc"),
  description: z.string().optional(),
  system_prompt: z.string().min(1, "System prompt la bat buoc"),
  model_id: z.string().min(1),              // "provider/model"
  credential_id: z.string().nullable(),     // FK to ai_credentials.id
  welcome_message: z.string().optional(),
  temperature: z.number().min(0).max(2).optional(),
  max_tokens: z.number().min(1).max(128000).optional(),
  max_turns: z.number().min(1).max(200).optional(),
  is_published: z.boolean().optional(),
});

export type AgentEditorFormValues = z.infer<typeof agentEditorSchema>;
