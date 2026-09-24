import type { components } from "./api-types";

export type MemberOut = components["schemas"]["MemberOut"];
export type MemberCreateResponse = components["schemas"]["MemberCreateResponse"];
export type MemberFileResult = components["schemas"]["MemberFileResult"];
export type MemberRefOut = components["schemas"]["MemberRefOut"];
export type EventOut = components["schemas"]["EventOut"];
export type EventStatus = components["schemas"]["EventStatus"];
export type ResultResponse = components["schemas"]["ResultResponse"];
export type ReviewFaceOut = components["schemas"]["ReviewFaceOut"];
export type PersonResult = components["schemas"]["PersonResult"];
export type UnidentifiedCluster = components["schemas"]["UnidentifiedCluster"];
export type PhotoIndexEntry = components["schemas"]["PhotoIndexEntry"];
export type PhotoPerson = components["schemas"]["PhotoPerson"];
export type AbsentMember = components["schemas"]["AbsentMember"];

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem("token", token);
  else localStorage.removeItem("token");
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const headers = new Headers(init?.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init?.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API_URL}${path}`, { ...init, headers });

  if (res.status === 401) {
    setToken(null);
    if (typeof window !== "undefined") window.location.href = "/login";
    throw new ApiError(401, "Unauthorized");
  }

  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      message = body.detail ? (typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail)) : message;
    } catch {
      // response body wasn't JSON; fall back to statusText
    }
    throw new ApiError(res.status, message);
  }

  if (res.status === 204) return undefined as T;
  const contentType = res.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) return res.json();
  return undefined as T;
}

export const api = {
  login: (email: string, password: string) =>
    request<components["schemas"]["LoginResponse"]>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  listMembers: () => request<MemberOut[]>("/members"),
  createMember: (form: FormData) => request<MemberCreateResponse>("/members", { method: "POST", body: form }),
  importMembers: (form: FormData) => request<MemberCreateResponse[]>("/members/import", { method: "POST", body: form }),
  deleteMember: (id: string) => request(`/members/${id}`, { method: "DELETE" }),
  getMember: (id: string) => request<MemberOut>(`/members/${id}`),
  listMemberRefs: (id: string) => request<MemberRefOut[]>(`/members/${id}/refs`),
  addMemberRefs: (id: string, form: FormData) =>
    request<MemberFileResult[]>(`/members/${id}/refs`, { method: "POST", body: form }),
  deleteMemberRef: (memberId: string, refId: string) =>
    request(`/members/${memberId}/refs/${refId}`, { method: "DELETE" }),

  listEvents: () => request<EventOut[]>("/events"),
  createEvent: (name: string, date: string) =>
    request<EventOut>("/events", { method: "POST", body: JSON.stringify({ name, date }) }),
  getEvent: (id: string) => request<EventOut>(`/events/${id}`),

  uploadPhotos: (eventId: string, form: FormData) =>
    request<{ photo_ids: string[] }>(`/events/${eventId}/photos`, { method: "POST", body: form }),

  processEvent: (eventId: string) => request(`/events/${eventId}/process`, { method: "POST" }),
  rematchEvent: (eventId: string) => request(`/events/${eventId}/rematch`, { method: "POST" }),
  getEventStatus: (eventId: string) => request<EventStatus>(`/events/${eventId}/status`),
  getEventResults: (eventId: string) => request<ResultResponse>(`/events/${eventId}/results`),
  finalizeEvent: (eventId: string) => request<ResultResponse>(`/events/${eventId}/finalize`, { method: "POST" }),

  getReviewQueue: (eventId: string) => request<ReviewFaceOut[]>(`/events/${eventId}/review`),
  resolveFace: (faceId: string, action: "confirm" | "reject" | "assign", memberId?: string) =>
    request(`/faces/${faceId}/resolve`, { method: "POST", body: JSON.stringify({ action, member_id: memberId }) }),

  assignCluster: (clusterId: string, memberId: string) =>
    request(`/clusters/${clusterId}/assign`, { method: "POST", body: JSON.stringify({ member_id: memberId }) }),
  mergeCluster: (clusterId: string, intoClusterId: string) =>
    request(`/clusters/${clusterId}/merge`, { method: "POST", body: JSON.stringify({ into_cluster_id: intoClusterId }) }),
  dismissCluster: (clusterId: string) => request(`/clusters/${clusterId}/dismiss`, { method: "POST" }),

  getPhotoFaces: (photoId: string) =>
    request<{ face_id: string; bbox: number[]; status: string; member_id: string | null; score: number | null }[]>(
      `/photos/${photoId}/faces`
    ),
};

/** GET /events/{id}/export needs a Bearer header, which a plain <a href> can't
 * send — fetch the blob ourselves and trigger the browser's save dialog. */
export async function downloadExport(eventId: string, format: "json" | "xlsx", filename: string) {
  const token = getToken();
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_URL}/events/${eventId}/export?format=${format}`, { headers });
  if (!res.ok) throw new ApiError(res.status, res.statusText);

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/** Media URLs from the API are relative, signed paths (e.g. "/media/...?exp=&sig="). */
export function mediaUrl(pathOrUrl: string): string {
  if (pathOrUrl.startsWith("http")) return pathOrUrl;
  return `${API_URL}${pathOrUrl}`;
}

export { API_URL };
