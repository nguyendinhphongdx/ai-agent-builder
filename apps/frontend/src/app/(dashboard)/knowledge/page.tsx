import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Knowledge Bases | AI Agent Builder",
};

export default function KnowledgePage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Knowledge Bases</h1>
      <p className="text-muted-foreground">
        RAG knowledge bases will be available in Phase 2.
      </p>
    </div>
  );
}
