"use client";

import { useState } from "react";

import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { mediaUrl, type PhotoIndexEntry, type ResultResponse } from "@/lib/api";
import { FaceOverlay } from "@/components/event/face-overlay";

export function PhotosTab({ results, isLoading }: { results?: ResultResponse; isLoading: boolean }) {
  const [selected, setSelected] = useState<PhotoIndexEntry | null>(null);

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-3 pt-4 sm:grid-cols-4 lg:grid-cols-6">
        {Array.from({ length: 12 }).map((_, i) => (
          <Skeleton key={i} className="aspect-square w-full" />
        ))}
      </div>
    );
  }

  if (!results || results.photos.length === 0) {
    return <p className="pt-4 text-sm text-muted-foreground">No photos uploaded yet.</p>;
  }

  return (
    <>
      <div className="grid grid-cols-2 gap-3 pt-4 sm:grid-cols-4 lg:grid-cols-6">
        {results.photos.map((photo) => (
          <button
            key={photo.photo_id}
            type="button"
            onClick={() => setSelected(photo)}
            className="group relative overflow-hidden rounded-md border"
          >
            {photo.thumb_url && (
              // eslint-disable-next-line @next/next/no-img-element -- signed, expiring media URL from the API
              <img src={mediaUrl(photo.thumb_url)} alt={photo.filename} className="aspect-square w-full object-cover" />
            )}
            <span className="absolute inset-x-0 bottom-0 truncate bg-black/60 px-1.5 py-0.5 text-[10px] text-white">
              {photo.filename} · {photo.people.length} {photo.people.length === 1 ? "person" : "people"}
            </span>
          </button>
        ))}
      </div>

      <Dialog open={!!selected} onOpenChange={(open) => !open && setSelected(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{selected?.filename}</DialogTitle>
          </DialogHeader>
          {selected?.photo_url && (
            <FaceOverlay photoUrl={mediaUrl(selected.photo_url)} people={selected.people} alt={selected.filename} />
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
