"use client";

import { useEffect, useMemo, useState } from "react";
import { Check, SkipForward, UserPlus, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Kbd } from "@/components/ui/kbd";
import { Skeleton } from "@/components/ui/skeleton";
import { mediaUrl } from "@/lib/api";
import { useMembers, useResolveFace, useReviewQueue } from "@/lib/hooks";
import { MemberCombobox } from "@/components/event/member-combobox";

export function ReviewTab({ eventId }: { eventId: string }) {
  const { data: queue, isLoading } = useReviewQueue(eventId);
  const { data: members } = useMembers();
  const resolve = useResolveFace(eventId);
  const [skipped, setSkipped] = useState<Set<string>>(new Set());
  const [assigning, setAssigning] = useState(false);

  const ordered = useMemo(() => {
    if (!queue) return [];
    const notSkipped = queue.filter((f) => !skipped.has(f.face_id));
    const wasSkipped = queue.filter((f) => skipped.has(f.face_id));
    return [...notSkipped, ...wasSkipped];
  }, [queue, skipped]);

  const current = ordered[0];
  const membersById = useMemo(() => new Map((members ?? []).map((m) => [m.id, m])), [members]);

  function confirm() {
    if (!current || !current.candidates[0]) return;
    resolve.mutate({ faceId: current.face_id, action: "confirm" });
  }
  function reject() {
    if (!current) return;
    resolve.mutate({ faceId: current.face_id, action: "reject" });
  }
  function assignTo(memberId: string) {
    if (!current) return;
    resolve.mutate({ faceId: current.face_id, action: "assign", memberId });
    setAssigning(false);
  }
  function skip() {
    if (!current) return;
    setSkipped((prev) => new Set(prev).add(current.face_id));
  }

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (!current || assigning) return;
      if (e.target instanceof HTMLElement && ["INPUT", "TEXTAREA"].includes(e.target.tagName)) return;
      if (e.key === "y" || e.key === "Y") confirm();
      else if (e.key === "n" || e.key === "N") reject();
      else if (e.key === "a" || e.key === "A") setAssigning(true);
      else if (e.key === "s" || e.key === "S") skip();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current, assigning]);

  if (isLoading) {
    return <Skeleton className="mt-4 h-96 w-full" />;
  }

  if (!current) {
    return <p className="pt-4 text-sm text-muted-foreground">Review queue is empty.</p>;
  }

  const top = current.candidates[0];
  const runnerUp = current.candidates[1];

  return (
    <div className="flex flex-col items-center gap-4 pt-4">
      <p className="text-sm text-muted-foreground">{ordered.length} face(s) remaining in the queue</p>

      <div className="flex w-full max-w-2xl items-stretch justify-center gap-4">
        <Card className="flex-1 items-center gap-2 p-4">
          <p className="text-xs font-medium text-muted-foreground">Detected face</p>
          {/* eslint-disable-next-line @next/next/no-img-element -- signed, expiring media URL from the API */}
          <img src={mediaUrl(current.crop_url)} alt="Detected face" className="aspect-square w-40 rounded-md object-cover" />
        </Card>

        {top && (
          <Card className="flex-1 items-center gap-2 p-4">
            <p className="text-xs font-medium text-muted-foreground">
              Candidate: {membersById.get(top.member_id)?.name ?? top.name} ({top.score.toFixed(2)})
            </p>
            {/* eslint-disable-next-line @next/next/no-img-element -- signed, expiring media URL from the API */}
            <img src={mediaUrl(top.ref_photo_url)} alt={top.name} className="aspect-square w-40 rounded-md object-cover" />
          </Card>
        )}
      </div>

      {runnerUp && (
        <p className="text-xs text-muted-foreground">
          Runner-up: {runnerUp.name} ({runnerUp.score.toFixed(2)})
        </p>
      )}

      {assigning ? (
        <div className="flex items-center gap-2">
          <MemberCombobox onSelect={assignTo} placeholder="Assign to member…" />
          <Button variant="ghost" size="sm" onClick={() => setAssigning(false)}>
            Cancel
          </Button>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <Button onClick={confirm} disabled={!top || resolve.isPending}>
            <Check className="size-4" />
            Confirm <Kbd>Y</Kbd>
          </Button>
          <Button variant="outline" onClick={reject} disabled={resolve.isPending}>
            <X className="size-4" />
            Reject <Kbd>N</Kbd>
          </Button>
          <Button variant="outline" onClick={() => setAssigning(true)} disabled={resolve.isPending}>
            <UserPlus className="size-4" />
            Assign <Kbd>A</Kbd>
          </Button>
          <Button variant="ghost" onClick={skip} disabled={resolve.isPending}>
            <SkipForward className="size-4" />
            Skip <Kbd>S</Kbd>
          </Button>
        </div>
      )}
    </div>
  );
}
