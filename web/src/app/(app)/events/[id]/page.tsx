"use client";

import { useParams, useRouter, useSearchParams } from "next/navigation";

import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EventHeader } from "@/components/event/event-header";
import { UploadDropzone } from "@/components/event/upload-dropzone";
import { AttendanceTab } from "@/components/event/attendance-tab";
import { PeopleTab } from "@/components/event/people-tab";
import { PhotosTab } from "@/components/event/photos-tab";
import { ReviewTab } from "@/components/event/review-tab";
import { UnidentifiedTab } from "@/components/event/unidentified-tab";
import { useEvent, useEventResults, useEventStatus } from "@/lib/hooks";

const TABS = ["attendance", "people", "photos", "review", "unidentified"] as const;
type Tab = (typeof TABS)[number];

export default function EventDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const tab = (searchParams.get("tab") as Tab) && TABS.includes(searchParams.get("tab") as Tab)
    ? (searchParams.get("tab") as Tab)
    : "attendance";

  const { data: event, isLoading: eventLoading } = useEvent(id);
  const isProcessing = event?.status === "processing";
  const { data: status } = useEventStatus(id, isProcessing || event?.status === "draft");
  const { data: results, isLoading: resultsLoading } = useEventResults(id);

  function setTab(next: Tab) {
    router.push(`/events/${id}?tab=${next}`);
  }

  if (eventLoading) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (!event) {
    return <p className="text-sm text-muted-foreground">Event not found.</p>;
  }

  return (
    <div className="flex flex-col gap-6">
      <EventHeader event={event} status={status} />

      {event.status !== "final" && <UploadDropzone eventId={event.id} />}

      <Tabs value={tab} onValueChange={(v) => setTab(v as Tab)}>
        <TabsList>
          <TabsTrigger value="attendance">Attendance</TabsTrigger>
          <TabsTrigger value="people">People</TabsTrigger>
          <TabsTrigger value="photos">Photos</TabsTrigger>
          <TabsTrigger value="review">
            Review{results && results.summary.needs_review > 0 ? ` (${results.summary.needs_review})` : ""}
          </TabsTrigger>
          <TabsTrigger value="unidentified">
            Unidentified{results && results.summary.unidentified > 0 ? ` (${results.summary.unidentified})` : ""}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="attendance">
          <AttendanceTab results={results} isLoading={resultsLoading} />
        </TabsContent>
        <TabsContent value="people">
          <PeopleTab results={results} isLoading={resultsLoading} />
        </TabsContent>
        <TabsContent value="photos">
          <PhotosTab results={results} isLoading={resultsLoading} />
        </TabsContent>
        <TabsContent value="review">
          <ReviewTab eventId={event.id} />
        </TabsContent>
        <TabsContent value="unidentified">
          <UnidentifiedTab eventId={event.id} results={results} isLoading={resultsLoading} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
