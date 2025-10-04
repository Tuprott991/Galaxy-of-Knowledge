import React, { createContext, useContext, useState, useEffect } from "react";
import { searchModes } from "@/data/search-mode";

type GlobalContextType = {
  query: string;
  setQuery: (value: string) => void;
  searchMode: string;
  setSearchMode: (value: string) => void;
  chatView: boolean;
  setChatView: (value: boolean) => void;
};

const GlobalContext = createContext<GlobalContextType | undefined>(undefined);

export const GlobalProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [query, setQuery] = useState("");
  const [searchMode, setSearchMode] = useState(searchModes[0].value);
  const [chatView, setChatView] = useState(true);

  useEffect(() => {
    console.log("[GlobalContext] Updated:", { query, searchMode });
  }, [query, searchMode]);

  return (
    <GlobalContext.Provider
      value={{ query, setQuery, searchMode, setSearchMode, chatView, setChatView }}
    >
      {children}
    </GlobalContext.Provider>
  );
};

/* eslint-disable react-refresh/only-export-components */
export function useGlobal() {
  const context = useContext(GlobalContext);
  if (!context) {
    throw new Error("useGlobal must be used within a GlobalProvider");
  }
  return context;
}
