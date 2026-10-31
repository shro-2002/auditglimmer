"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Button, Card, EmptyState, ErrorState, Skeleton } from "@/components/ui/primitives";
import { api, invalidateSession, queryKeys, urls } from "@/lib/api";
import { useSessionId } from "@/lib/use-session-id";

export default function ImagesPage() {
  const id = useSessionId();
  const queryClient = useQueryClient();
  const [files, setFiles] = useState<File[]>([]);
  const images = useQuery({ queryKey: queryKeys.images(id), queryFn: () => api.images(id) });
  const config = useQuery({ queryKey: queryKeys.config, queryFn: api.config });

  const upload = useMutation({
    mutationFn: (list: File[]) => api.uploadImages(id, list),
    onSuccess: () => {
      setFiles([]);
      invalidateSession(queryClient, id);
    },
  });

  const maxMb = config.data?.max_upload_mb;

  return (
    <div className="space-y-5">
      <Card title="Upload warehouse photos">
        <form
          className="flex flex-wrap items-end gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (files.length) upload.mutate(files);
          }}
        >
          <div>
            <label htmlFor="image-files" className="text-sm font-medium">
              PNG, JPEG or WebP{maxMb ? ` (≤ ${maxMb} MB each)` : ""}, up to 20 per session
            </label>
            <input
              id="image-files"
              type="file"
              multiple
              accept="image/png,image/jpeg,image/webp"
              className="mt-1 block text-sm text-ink-muted file:mr-3 file:min-h-10 file:rounded-md file:border file:border-line-strong file:bg-surface-3 file:px-3 file:text-ink"
              onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
            />
          </div>
          <Button type="submit" disabled={files.length === 0 || upload.isPending}>
            {upload.isPending ? "Uploading…" : `Upload ${files.length || ""} image${files.length === 1 ? "" : "s"}`}
          </Button>
        </form>
        <div aria-live="polite" className="mt-3">
          {upload.isError && <ErrorState title="Upload failed" error={upload.error} />}
          {upload.isSuccess && <p className="text-sm text-st-verified">Uploaded {upload.data.length} image(s).</p>}
        </div>
      </Card>

      <Card title={`Session images${images.data ? ` (${images.data.length})` : ""}`}>
        {images.isPending && (
          <div role="status" aria-label="Loading images" className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {Array.from({ length: 5 }, (_, i) => (
              <Skeleton key={i} className="aspect-[4/3] w-full" />
            ))}
          </div>
        )}
        {images.isError && <ErrorState error={images.error} onRetry={() => images.refetch()} />}
        {images.data?.length === 0 && (
          <EmptyState title="No images yet">Upload photos of the facility, or load the demo dataset from the Ledger tab.</EmptyState>
        )}
        {images.data && images.data.length > 0 && (
          <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {images.data.map((img) => (
              <li key={img.id} className="overflow-hidden rounded-md border border-line bg-surface-2">
                {/* eslint-disable-next-line @next/next/no-img-element -- dynamic API-hosted image */}
                <img
                  src={urls.image(img)}
                  alt={`Warehouse photo ${img.filename}`}
                  width={img.width}
                  height={img.height}
                  loading="lazy"
                  className="aspect-[4/3] w-full bg-canvas object-contain"
                />
                <div className="space-y-0.5 p-2 text-xs">
                  <p className="truncate font-medium" title={img.filename}>
                    {img.filename}
                  </p>
                  <p className="tabular text-ink-muted">
                    {img.width}×{img.height}
                    {img.fixture && <span className="ml-2 text-demo">synthetic demo fixture</span>}
                  </p>
                  <p className="truncate font-mono text-ink-faint" title={img.sha256}>
                    {img.sha256.slice(0, 16)}…
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
