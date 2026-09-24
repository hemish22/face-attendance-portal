"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api";
import { useCreateEvent } from "@/lib/hooks";

export default function NewEventPage() {
  const router = useRouter();
  const createEvent = useCreateEvent();
  const [name, setName] = useState("");
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      const event = await createEvent.mutateAsync({ name, date });
      router.push(`/events/${event.id}`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to create event");
    }
  }

  return (
    <div className="flex max-w-md flex-col gap-4">
      <h1 className="text-xl font-semibold">New event</h1>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Event details</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="name">Name</Label>
              <Input id="name" required value={name} onChange={(e) => setName(e.target.value)} placeholder="Workshop 1" />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="date">Date</Label>
              <Input id="date" type="date" required value={date} onChange={(e) => setDate(e.target.value)} />
            </div>
            <Button type="submit" disabled={createEvent.isPending}>
              {createEvent.isPending ? "Creating…" : "Create event"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
