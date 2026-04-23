"use client";

import { apiClient } from "@/lib/api/client";

export interface UploadedFile {
  id: string;
  original_name: string;
  mime_type: string;
  size: number;
  type: string; // upload config type (e.g. "attachment")
  storage_key?: string;
}

export interface UploadOptions {
  /** Called with 0–100 as the upload progresses. */
  onProgress?: (percent: number) => void;
  /** AbortSignal so callers can cancel an in-flight upload. */
  signal?: AbortSignal;
}

/**
 * Upload one attachment. Posts to the existing ``/upload`` endpoint with
 * ``type="attachment"`` so the uploads config enforces MIME + size limits.
 */
export async function uploadAttachment(
  file: File,
  options: UploadOptions = {},
): Promise<UploadedFile> {
  const form = new FormData();
  form.append("file", file);
  form.append("type", "attachment");

  const response = await apiClient.post<UploadedFile>("/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
    signal: options.signal,
    onUploadProgress: (evt) => {
      if (!options.onProgress || !evt.total) return;
      const pct = Math.round((evt.loaded / evt.total) * 100);
      options.onProgress(Math.min(100, pct));
    },
  });
  return response.data;
}
