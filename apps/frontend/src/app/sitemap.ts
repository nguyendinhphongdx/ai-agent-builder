import type { MetadataRoute } from "next";
import { SITE } from "@/features/landing";

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  return [
    { url: SITE.url, lastModified: now, changeFrequency: "weekly", priority: 1 },
    { url: `${SITE.url}/login`, lastModified: now, changeFrequency: "yearly", priority: 0.3 },
    { url: `${SITE.url}/register`, lastModified: now, changeFrequency: "yearly", priority: 0.5 },
  ];
}
