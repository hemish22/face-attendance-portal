import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";

import { api } from "./api";
import type { ResultResponse } from "./api";

/** present[].photos / unidentified[].photos only carry photo_id + filename —
 * look the thumbnail up from the top-level photos[] index in the same payload. */
export function usePhotoThumbMap(results: ResultResponse | undefined) {
  return useMemo(() => {
    const map = new Map<string, { photo_url?: string | null; thumb_url?: string | null }>();
    results?.photos.forEach((p) => map.set(p.photo_id, { photo_url: p.photo_url, thumb_url: p.thumb_url }));
    return map;
  }, [results]);
}

export function useMembers() {
  return useQuery({ queryKey: ["members"], queryFn: api.listMembers });
}

export function useCreateMember() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (form: FormData) => api.createMember(form),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["members"] }),
  });
}

export function useMember(memberId: string) {
  return useQuery({ queryKey: ["members", memberId], queryFn: () => api.getMember(memberId), enabled: !!memberId });
}

export function useMemberRefs(memberId: string) {
  return useQuery({ queryKey: ["members", memberId, "refs"], queryFn: () => api.listMemberRefs(memberId), enabled: !!memberId });
}

export function useAddMemberRefs(memberId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (form: FormData) => api.addMemberRefs(memberId, form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["members", memberId, "refs"] });
      qc.invalidateQueries({ queryKey: ["members"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useDeleteMemberRef(memberId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (refId: string) => api.deleteMemberRef(memberId, refId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["members", memberId, "refs"] });
      qc.invalidateQueries({ queryKey: ["members"] });
      toast.success("Reference photo removed");
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useDeleteMember() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteMember(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["members"] });
      toast.success("Member deleted");
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useEvents() {
  return useQuery({ queryKey: ["events"], queryFn: api.listEvents });
}

export function useEvent(eventId: string) {
  return useQuery({ queryKey: ["events", eventId], queryFn: () => api.getEvent(eventId), enabled: !!eventId });
}

export function useCreateEvent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, date }: { name: string; date: string }) => api.createEvent(name, date),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["events"] }),
  });
}

export function useEventStatus(eventId: string, polling: boolean) {
  return useQuery({
    queryKey: ["events", eventId, "status"],
    queryFn: () => api.getEventStatus(eventId),
    enabled: !!eventId,
    refetchInterval: polling ? 2000 : false,
  });
}

export function useEventResults(eventId: string) {
  return useQuery({ queryKey: ["events", eventId, "results"], queryFn: () => api.getEventResults(eventId), enabled: !!eventId });
}

export function useReviewQueue(eventId: string) {
  return useQuery({ queryKey: ["events", eventId, "review"], queryFn: () => api.getReviewQueue(eventId), enabled: !!eventId });
}

function useEventInvalidator(eventId: string) {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: ["events", eventId] });
  };
}

export function useUploadPhotos(eventId: string) {
  const invalidate = useEventInvalidator(eventId);
  return useMutation({
    mutationFn: (form: FormData) => api.uploadPhotos(eventId, form),
    onSuccess: invalidate,
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useProcessEvent(eventId: string) {
  const invalidate = useEventInvalidator(eventId);
  return useMutation({
    mutationFn: () => api.processEvent(eventId),
    onSuccess: () => {
      invalidate();
      toast.success("Processing started");
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useRematchEvent(eventId: string) {
  const invalidate = useEventInvalidator(eventId);
  return useMutation({
    mutationFn: () => api.rematchEvent(eventId),
    onSuccess: () => {
      invalidate();
      toast.success("Rematch started");
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useFinalizeEvent(eventId: string) {
  const invalidate = useEventInvalidator(eventId);
  return useMutation({
    mutationFn: () => api.finalizeEvent(eventId),
    onSuccess: () => {
      invalidate();
      toast.success("Event finalized");
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useResolveFace(eventId: string) {
  const invalidate = useEventInvalidator(eventId);
  return useMutation({
    mutationFn: ({ faceId, action, memberId }: { faceId: string; action: "confirm" | "reject" | "assign"; memberId?: string }) =>
      api.resolveFace(faceId, action, memberId),
    onSuccess: invalidate,
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useAssignCluster(eventId: string) {
  const invalidate = useEventInvalidator(eventId);
  return useMutation({
    mutationFn: ({ clusterId, memberId }: { clusterId: string; memberId: string }) => api.assignCluster(clusterId, memberId),
    onSuccess: () => {
      invalidate();
      toast.success("Assigned");
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useMergeCluster(eventId: string) {
  const invalidate = useEventInvalidator(eventId);
  return useMutation({
    mutationFn: ({ clusterId, intoClusterId }: { clusterId: string; intoClusterId: string }) =>
      api.mergeCluster(clusterId, intoClusterId),
    onSuccess: () => {
      invalidate();
      toast.success("Merged");
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useDismissCluster(eventId: string) {
  const invalidate = useEventInvalidator(eventId);
  return useMutation({
    mutationFn: (clusterId: string) => api.dismissCluster(clusterId),
    onSuccess: () => {
      invalidate();
      toast.success("Dismissed");
    },
    onError: (e: Error) => toast.error(e.message),
  });
}
