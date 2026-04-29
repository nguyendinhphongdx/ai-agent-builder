"use client";

import Link from "next/link";
import { ArrowUpCircle, Sparkles } from "lucide-react";
import { useTemplate, useTemplateVersions } from "../hooks/useTemplates";

interface ForkedFromBadgeProps {
  templateId: string;
  /** Version this agent was forked from. When the template's current
   *  version differs, an "Update available" pill appears. */
  versionId?: string | null;
}

/** Compact pill that links back to the Hub page of the template a forked
 *  agent was cloned from. When the source template has shipped a newer
 *  version since the fork, an extra "Update" pill is shown next to it.
 *  Renders nothing while the template is loading or if the lookup fails
 *  (e.g. template was archived). */
export function ForkedFromBadge({ templateId, versionId }: ForkedFromBadgeProps) {
  const { data: template } = useTemplate(templateId);
  const { data: versions } = useTemplateVersions(templateId);
  if (!template) return null;

  const current = versions?.find((v) => v.is_current);
  const hasUpdate = !!(versionId && current && current.id !== versionId);
  const updateLabel = hasUpdate && current ? `→ ${current.version}` : null;

  return (
    <div className="flex items-center gap-1.5">
      <Link
        href={`/hub/${template.slug}`}
        className="flex items-center gap-1.5 rounded-full border border-violet-500/30 bg-violet-500/10 px-2 py-0.5 text-[10px] font-medium text-violet-700 transition-colors hover:bg-violet-500/20 dark:text-violet-300"
        title="View source template"
      >
        <Sparkles className="h-2.5 w-2.5" />
        Forked from {template.title}
      </Link>
      {hasUpdate && (
        <Link
          href={`/hub/${template.slug}`}
          className="flex items-center gap-1 rounded-full border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium text-amber-700 transition-colors hover:bg-amber-500/20 dark:text-amber-300"
          title="A newer version of the source template is available — re-fork to use it"
        >
          <ArrowUpCircle className="h-2.5 w-2.5" />
          Update available {updateLabel}
        </Link>
      )}
    </div>
  );
}
