"use client";

import Link from "next/link";
import { Sparkles } from "lucide-react";
import { useTemplate } from "../hooks/useTemplates";

interface ForkedFromBadgeProps {
  templateId: string;
}

/** Compact pill that links back to the Hub page of the template a forked
 *  agent was cloned from. Renders nothing while the template is loading or
 *  if the lookup fails (e.g. template was archived). */
export function ForkedFromBadge({ templateId }: ForkedFromBadgeProps) {
  const { data: template } = useTemplate(templateId);
  if (!template) return null;

  return (
    <Link
      href={`/hub/${template.slug}`}
      className="flex items-center gap-1.5 rounded-full border border-violet-500/30 bg-violet-500/10 px-2 py-0.5 text-[10px] font-medium text-violet-700 transition-colors hover:bg-violet-500/20 dark:text-violet-300"
      title="View source template"
    >
      <Sparkles className="h-2.5 w-2.5" />
      Forked from {template.title}
    </Link>
  );
}
