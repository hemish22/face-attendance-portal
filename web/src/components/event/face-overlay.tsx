"use client";

import { useState } from "react";
import type { PhotoPerson } from "@/lib/api";

const STATUS_COLOR: Record<PhotoPerson["status"], string> = {
  auto: "border-green-500",
  confirmed: "border-green-500",
  review: "border-amber-500",
  unknown: "border-destructive border-dashed",
};

export function FaceOverlay({ photoUrl, people, alt }: { photoUrl: string; people: PhotoPerson[]; alt: string }) {
  const [selected, setSelected] = useState<number | null>(null);

  return (
    <div className="relative w-full">
      {/* eslint-disable-next-line @next/next/no-img-element -- signed, expiring media URL from the API */}
      <img src={photoUrl} alt={alt} className="w-full rounded-md" />
      {people.map((person, i) => {
        const [x1, y1, x2, y2] = person.bbox;
        const isSelected = selected === i;
        return (
          <button
            key={i}
            type="button"
            onClick={() => setSelected(isSelected ? null : i)}
            className={`absolute border-2 ${STATUS_COLOR[person.status]} ${isSelected ? "ring-2 ring-offset-1 ring-primary" : ""} transition-shadow`}
            style={{
              left: `${x1 * 100}%`,
              top: `${y1 * 100}%`,
              width: `${(x2 - x1) * 100}%`,
              height: `${(y2 - y1) * 100}%`,
            }}
          >
            <span className="absolute -top-5 left-0 whitespace-nowrap rounded bg-black/70 px-1 text-[10px] text-white">
              {person.label}
            </span>
          </button>
        );
      })}
    </div>
  );
}
