"use client";

import Link from "next/link";
import { Plus } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useEvents } from "@/lib/hooks";
import type { EventOut } from "@/lib/api";

const STATUS_VARIANT: Record<EventOut["status"], "outline" | "secondary" | "default"> = {
  draft: "outline",
  processing: "secondary",
  review: "secondary",
  final: "default",
};

export default function EventsPage() {
  const { data: events, isLoading } = useEvents();

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Events</h1>
        <Button render={<Link href="/events/new" />}>
          <Plus className="size-4" />
          New event
        </Button>
      </div>

      {isLoading ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      ) : !events || events.length === 0 ? (
        <p className="text-sm text-muted-foreground">No events yet. Create one to get started.</p>
      ) : (
        <div className="flex flex-col gap-2">
          {events.map((event) => (
            <Link key={event.id} href={`/events/${event.id}`}>
              <Card className="flex-row items-center justify-between p-4 hover:bg-accent/50 transition-colors">
                <div>
                  <p className="font-medium">{event.name}</p>
                  <p className="text-sm text-muted-foreground">{event.date}</p>
                </div>
                <Badge variant={STATUS_VARIANT[event.status]} className="capitalize">
                  {event.status}
                </Badge>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
