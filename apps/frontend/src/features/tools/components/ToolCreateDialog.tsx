"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Globe, Code, Database, Wrench, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogClose,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { useCreateTool } from "../hooks/useTools";
import { TOOL_TYPE_META, type ToolType } from "../types";
import { cn } from "@/lib/utils";

const ICON_MAP: Record<string, typeof Globe> = {
  globe: Globe,
  code: Code,
  database: Database,
  wrench: Wrench,
};

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().min(1, "Description is required"),
  tool_type: z.string().min(1),
});

type FormValues = z.infer<typeof schema>;

interface ToolCreateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ToolCreateDialog({ open, onOpenChange }: ToolCreateDialogProps) {
  const createTool = useCreateTool();
  const [selectedType, setSelectedType] = useState<ToolType>("http_request");

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: "",
      description: "",
      tool_type: "http_request",
    },
  });

  const onSubmit = (data: FormValues) => {
    const defaults: Record<string, Record<string, unknown>> = {
      http_request: { method: "GET", url: "", headers: {} },
      code_exec: { language: "python", code_template: "" },
      web_scrape: { url_template: "", max_length: 5000 },
      db_query: { connection_string: "", max_rows: 50 },
      custom_function: { function_code: "" },
    };

    createTool.mutate(
      {
        name: data.name,
        description: data.description,
        tool_type: data.tool_type as ToolType,
        config: defaults[data.tool_type] ?? {},
        input_schema: {
          type: "object",
          properties: {
            query: { type: "string", description: "Input query" },
          },
          required: ["query"],
        },
      },
      {
        onSuccess: () => {
          onOpenChange(false);
          form.reset();
        },
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-card border-border text-foreground max-w-md">
        <DialogHeader>
          <DialogTitle>Create Tool</DialogTitle>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
            {/* Tool type picker */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground/70">Type</label>
              <div className="grid grid-cols-2 gap-2">
                {(Object.entries(TOOL_TYPE_META) as [ToolType, typeof TOOL_TYPE_META[ToolType]][]).map(
                  ([type, meta]) => {
                    const Icon = ICON_MAP[meta.icon] ?? Wrench;
                    const isSelected = selectedType === type;
                    return (
                      <button
                        key={type}
                        type="button"
                        onClick={() => {
                          setSelectedType(type);
                          form.setValue("tool_type", type);
                        }}
                        className={cn(
                          "flex items-center gap-2.5 rounded-lg border p-2.5 text-left transition-all",
                          isSelected
                            ? "border-primary/30 bg-primary/10"
                            : "border-border bg-muted/50 hover:border-border"
                        )}
                      >
                        <Icon className={cn("h-4 w-4", isSelected ? "text-primary" : "text-muted-foreground")} />
                        <div>
                          <p className="text-[11px] font-medium">{meta.label}</p>
                          <p className="text-[9px] text-muted-foreground">{meta.description}</p>
                        </div>
                      </button>
                    );
                  }
                )}
              </div>
            </div>

            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm text-foreground/70">Name</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="e.g. Search Products API"
                      className="bg-muted border-border"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm text-foreground/70">
                    Description
                    <span className="text-muted-foreground font-normal ml-1">(LLM sees this)</span>
                  </FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="Search the product catalog by name or category..."
                      className="min-h-[60px] bg-muted border-border text-sm"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="flex justify-end gap-2 pt-2">
              <DialogClose>
                <Button type="button" variant="ghost" size="sm">
                  Cancel
                </Button>
              </DialogClose>
              <Button
                type="submit"
                size="sm"
                disabled={createTool.isPending}
                className="gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
              >
                {createTool.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
                Create
              </Button>
            </div>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
