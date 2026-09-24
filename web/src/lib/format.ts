export const STATUS_BADGE: Record<string, string> = {
  auto: "bg-green-100 text-green-800 border-green-300",
  confirmed: "bg-green-100 text-green-800 border-green-300",
  review: "bg-amber-100 text-amber-800 border-amber-300",
  unknown: "bg-red-100 text-red-800 border-red-300",
  present: "bg-green-100 text-green-800 border-green-300",
  needs_review: "bg-amber-100 text-amber-800 border-amber-300",
  absent: "bg-red-100 text-red-800 border-red-300",
  draft: "bg-zinc-100 text-zinc-800 border-zinc-300",
  processing: "bg-blue-100 text-blue-800 border-blue-300",
  final: "bg-green-100 text-green-800 border-green-300",
};

export function scorePercent(score: number | null | undefined): string {
  if (score == null) return "—";
  return `${Math.round(score * 100)}%`;
}
