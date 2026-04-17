import type { DocEntry, DocIndex } from "./indexer.js";

interface SearchResult {
  doc: DocEntry;
  score: number;
  matchedTags: string[];
}

function normalize(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s_-]/g, " ")
    .split(/\s+/)
    .filter((w) => w.length > 1);
}

/**
 * 4-tier keyword search:
 * 1. Tag exact match → 10 points
 * 2. Title word match → 5 points
 * 3. Summary substring → 2 points
 * 4. Content scan → 1 point (capped at 3)
 */
export function search(
  index: DocIndex,
  query: string,
  options: { domain?: string; limit?: number } = {}
): SearchResult[] {
  const { domain, limit = 5 } = options;
  const queryTerms = normalize(query);

  if (queryTerms.length === 0) return [];

  const results: SearchResult[] = [];

  for (const doc of index.entries) {
    // Domain filter
    if (domain && doc.domain !== domain) continue;

    let score = 0;
    const matchedTags: string[] = [];

    // Tier 1: Tag exact match (10 pts each)
    const tagsLower = doc.tags.map((t) => t.toLowerCase());
    for (const term of queryTerms) {
      if (tagsLower.includes(term)) {
        score += 10;
        matchedTags.push(term);
      }
      // Partial tag match (e.g., "websocket" matches "websocket-protocol")
      for (const tag of tagsLower) {
        if (tag.includes(term) && !tagsLower.includes(term)) {
          score += 5;
          matchedTags.push(tag);
        }
      }
    }

    // Tier 2: Title word match (5 pts each)
    const titleWords = normalize(doc.title);
    for (const term of queryTerms) {
      if (titleWords.includes(term)) {
        score += 5;
      }
    }

    // Tier 3: Summary substring (2 pts each)
    const summaryLower = doc.summary.toLowerCase();
    for (const term of queryTerms) {
      if (summaryLower.includes(term)) {
        score += 2;
      }
    }

    // Tier 4: Content scan (1 pt, capped at 3)
    if (score === 0 && doc.content) {
      const contentLower = doc.content.toLowerCase();
      let contentScore = 0;
      for (const term of queryTerms) {
        if (contentLower.includes(term)) {
          contentScore += 1;
        }
      }
      score += Math.min(contentScore, 3);
    }

    if (score > 0) {
      results.push({ doc, score, matchedTags });
    }
  }

  results.sort((a, b) => b.score - a.score);
  return results.slice(0, limit);
}

/**
 * Find docs related to a table name.
 */
export function findTableDocs(
  index: DocIndex,
  tableName: string
): DocEntry | undefined {
  const normalized = tableName.toLowerCase().replace(/s$/, "");

  // Direct tag match
  for (const doc of index.entries) {
    if (doc.domain !== "database") continue;
    if (
      doc.tags.some(
        (t) =>
          t.toLowerCase() === tableName.toLowerCase() ||
          t.toLowerCase() === normalized
      )
    ) {
      return doc;
    }
  }

  // ID match
  return index.byId.get(`database-table-${normalized}`) ||
    index.byId.get(`database-${normalized}`);
}

/**
 * Find docs related to an API endpoint.
 */
export function findApiDocs(
  index: DocIndex,
  endpoint: string
): DocEntry | undefined {
  const normalized = endpoint.toLowerCase().replace(/^\/api\//, "");
  const firstSegment = normalized.split("/")[0];

  for (const doc of index.entries) {
    if (doc.domain !== "api") continue;
    if (doc.tags.some((t) => t.toLowerCase().includes(firstSegment))) {
      return doc;
    }
  }

  return undefined;
}

/**
 * Find docs related to a frontend component/feature.
 */
export function findComponentDocs(
  index: DocIndex,
  name: string
): DocEntry[] {
  const normalized = name.toLowerCase();

  return index.entries.filter((doc) => {
    if (doc.domain !== "frontend") return false;
    return (
      doc.tags.some((t) => t.toLowerCase().includes(normalized)) ||
      doc.title.toLowerCase().includes(normalized) ||
      doc.id.toLowerCase().includes(normalized)
    );
  });
}
