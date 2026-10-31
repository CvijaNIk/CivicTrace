import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ParquetExplorer } from "./ParquetExplorer";
import { PassportPreview } from "./PassportPreview";
import { App } from "./App";
import "./style.css";
const root = document.getElementById("root");
if (!root) throw Error("Missing application root");
createRoot(root).render(
  <StrictMode>
    {new URLSearchParams(window.location.search).get("view") === "passport" ? (
      <PassportPreview />
    ) : new URLSearchParams(window.location.search).get("view") ===
      "parquet" ? (
      <ParquetExplorer />
    ) : (
      <App />
    )}
  </StrictMode>,
);
