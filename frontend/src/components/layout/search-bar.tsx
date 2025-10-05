import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { searchModes } from "@/data/search-mode";
import { useGlobal } from "@/context/GlobalContext";

export function SearchBar() {
  const { query, setQuery, searchMode, setSearchMode } = useGlobal();
  const [localQuery, setLocalQuery] = useState(query);

  useEffect(() => {
    setLocalQuery(query);
  }, [query]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      setQuery(localQuery);
    }
  };

  return (
    <div className="flex gap-3">
      <Input
        type="text"
        value={localQuery}
        onChange={(e) => setLocalQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Search papers, nodes, or keywords..."
        className="py-2 bg-neutral-900/70 text-neutral-100 border-neutral-700 placeholder:text-neutral-400 rounded-md backdrop-blur-md focus-visible:ring-neutral-500 w-[360px]"
      />

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="secondary">
            {searchModes.find((m) => m.value === searchMode)?.label}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-50">
          <DropdownMenuLabel>Choose Mode</DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuRadioGroup
            value={searchMode}
            onValueChange={setSearchMode}
          >
            {searchModes.map((mode) => (
              <DropdownMenuRadioItem key={mode.value} value={mode.value}>
                {mode.label}
              </DropdownMenuRadioItem>
            ))}
          </DropdownMenuRadioGroup>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
