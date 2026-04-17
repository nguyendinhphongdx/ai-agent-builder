import { apiClient } from "./client";

export type UploadType = "avatar" | "document" | "cv" | "attachment";

export interface FileRecord {
  id: string;
  owner_id: string;
  type: string;
  original_name: string;
  storage_key: string;
  mime_type: string;
  size: number;
  access: "public" | "private";
  entity_type: string | null;
  entity_id: string | null;
  url: string | null;
  created_at: string;
}

export interface FileUrlResponse {
  url: string;
  expires_in: number;
}

export const uploadService = {
  /**
   * Upload a file. Single endpoint, type determines validation.
   */
  upload: (
    file: File,
    type: UploadType,
    options?: { entityType?: string; entityId?: string }
  ) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("type", type);
    if (options?.entityType) formData.append("entity_type", options.entityType);
    if (options?.entityId) formData.append("entity_id", options.entityId);

    return apiClient
      .post<FileRecord>("/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },

  /** Get file metadata */
  getFile: (fileId: string) =>
    apiClient.get<FileRecord>(`/upload/${fileId}`).then((r) => r.data),

  /** Get URL for a file (presigned for private files) */
  getFileUrl: (fileId: string) =>
    apiClient.get<FileUrlResponse>(`/upload/${fileId}/url`).then((r) => r.data),

  /** Delete a file */
  deleteFile: (fileId: string) =>
    apiClient.delete(`/upload/${fileId}`),

  /** List available upload types and constraints */
  getUploadTypes: () =>
    apiClient.get<Record<string, { max_size: number; max_size_mb: number; allowed_extensions: string[]; access: string }>>("/upload/types").then((r) => r.data),
};
