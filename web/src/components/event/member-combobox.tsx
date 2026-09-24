"use client";

import { useState } from "react";
import { Check, ChevronsUpDown } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { useMembers } from "@/lib/hooks";

export function MemberCombobox({
  onSelect,
  placeholder = "Assign to…",
}: {
  onSelect: (memberId: string) => void;
  placeholder?: string;
}) {
  const { data: members } = useMembers();
  const [open, setOpen] = useState(false);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger render={<Button variant="outline" className="w-56 justify-between" />}>
        <span className="truncate text-muted-foreground">{placeholder}</span>
        <ChevronsUpDown className="size-4 opacity-50" />
      </PopoverTrigger>
      <PopoverContent className="w-56 p-0" align="start">
        <Command>
          <CommandInput placeholder="Search members…" />
          <CommandList>
            <CommandEmpty>No member found.</CommandEmpty>
            <CommandGroup>
              {members?.map((m) => (
                <CommandItem
                  key={m.id}
                  value={`${m.name} ${m.roll_no}`}
                  onSelect={() => {
                    onSelect(m.id);
                    setOpen(false);
                  }}
                >
                  <Check className={cn("size-4", "opacity-0")} />
                  {m.name}
                  <span className="ml-auto text-xs text-muted-foreground">{m.roll_no}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
