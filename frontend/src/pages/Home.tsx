import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { HelpButton } from "@/components/layout/help-button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { searchModes } from "@/data/searchMode";
import { useGlobal } from "@/context/GlobalContext";

export default function Home() {
  const { query, setQuery, searchMode, setSearchMode } = useGlobal();
  const [localQuery, setLocalQuery] = useState(query);

  useEffect(() => {
    setLocalQuery(query);
  }, [query]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      setQuery(localQuery);
      console.log("[Global Query Updated]:", localQuery);
    }
  };

  return (
    <div className="relative min-h-screen flex items-center justify-center bg-neutral-950 text-neutral-100">
      {/* Logo góc trái */}
      <div className="fixed top-4 left-4 select-none">
        <p className="text-xl font-semibold tracking-tight">
          <span className="text-green-400">Soft</span>
          <span className="text-white">AI</span>
        </p>
      </div>

      {/* Nút Insight góc phải */}
      <Button variant="secondary" className="fixed top-4 right-4">
        Insight
      </Button>

      {/* Ô tìm kiếm trung tâm */}
      <div className="fixed top-4 left-1/2 -translate-x-1/2">
        <div className="relative flex gap-3">
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
      </div>

      {/* Nút Help góc phải dưới */}
      <HelpButton />
    </div>
  );
}
