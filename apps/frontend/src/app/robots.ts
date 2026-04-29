import type { MetadataRoute } from "next";
import { SITE } from "@/features/landing";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        // Authenticated app surface — no public value, save crawl budget.
        disallow: [
          "/api/",
          "/agents/",
          "/conversations/",
          "/workflows/",
          "/knowledge/",
          "/tools/",
          "/settings/",
          "/home/",
        ],
      },
    ],
    sitemap: `${SITE.url}/sitemap.xml`,
    host: SITE.url,
  };
}
