"use client";

import { useState } from "react";
import { useDropzone } from "react-dropzone";
import toast from "react-hot-toast";
import { UploadCloud, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, type MemberFileResult } from "@/lib/api";
import { useCreateMember } from "@/lib/hooks";

export function MemberForm({ onDone }: { onDone: () => void }) {
  const [rollNo, setRollNo] = useState("");
  const [name, setName] = useState("");
  const [dept, setDept] = useState("");
  const [year, setYear] = useState("");
  const [consent, setConsent] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [results, setResults] = useState<MemberFileResult[] | null>(null);
  const createMember = useCreateMember();

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: { "image/jpeg": [], "image/png": [] },
    onDrop: (accepted) => setFiles((prev) => [...prev, ...accepted]),
  });

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!consent) {
      toast.error("Consent is required to enroll a member");
      return;
    }
    if (files.length === 0) {
      toast.error("Add at least one enrollment photo");
      return;
    }

    const form = new FormData();
    form.set("roll_no", rollNo);
    form.set("name", name);
    if (dept) form.set("dept", dept);
    if (year) form.set("year", year);
    form.set("consent", "true");
    files.forEach((f) => form.append("files", f));

    try {
      const res = await createMember.mutateAsync(form);
      setResults(res.files);
      const rejected = res.files.filter((f) => !f.accepted).length;
      if (rejected === 0) {
        toast.success(`${name} enrolled`);
        onDone();
      } else {
        toast(`${name} created — ${rejected} photo(s) rejected, see reasons below`);
      }
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Failed to create member");
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col gap-2">
          <Label htmlFor="roll_no">Roll No</Label>
          <Input id="roll_no" required value={rollNo} onChange={(e) => setRollNo(e.target.value)} />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="name">Name</Label>
          <Input id="name" required value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="dept">Department</Label>
          <Input id="dept" value={dept} onChange={(e) => setDept(e.target.value)} />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="year">Year</Label>
          <Input id="year" value={year} onChange={(e) => setYear(e.target.value)} />
        </div>
      </div>

      <div
        {...getRootProps()}
        className={`flex flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed p-6 text-center text-sm cursor-pointer transition-colors ${
          isDragActive ? "border-primary bg-accent" : "border-input"
        }`}
      >
        <input {...getInputProps()} />
        <UploadCloud className="size-5 text-muted-foreground" />
        <span>Drop enrollment photos here, or click to browse</span>
        <span className="text-xs text-muted-foreground">JPEG or PNG, one clear face per photo</span>
      </div>

      {files.length > 0 && (
        <ul className="flex flex-col gap-1">
          {files.map((f, i) => (
            <li key={i} className="flex items-center justify-between rounded-md bg-muted px-2 py-1 text-sm">
              <span className="truncate">{f.name}</span>
              <button
                type="button"
                onClick={() => setFiles((prev) => prev.filter((_, idx) => idx !== i))}
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="size-4" />
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="flex items-center gap-2">
        <Checkbox id="consent" checked={consent} onCheckedChange={(v) => setConsent(v === true)} />
        <Label htmlFor="consent" className="font-normal">
          Member has consented to face data storage and processing
        </Label>
      </div>

      {results && (
        <ul className="flex flex-col gap-1 rounded-md border p-2 text-sm">
          {results.map((r, i) => (
            <li key={i} className={r.accepted ? "text-green-600" : "text-destructive"}>
              {r.filename}: {r.accepted ? "accepted" : r.reason}
            </li>
          ))}
        </ul>
      )}

      <Button type="submit" disabled={createMember.isPending}>
        {createMember.isPending ? "Enrolling…" : "Enroll member"}
      </Button>
    </form>
  );
}
