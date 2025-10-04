import React, { createContext, useContext, useState, useEffect } from "react";
import { searchModes } from "@/data/searchMode";

type GlobalContextType = {
  query: string;
  setQuery: (value: string) => void;
  searchMode: string;
  setSearchMode: (value: string) => void;
};

const GlobalContext = createContext<GlobalContextType | undefined>(undefined);

export const GlobalProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [query, setQuery] = useState("");
  const [searchMode, setSearchMode] = useState(searchModes[0].value);

  useEffect(() => {
    console.log("[GlobalContext] Updated:", { query, searchMode });
  }, [query, searchMode]);

  return (
    <GlobalContext.Provider
      value={{ query, setQuery, searchMode, setSearchMode }}
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
