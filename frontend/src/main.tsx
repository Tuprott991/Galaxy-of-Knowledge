import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import { GlobalProvider } from "@/context/GlobalContext";
import App from "./App.tsx";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <GlobalProvider>
      <App />
    </GlobalProvider>
  </StrictMode>
);
