"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { uploadAttachment, type UploadedFile } from "../services/attachmentService";
import type { MessageAttachment } from "../types";

export type AttachmentStatus = "uploading" | "ready" | "failed";

export interface Attachment {
  /** Local id — stable across the upload lifecycle. */
  id: string;
  file: File;
  mimeType: string;
  status: AttachmentStatus;
  /** 0–100. Only meaningful while ``status === "uploading"``. */
  progress: number;
  /** Populated when status becomes ``"ready"``. */
  serverId?: string;
  /** Populated when status becomes ``"failed"``. */
  error?: string;
  /** Object URL for local previews (images). Revoked on remove/clear. */
  previewUrl?: string;
}

export interface UseAttachmentsResult {
  attachments: Attachment[];
  /** True while any upload is still in flight. Send button disables on this. */
  isBusy: boolean;
  add: (files: File[]) => void;
  remove: (id: string) => void;
  clear: () => void;
  /** Message-shaped metadata for ``ready`` attachments — contains id + name/mime/size. */
  ready: () => MessageAttachment[];
}

/** Hook that tracks a list of attachments. Uploads run in parallel; each one
 *  updates its own slot independently so users never wait for a slow upload
 *  to finish before seeing others progress. */
export function useAttachments(): UseAttachmentsResult {
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const controllersRef = useRef<Map<string, AbortController>>(new Map());

  // Revoke object URLs on unmount to avoid memory leaks
  useEffect(() => {
    return () => {
      attachments.forEach((a) => {
        if (a.previewUrl) URL.revokeObjectURL(a.previewUrl);
      });
    };
    // Intentionally run only on unmount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const patch = useCallback((id: string, patch: Partial<Attachment>) => {
    setAttachments((prev) =>
      prev.map((a) => (a.id === id ? { ...a, ...patch } : a)),
    );
  }, []);

  const uploadOne = useCallback(
    (id: string, file: File) => {
      const controller = new AbortController();
      controllersRef.current.set(id, controller);

      uploadAttachment(file, {
        signal: controller.signal,
        onProgress: (p) => patch(id, { progress: p }),
      })
        .then((result: UploadedFile) => {
          patch(id, {
            status: "ready",
            serverId: result.id,
            progress: 100,
          });
        })
        .catch((err) => {
          if (controller.signal.aborted) return; // removed during upload
          patch(id, {
            status: "failed",
            error: err?.response?.data?.detail ?? err?.message ?? "Upload failed",
          });
        })
        .finally(() => {
          controllersRef.current.delete(id);
        });
    },
    [patch],
  );

  const add = useCallback(
    (files: File[]) => {
      const next: Attachment[] = files.map((file) => ({
        id: crypto.randomUUID(),
        file,
        mimeType: file.type || "application/octet-stream",
        status: "uploading",
        progress: 0,
        previewUrl: file.type.startsWith("image/")
          ? URL.createObjectURL(file)
          : undefined,
      }));

      setAttachments((prev) => [...prev, ...next]);
      // Kick off all uploads in parallel — each updates its slot independently.
      next.forEach((a) => uploadOne(a.id, a.file));
    },
    [uploadOne],
  );

  const remove = useCallback((id: string) => {
    const controller = controllersRef.current.get(id);
    if (controller) {
      controller.abort();
      controllersRef.current.delete(id);
    }
    setAttachments((prev) => {
      const gone = prev.find((a) => a.id === id);
      if (gone?.previewUrl) URL.revokeObjectURL(gone.previewUrl);
      return prev.filter((a) => a.id !== id);
    });
  }, []);

  const clear = useCallback(() => {
    controllersRef.current.forEach((c) => c.abort());
    controllersRef.current.clear();
    setAttachments((prev) => {
      prev.forEach((a) => {
        if (a.previewUrl) URL.revokeObjectURL(a.previewUrl);
      });
      return [];
    });
  }, []);

  const ready = useCallback(
    (): MessageAttachment[] =>
      attachments
        .filter((a) => a.status === "ready" && a.serverId)
        .map((a) => ({
          id: a.serverId!,
          file_name: a.file.name,
          mime_type: a.mimeType,
          size: a.file.size,
        })),
    [attachments],
  );

  const isBusy = attachments.some((a) => a.status === "uploading");

  return { attachments, isBusy, add, remove, clear, ready };
}
