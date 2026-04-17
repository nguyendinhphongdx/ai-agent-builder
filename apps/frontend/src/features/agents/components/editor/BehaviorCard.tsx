"use client";

import { Sparkles } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import type { UseFormReturn } from "react-hook-form";
import type { AgentEditorFormValues } from "./types";

interface BehaviorCardProps {
  form: UseFormReturn<AgentEditorFormValues>;
}

export function BehaviorCard({ form }: BehaviorCardProps) {
  return (
    <div className="rounded-xl border border-border bg-linear-to-b from-muted/40 to-background p-4">
      <div className="mb-4 flex items-start gap-2">
        <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-primary/30 bg-primary/10">
          <Sparkles className="h-3.5 w-3.5 text-primary" />
        </div>
        <div>
          <p className="text-sm font-medium">Hành vi & Tính cách</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            Hướng dẫn cách agent phản hồi và giao tiếp.
          </p>
        </div>
      </div>

      <div className="space-y-4">
        <FormField
          control={form.control}
          name="system_prompt"
          render={({ field }) => (
            <FormItem>
              <FormLabel>
                System Prompt <span className="text-destructive">*</span>
              </FormLabel>
              <FormDescription>
                Hướng dẫn cho LLM về cách agent hành xử, phong cách trả lời.
              </FormDescription>
              <FormControl>
                <Textarea
                  placeholder={
                    "Bạn là trợ lý AI thông minh, trả lời chính xác và ngắn gọn.\n\nNguyên tắc:\n- Luôn trả lời bằng tiếng Việt\n- Trích dẫn nguồn khi cần"
                  }
                  className="min-h-40 font-mono text-xs leading-relaxed"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="welcome_message"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Tin nhắn chào mừng</FormLabel>
              <FormDescription>
                Hiển thị khi user bắt đầu cuộc hội thoại mới.
              </FormDescription>
              <FormControl>
                <Input
                  placeholder="Xin chào! Tôi có thể giúp gì cho bạn?"
                  {...field}
                />
              </FormControl>
            </FormItem>
          )}
        />
      </div>
    </div>
  );
}
