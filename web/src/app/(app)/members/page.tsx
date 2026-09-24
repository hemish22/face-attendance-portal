"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Plus, Search } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { MemberForm } from "@/components/member-form";
import { useMembers } from "@/lib/hooks";

function refBadge(count: number) {
  if (count === 0) return <Badge variant="destructive">Not enrolled</Badge>;
  if (count < 3) return <Badge className="bg-amber-500 text-white">{count} ref{count === 1 ? "" : "s"}</Badge>;
  return <Badge className="bg-green-600 text-white">{count} refs</Badge>;
}

export default function MembersPage() {
  const { data: members, isLoading } = useMembers();
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState(false);

  const filtered = useMemo(() => {
    if (!members) return [];
    const q = search.trim().toLowerCase();
    if (!q) return members;
    return members.filter((m) => m.name.toLowerCase().includes(q) || m.roll_no.toLowerCase().includes(q));
  }, [members, search]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-xl font-semibold">Members</h1>
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger render={<Button />}>
            <Plus className="size-4" />
            Add member
          </SheetTrigger>
          <SheetContent className="w-full sm:max-w-md overflow-y-auto p-4">
            <SheetHeader>
              <SheetTitle>Enroll a member</SheetTitle>
            </SheetHeader>
            <div className="mt-4">
              <MemberForm onDone={() => setOpen(false)} />
            </div>
          </SheetContent>
        </Sheet>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input placeholder="Search by name or roll no…" className="pl-8" value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      {isLoading ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <p className="text-sm text-muted-foreground">No members found.</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Roll No</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Dept</TableHead>
              <TableHead>Year</TableHead>
              <TableHead>Enrollment</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((m) => (
              <TableRow key={m.id} className="cursor-pointer">
                <TableCell>
                  <Link href={`/members/${m.id}`} className="block">
                    {m.roll_no}
                  </Link>
                </TableCell>
                <TableCell>
                  <Link href={`/members/${m.id}`} className="block">
                    {m.name}
                  </Link>
                </TableCell>
                <TableCell>{m.dept ?? "—"}</TableCell>
                <TableCell>{m.year ?? "—"}</TableCell>
                <TableCell>{refBadge(m.ref_count)}</TableCell>
                <TableCell>
                  {m.active ? <Badge variant="secondary">Active</Badge> : <Badge variant="outline">Inactive</Badge>}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
