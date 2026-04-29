"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Send, Sparkles } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { usePublishAgent } from "../hooks/useTemplates";
import { TEMPLATE_CATEGORIES } from "../types";

interface PublishDialogProps {
  agentId: string;
  agentName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function PublishDialog({
  agentId,
  agentName,
  open,
  onOpenChange,
}: PublishDialogProps) {
  const router = useRouter();
  const publish = usePublishAgent();

  const [title, setTitle] = useState(agentName);
  const [description, setDescription] = useState("");
  const [authorName, setAuthorName] = useState("");
  const [category, setCategory] = useState("");
  const [tagsInput, setTagsInput] = useState("");

  const handleSubmit = () => {
    if (!title.trim()) return;
    const tags = tagsInput
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    publish.mutate(
      {
        agentId,
        input: {
          title: title.trim(),
          description: description.trim() || undefined,
          author_name: authorName.trim() || undefined,
          category: category || undefined,
          tags,
          price_cents: 0, // V1: free only
        },
      },
      {
        onSuccess: (template) => {
          onOpenChange(false);
          router.push(`/hub/${template.slug}`);
        },
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-violet-500" />
            Publish to Hub
          </DialogTitle>
          <DialogDescription>
            Anyone can fork this agent into their own library. Tools are cloned.
            Knowledge bases are cloned as empty shells (no documents shared).
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Title */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">
              Title
            </label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Customer Support Bot"
              maxLength={200}
            />
          </div>

          {/* Description */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">
              Description
            </label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What does this agent do? Include any setup notes — required credentials, expected use cases, etc."
              rows={4}
              maxLength={5000}
            />
          </div>

          {/* Author name */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">
              Author display name (optional)
            </label>
            <Input
              value={authorName}
              onChange={(e) => setAuthorName(e.target.value)}
              placeholder="Defaults to your account name"
              maxLength={100}
            />
            <p className="text-[10px] text-muted-foreground/70">
              Free text — use a brand name if you want.
            </p>
          </div>

          {/* Category + tags */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                Category
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full rounded-md border border-border bg-background px-3 py-1.5 text-xs outline-none focus:border-primary"
              >
                <option value="">— Select —</option>
                {TEMPLATE_CATEGORIES.map((cat) => (
                  <option key={cat.value} value={cat.value}>
                    {cat.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                Tags (comma-separated)
              </label>
              <Input
                value={tagsInput}
                onChange={(e) => setTagsInput(e.target.value)}
                placeholder="ecommerce, returns"
              />
            </div>
          </div>

          <p className="rounded-md border border-emerald-500/30 bg-emerald-500/5 p-2.5 text-[11px] text-emerald-700 dark:text-emerald-300">
            V1 publishes as free. Paid templates and Stripe checkout coming in V2.
          </p>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={publish.isPending}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={publish.isPending || !title.trim()}
            className="gap-1.5"
          >
            {publish.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Send className="h-3.5 w-3.5" />
            )}
            Publish
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
