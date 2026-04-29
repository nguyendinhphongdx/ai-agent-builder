"use client";

import { useEffect, useState } from "react";
import { Loader2, Save } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useUpdateTemplate } from "../hooks/useTemplates";
import { TEMPLATE_CATEGORIES, type TemplateSummary } from "../types";

interface EditTemplateDialogProps {
  template: TemplateSummary;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function EditTemplateDialog({
  template,
  open,
  onOpenChange,
}: EditTemplateDialogProps) {
  const update = useUpdateTemplate(template.id);

  const [title, setTitle] = useState(template.title);
  const [description, setDescription] = useState(template.description ?? "");
  const [authorName, setAuthorName] = useState(template.author_name);
  const [category, setCategory] = useState(template.category ?? "");
  const [tagsInput, setTagsInput] = useState(template.tags.join(", "));

  // Reset form when reopening with a different template.
  useEffect(() => {
    if (open) {
      setTitle(template.title);
      setDescription(template.description ?? "");
      setAuthorName(template.author_name);
      setCategory(template.category ?? "");
      setTagsInput(template.tags.join(", "));
    }
  }, [open, template]);

  const handleSubmit = () => {
    if (!title.trim()) return;
    update.mutate(
      {
        title: title.trim(),
        description: description.trim() || undefined,
        author_name: authorName.trim() || undefined,
        category: category || undefined,
        tags: tagsInput
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
      },
      { onSuccess: () => onOpenChange(false) },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Edit template</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <Field label="Title">
            <Input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} />
          </Field>
          <Field label="Description">
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
              maxLength={5000}
            />
          </Field>
          <Field label="Author display name">
            <Input
              value={authorName}
              onChange={(e) => setAuthorName(e.target.value)}
              maxLength={100}
            />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Category">
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full rounded-md border border-border bg-background px-3 py-1.5 text-xs outline-none focus:border-primary"
              >
                <option value="">— None —</option>
                {TEMPLATE_CATEGORIES.map((cat) => (
                  <option key={cat.value} value={cat.value}>
                    {cat.label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Tags (comma-separated)">
              <Input value={tagsInput} onChange={(e) => setTagsInput(e.target.value)} />
            </Field>
          </div>

          <p className="text-[11px] text-muted-foreground/70">
            Editing metadata only. The agent snapshot stays frozen — to ship
            changes, publish a new version (coming in V2).
          </p>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={update.isPending}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={update.isPending || !title.trim()}
            className="gap-1.5"
          >
            {update.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Save className="h-3.5 w-3.5" />
            )}
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-medium text-muted-foreground">{label}</label>
      {children}
    </div>
  );
}
