"use client";

import { useMemo, useState } from "react";
import { Search } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { mediaUrl, type PersonResult, type ResultResponse } from "@/lib/api";
import { usePhotoThumbMap } from "@/lib/hooks";

type Row = {
  member_id: string;
  roll_no: string;
  name: string;
  status: "Present" | "Review" | "Absent";
  best_score: number | null;
  photos_matched: number;
  person?: PersonResult;
};

const STATUS_BADGE: Record<Row["status"], string> = {
  Present: "bg-green-600 text-white",
  Review: "bg-amber-500 text-white",
  Absent: "bg-destructive/10 text-destructive",
};

export function AttendanceTab({ results, isLoading }: { results?: ResultResponse; isLoading: boolean }) {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | Row["status"]>("all");
  const [selected, setSelected] = useState<Row | null>(null);
  const thumbs = usePhotoThumbMap(results);

  const rows: Row[] = useMemo(() => {
    if (!results) return [];
    const present = results.present.map((p) => ({
      member_id: p.member_id, roll_no: p.roll_no, name: p.name, status: "Present" as const,
      best_score: p.best_score, photos_matched: p.photos_matched, person: p,
    }));
    const review = results.needs_review.map((p) => ({
      member_id: p.member_id, roll_no: p.roll_no, name: p.name, status: "Review" as const,
      best_score: p.best_score, photos_matched: p.photos_matched, person: p,
    }));
    const absent = results.absent.map((a) => ({
      member_id: a.member_id, roll_no: a.roll_no, name: a.name, status: "Absent" as const,
      best_score: null, photos_matched: 0,
    }));
    return [...present, ...review, ...absent];
  }, [results]);

  const filtered = useMemo(() => {
    let out = rows;
    if (statusFilter !== "all") out = out.filter((r) => r.status === statusFilter);
    const q = search.trim().toLowerCase();
    if (q) out = out.filter((r) => r.name.toLowerCase().includes(q) || r.roll_no.toLowerCase().includes(q));
    return out.sort((a, b) => a.name.localeCompare(b.name));
  }, [rows, statusFilter, search]);

  if (isLoading) {
    return (
      <div className="flex flex-col gap-2 pt-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 pt-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative max-w-sm flex-1">
          <Search className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input placeholder="Search by name or roll no…" className="pl-8" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as typeof statusFilter)}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="Present">Present</SelectItem>
            <SelectItem value="Review">Review</SelectItem>
            <SelectItem value="Absent">Absent</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Roll No</TableHead>
            <TableHead>Name</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Best Match Score</TableHead>
            <TableHead>Photos Matched</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {filtered.map((r) => (
            <TableRow key={r.member_id} className="cursor-pointer" onClick={() => setSelected(r)}>
              <TableCell>{r.roll_no}</TableCell>
              <TableCell>{r.name}</TableCell>
              <TableCell>
                <Badge className={STATUS_BADGE[r.status]}>{r.status}</Badge>
              </TableCell>
              <TableCell>{r.best_score != null ? r.best_score.toFixed(2) : "—"}</TableCell>
              <TableCell>{r.photos_matched}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <Sheet open={!!selected} onOpenChange={(open) => !open && setSelected(null)}>
        <SheetContent className="w-full sm:max-w-md overflow-y-auto p-4">
          <SheetHeader>
            <SheetTitle>{selected?.name}</SheetTitle>
          </SheetHeader>
          <div className="mt-4 grid grid-cols-2 gap-2">
            {selected?.person?.photos.map((photo, i) => {
              const thumbUrl = thumbs.get(photo.photo_id)?.thumb_url;
              return (
                <div key={i} className="overflow-hidden rounded-md border">
                  {thumbUrl && (
                    // eslint-disable-next-line @next/next/no-img-element -- signed, expiring media URL from the API
                    <img src={mediaUrl(thumbUrl)} alt={photo.filename} className="aspect-square w-full object-cover" />
                  )}
                  <div className="p-2 text-xs">
                    <p className="truncate font-medium">{photo.filename}</p>
                    <p className="text-muted-foreground">
                      score {photo.score.toFixed(2)} · {photo.status}
                    </p>
                  </div>
                </div>
              );
            })}
            {!selected?.person && <p className="text-sm text-muted-foreground">No photos — this member is absent.</p>}
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
