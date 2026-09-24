"use client";

import { ChevronDown, Download, PlayCircle, RefreshCw, CheckCircle2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Progress } from "@/components/ui/progress";
import { downloadExport, type EventOut, type EventStatus } from "@/lib/api";
import { useFinalizeEvent, useProcessEvent, useRematchEvent } from "@/lib/hooks";

const STATUS_VARIANT: Record<EventOut["status"], "outline" | "secondary" | "default"> = {
  draft: "outline",
  processing: "secondary",
  review: "secondary",
  final: "default",
};

export function EventHeader({ event, status }: { event: EventOut; status?: EventStatus }) {
  const process = useProcessEvent(event.id);
  const rematch = useRematchEvent(event.id);
  const finalize = useFinalizeEvent(event.id);

  const isProcessing = status?.stage === "processing";
  const canProcess = event.status === "draft" || event.status === "review";
  const canRematch = event.status === "review";
  const canFinalize = event.status === "review";

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold">{event.name}</h1>
            <Badge variant={STATUS_VARIANT[event.status]} className="capitalize">
              {event.status}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">{event.date}</p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => process.mutate()} disabled={!canProcess || isProcessing || process.isPending}>
            <PlayCircle className="size-4" />
            Process
          </Button>
          <Button variant="outline" onClick={() => rematch.mutate()} disabled={!canRematch || isProcessing || rematch.isPending}>
            <RefreshCw className="size-4" />
            Rematch
          </Button>
          <Button onClick={() => finalize.mutate()} disabled={!canFinalize || finalize.isPending}>
            <CheckCircle2 className="size-4" />
            Finalize
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger render={<Button variant="outline" />}>
              <Download className="size-4" />
              Export
              <ChevronDown className="size-4" />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => downloadExport(event.id, "json", `${event.name}.json`)}>
                Export JSON
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => downloadExport(event.id, "xlsx", `${event.name}.xlsx`)}>
                Export Excel
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {isProcessing && status && (
        <Progress value={status.total ? (status.done / status.total) * 100 : 0}>
          <div className="flex justify-between text-sm text-muted-foreground">
            <span>
              Processing photos… {status.done}/{status.total}
              {status.failed > 0 ? ` (${status.failed} failed)` : ""}
            </span>
          </div>
        </Progress>
      )}
    </div>
  );
}
