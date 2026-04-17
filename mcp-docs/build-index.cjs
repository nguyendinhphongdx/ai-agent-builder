const fs = require("fs");
const path = require("path");
const matter = require("gray-matter");

const docsDir = path.resolve(__dirname, "..", "docs");
const entries = [];

function walk(dir) {
  for (const f of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, f.name);
    if (f.isDirectory()) {
      walk(full);
    } else if (f.name.endsWith(".md")) {
      const raw = fs.readFileSync(full, "utf-8");
      const { data } = matter(raw);
      if (data.id) {
        entries.push({
          id: data.id,
          path: path.relative(docsDir, full).split(path.sep).join("/"),
          title: data.title || f.name,
          domain: data.domain || "unknown",
          tags: data.tags || [],
          related: data.related || [],
          summary: data.summary || "",
        });
      }
    }
  }
}

walk(docsDir);
entries.sort(
  (a, b) => a.domain.localeCompare(b.domain) || a.id.localeCompare(b.id)
);

const outPath = path.join(docsDir, "_index.json");
fs.writeFileSync(outPath, JSON.stringify(entries, null, 2));
console.log(`Generated _index.json with ${entries.length} entries`);
