import fs from "fs";
import path from "path";
import matter from "gray-matter";

export interface DocEntry {
  id: string;
  path: string;
  title: string;
  domain: string;
  tags: string[];
  related: string[];
  summary: string;
  content?: string; // Lazy-loaded
}

export interface DocIndex {
  entries: DocEntry[];
  byId: Map<string, DocEntry>;
  byDomain: Map<string, DocEntry[]>;
  byTag: Map<string, DocEntry[]>;
}

/**
 * Load all markdown files from docs/ directory and build search index.
 * Parses YAML frontmatter for metadata.
 */
export function loadIndex(docsDir: string): DocIndex {
  const entries: DocEntry[] = [];
  const byId = new Map<string, DocEntry>();
  const byDomain = new Map<string, DocEntry[]>();
  const byTag = new Map<string, DocEntry[]>();

  // Recursively find all .md files
  function walk(dir: string) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        walk(fullPath);
      } else if (entry.name.endsWith(".md")) {
        const raw = fs.readFileSync(fullPath, "utf-8");
        const { data, content } = matter(raw);

        if (!data.id) return; // Skip files without frontmatter

        const doc: DocEntry = {
          id: data.id,
          path: path.relative(docsDir, fullPath).replace(/\\/g, "/"),
          title: data.title || entry.name,
          domain: data.domain || "unknown",
          tags: data.tags || [],
          related: data.related || [],
          summary: data.summary || "",
          content: content.trim(),
        };

        entries.push(doc);
        byId.set(doc.id, doc);

        // Index by domain
        if (!byDomain.has(doc.domain)) byDomain.set(doc.domain, []);
        byDomain.get(doc.domain)!.push(doc);

        // Index by tags
        for (const tag of doc.tags) {
          if (!byTag.has(tag)) byTag.set(tag, []);
          byTag.get(tag)!.push(doc);
        }
      }
    }
  }

  walk(docsDir);

  console.error(
    `[mcp-docs] Loaded ${entries.length} docs from ${docsDir}`
  );

  return { entries, byId, byDomain, byTag };
}

/**
 * Get full content of a doc file.
 */
export function getDocContent(docsDir: string, docPath: string): string {
  const fullPath = path.join(docsDir, docPath);
  if (!fs.existsSync(fullPath)) {
    throw new Error(`Doc not found: ${docPath}`);
  }
  const raw = fs.readFileSync(fullPath, "utf-8");
  const { content } = matter(raw);
  return content.trim();
}
