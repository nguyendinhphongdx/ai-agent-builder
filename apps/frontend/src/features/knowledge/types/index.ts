export interface KnowledgeBase {
  id: string;
  name: string;
  description: string | null;
  embedding_provider: string;
  embedding_model: string;
  embedding_dimensions: number;
  chunk_size: number;
  chunk_overlap: number;
  chunk_strategy: string;
  retrieval_top_k: number;
  retrieval_score_threshold: number;
  total_documents: number;
  total_chunks: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export type DocumentPhase =
  | "queued"
  | "parsing"
  | "chunking"
  | "embedding"
  | "ready"
  | "failed"
  | null;

export interface KBDocument {
  id: string;
  knowledge_base_id: string;
  filename: string;
  file_type: string;
  file_size: number | null;
  chunk_count: number;
  status: "pending" | "processing" | "ready" | "failed";
  processing_phase: DocumentPhase;
  processing_progress: number | null;
  error_message: string | null;
  created_at: string;
}

export interface DocumentProgressEvent {
  kb_id: string;
  doc_id: string;
  status: "pending" | "processing" | "ready" | "failed";
  phase: DocumentPhase;
  progress: number | null;
  chunk_count: number;
  error_message: string | null;
}

export interface KBDocumentDetail extends KBDocument {
  mime_type: string | null;
  content_hash: string | null;
  token_count: number | null;
  processing_started_at: string | null;
  processing_completed_at: string | null;

  // Snapshot KB config
  chunk_size: number;
  chunk_overlap: number;
  chunk_strategy: string;
  embedding_provider: string;
  embedding_model: string;
  embedding_dimensions: number;

  // Aggregates
  linked_apps: number;
}

export interface KBChunk {
  id: string;
  document_id: string;
  knowledge_base_id: string;
  chunk_index: number;
  content: string;
  token_count: number | null;
  data: Record<string, unknown>;
  created_at: string;
}

export interface KBChunkListResponse {
  items: KBChunk[];
  total: number;
}

export interface KBCreateInput {
  name: string;
  description?: string;
  chunk_size?: number;
  chunk_overlap?: number;
  chunk_strategy?: string;
  retrieval_top_k?: number;
  retrieval_score_threshold?: number;
}

export interface KBUpdateInput {
  name?: string;
  description?: string;
  chunk_size?: number;
  chunk_overlap?: number;
  retrieval_top_k?: number;
  retrieval_score_threshold?: number;
}

export interface RetrievedChunk {
  content: string;
  metadata: Record<string, unknown>;
  score: number | null;
}
