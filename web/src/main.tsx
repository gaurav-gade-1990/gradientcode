import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, HashRouter } from "react-router";
import App from "./App";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {import.meta.env.VITE_ARTIFACT ? (
      // The artifact host serves one page, so routes live in the hash.
      <HashRouter>
        <App />
      </HashRouter>
    ) : (
      <BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/, "") || "/"}>
        <App />
      </BrowserRouter>
    )}
  </StrictMode>,
);
