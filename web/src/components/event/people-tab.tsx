"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Carousel, CarouselContent, CarouselItem, CarouselNext, CarouselPrevious } from "@/components/ui/carousel";
import { Skeleton } from "@/components/ui/skeleton";
import { mediaUrl, type ResultResponse } from "@/lib/api";
import { usePhotoThumbMap } from "@/lib/hooks";

const STATUS_BADGE: Record<string, string> = {
  auto: "bg-green-600 text-white",
  confirmed: "bg-green-600 text-white",
  review: "bg-amber-500 text-white",
  unknown: "border border-destructive text-destructive",
};

export function PeopleTab({ results, isLoading }: { results?: ResultResponse; isLoading: boolean }) {
  const thumbs = usePhotoThumbMap(results);

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 pt-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-48 w-full" />
        ))}
      </div>
    );
  }

  const people = [
    ...(results?.present ?? []).map((p) => ({ id: p.member_id, name: p.name, photos: p.photos })),
    ...(results?.needs_review ?? []).map((p) => ({ id: p.member_id, name: p.name, photos: p.photos })),
    ...(results?.unidentified ?? []).map((u) => ({ id: u.cluster_id, name: u.label, photos: u.photos.map((p) => ({ ...p, score: 0, status: "unknown" as const })) })),
  ];

  if (people.length === 0) {
    return <p className="pt-4 text-sm text-muted-foreground">No matched people yet.</p>;
  }

  return (
    <div className="grid grid-cols-1 gap-4 pt-4 sm:grid-cols-2 lg:grid-cols-3">
      {people.map((person) => (
        <Card key={person.id}>
          <CardHeader>
            <CardTitle className="flex items-center justify-between text-base">
              <span className="truncate">{person.name}</span>
              <span className="text-sm font-normal text-muted-foreground">{person.photos.length} photo(s)</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Carousel opts={{ align: "start" }}>
              <CarouselContent>
                {person.photos.map((photo, i) => {
                  const thumbUrl = thumbs.get(photo.photo_id)?.thumb_url;
                  return (
                    <CarouselItem key={i} className="basis-1/2">
                      <div className="overflow-hidden rounded-md border">
                        {thumbUrl && (
                          // eslint-disable-next-line @next/next/no-img-element -- signed, expiring media URL from the API
                          <img src={mediaUrl(thumbUrl)} alt={photo.filename} className="aspect-square w-full object-cover" />
                        )}
                        <div className="p-1.5">
                          <Badge className={STATUS_BADGE[photo.status] ?? ""}>{photo.status}</Badge>
                        </div>
                      </div>
                    </CarouselItem>
                  );
                })}
              </CarouselContent>
              {person.photos.length > 2 && (
                <>
                  <CarouselPrevious />
                  <CarouselNext />
                </>
              )}
            </Carousel>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
