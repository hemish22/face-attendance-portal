"use client";

import { useState } from "react";
import { GitMerge, XCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { mediaUrl, type ResultResponse } from "@/lib/api";
import { useAssignCluster, useDismissCluster, useMergeCluster } from "@/lib/hooks";
import { MemberCombobox } from "@/components/event/member-combobox";

export function UnidentifiedTab({
  eventId,
  results,
  isLoading,
}: {
  eventId: string;
  results?: ResultResponse;
  isLoading: boolean;
}) {
  const assign = useAssignCluster(eventId);
  const merge = useMergeCluster(eventId);
  const dismiss = useDismissCluster(eventId);
  const [mergingId, setMergingId] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 pt-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-56 w-full" />
        ))}
      </div>
    );
  }

  const clusters = results?.unidentified ?? [];
  if (clusters.length === 0) {
    return <p className="pt-4 text-sm text-muted-foreground">No unidentified people.</p>;
  }

  return (
    <div className="grid grid-cols-1 gap-4 pt-4 sm:grid-cols-2 lg:grid-cols-3">
      {clusters.map((cluster) => (
        <Card key={cluster.cluster_id}>
          <CardHeader>
            <CardTitle className="flex items-center justify-between text-base">
              <span>{cluster.label}</span>
              <span className="text-sm font-normal text-muted-foreground">{cluster.appearances} photo(s)</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {cluster.crop_url && (
              // eslint-disable-next-line @next/next/no-img-element -- signed, expiring media URL from the API
              <img
                src={mediaUrl(cluster.crop_url)}
                alt={cluster.label}
                className="aspect-square w-24 self-center rounded-md object-cover"
              />
            )}

            {mergingId === cluster.cluster_id ? (
              <div className="flex items-center gap-2">
                <Select
                  onValueChange={(intoId) => {
                    merge.mutate({ clusterId: cluster.cluster_id, intoClusterId: intoId as string });
                    setMergingId(null);
                  }}
                >
                  <SelectTrigger className="flex-1">
                    <SelectValue placeholder="Merge into…" />
                  </SelectTrigger>
                  <SelectContent>
                    {clusters
                      .filter((c) => c.cluster_id !== cluster.cluster_id)
                      .map((c) => (
                        <SelectItem key={c.cluster_id} value={c.cluster_id}>
                          {c.label}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
                <Button variant="ghost" size="sm" onClick={() => setMergingId(null)}>
                  Cancel
                </Button>
              </div>
            ) : (
              <div className="flex flex-wrap items-center gap-2">
                <MemberCombobox
                  placeholder="Name it…"
                  onSelect={(memberId) => assign.mutate({ clusterId: cluster.cluster_id, memberId })}
                />
                <Button variant="outline" size="sm" onClick={() => setMergingId(cluster.cluster_id)}>
                  <GitMerge className="size-4" />
                  Merge into…
                </Button>
                <Button variant="ghost" size="sm" onClick={() => dismiss.mutate(cluster.cluster_id)}>
                  <XCircle className="size-4" />
                  Dismiss
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
