"use client";

import { useParams, useRouter } from "next/navigation";
import { useRef } from "react";
import toast from "react-hot-toast";
import { Trash2, UploadCloud } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogClose,
} from "@/components/ui/dialog";
import { mediaUrl, ApiError } from "@/lib/api";
import {
  useAddMemberRefs,
  useDeleteMember,
  useDeleteMemberRef,
  useMember,
  useMemberRefs,
} from "@/lib/hooks";

export default function MemberDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data: member, isLoading } = useMember(id);
  const { data: refs, isLoading: refsLoading } = useMemberRefs(id);
  const addRefs = useAddMemberRefs(id);
  const deleteRef = useDeleteMemberRef(id);
  const deleteMember = useDeleteMember();
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function onFilesChosen(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    const form = new FormData();
    Array.from(files).forEach((f) => form.append("files", f));
    try {
      const results = await addRefs.mutateAsync(form);
      const rejected = results.filter((r) => !r.accepted);
      if (rejected.length === 0) toast.success("Photo(s) added");
      else toast(`${rejected.length} photo(s) rejected: ${rejected.map((r) => r.reason).join("; ")}`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to add photos");
    } finally {
      e.target.value = "";
    }
  }

  async function onDeleteMember() {
    await deleteMember.mutateAsync(id);
    router.push("/members");
  }

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (!member) {
    return <p className="text-sm text-muted-foreground">Member not found.</p>;
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold">{member.name}</h1>
          <p className="text-sm text-muted-foreground">
            {member.roll_no} {member.dept ? `· ${member.dept}` : ""} {member.year ? `· ${member.year}` : ""}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {member.active ? <Badge variant="secondary">Active</Badge> : <Badge variant="outline">Inactive</Badge>}
          <Dialog>
            <DialogTrigger render={<Button variant="destructive" size="sm" />}>
              <Trash2 className="size-4" />
              Delete
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Delete {member.name}?</DialogTitle>
              </DialogHeader>
              <p className="text-sm text-muted-foreground">
                This removes all reference photos and unlinks their faces from past events. This cannot be undone.
              </p>
              <DialogFooter>
                <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
                <Button variant="destructive" onClick={onDeleteMember} disabled={deleteMember.isPending}>
                  {deleteMember.isPending ? "Deleting…" : "Delete member"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-medium">Reference photos ({refs?.length ?? 0})</h2>
          <Button variant="outline" size="sm" onClick={() => fileInputRef.current?.click()} disabled={addRefs.isPending}>
            <UploadCloud className="size-4" />
            Add photos
          </Button>
          <input ref={fileInputRef} type="file" accept="image/jpeg,image/png" multiple hidden onChange={onFilesChosen} />
        </div>

        {refsLoading ? (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 md:grid-cols-6">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="aspect-square w-full" />
            ))}
          </div>
        ) : !refs || refs.length === 0 ? (
          <p className="text-sm text-muted-foreground">No reference photos yet.</p>
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 md:grid-cols-6">
            {refs.map((ref) => (
              <Card key={ref.id} className="group relative overflow-hidden p-0">
                {/* eslint-disable-next-line @next/next/no-img-element -- signed, expiring media URL from the API */}
                <img src={mediaUrl(ref.photo_url)} alt="" className="aspect-square w-full object-cover" />
                <div className="absolute inset-x-0 bottom-0 flex items-center justify-between gap-1 bg-black/60 px-1.5 py-1 text-[10px] text-white">
                  <span>{ref.source}</span>
                  <button
                    type="button"
                    onClick={() => deleteRef.mutate(ref.id)}
                    className="opacity-0 transition-opacity group-hover:opacity-100"
                    aria-label="Remove reference photo"
                  >
                    <Trash2 className="size-3.5" />
                  </button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
