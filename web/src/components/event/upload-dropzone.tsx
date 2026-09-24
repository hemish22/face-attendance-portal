"use client";

import { useCallback, useState } from "react";
import { useDropzone, type FileRejection } from "react-dropzone";
import toast from "react-hot-toast";
import { UploadCloud } from "lucide-react";

import { useUploadPhotos } from "@/lib/hooks";

const BATCH_SIZE = 5;
const CONCURRENCY = 2;

async function runWithConcurrency<T>(tasks: (() => Promise<T>)[], concurrency: number) {
  const queue = [...tasks];
  const workers = Array.from({ length: concurrency }, async () => {
    while (queue.length > 0) {
      const task = queue.shift();
      if (task) await task();
    }
  });
  await Promise.all(workers);
}

export function UploadDropzone({ eventId }: { eventId: string }) {
  const upload = useUploadPhotos(eventId);
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null);

  const onDrop = useCallback(
    async (accepted: File[], rejections: FileRejection[]) => {
      if (rejections.length > 0) {
        toast.error(`${rejections.length} file(s) skipped (not JPEG/PNG)`);
      }
      if (accepted.length === 0) return;

      const batches: File[][] = [];
      for (let i = 0; i < accepted.length; i += BATCH_SIZE) batches.push(accepted.slice(i, i + BATCH_SIZE));

      setProgress({ done: 0, total: accepted.length });
      let done = 0;
      let failed = 0;

      await runWithConcurrency(
        batches.map((batch) => async () => {
          const form = new FormData();
          batch.forEach((f) => form.append("files", f));
          try {
            await upload.mutateAsync(form);
          } catch {
            failed += batch.length;
          } finally {
            done += batch.length;
            setProgress({ done, total: accepted.length });
          }
        }),
        CONCURRENCY,
      );

      setProgress(null);
      if (failed > 0) toast.error(`${failed} photo(s) failed to upload`);
      else toast.success(`${accepted.length} photo(s) uploaded`);
    },
    [upload],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: { "image/jpeg": [], "image/png": [] },
    onDrop,
  });

  return (
    <div
      {...getRootProps()}
      className={`flex flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed p-6 text-center text-sm cursor-pointer transition-colors ${
        isDragActive ? "border-primary bg-accent" : "border-input"
      }`}
    >
      <input {...getInputProps()} />
      <UploadCloud className="size-5 text-muted-foreground" />
      {progress ? (
        <span>
          Uploading… {progress.done}/{progress.total}
        </span>
      ) : (
        <>
          <span>Drop event photos here, or click to browse</span>
          <span className="text-xs text-muted-foreground">JPEG or PNG, up to ~200 photos</span>
        </>
      )}
    </div>
  );
}
