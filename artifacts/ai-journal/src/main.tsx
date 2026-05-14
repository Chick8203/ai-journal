import { createRoot } from "react-dom/client";
import { setBaseUrl } from "@workspace/api-client-react";
import App from "./App";
import "./index.css";

// Detect Tauri via the global it injects into every WebView.
// On Windows, Tauri uses https://tauri.localhost/ (not tauri://), so we cannot
// rely on window.location.protocol to distinguish Tauri from a regular browser.
if ("__TAURI_INTERNALS__" in window) {
  setBaseUrl("http://127.0.0.1:8080");
}

createRoot(document.getElementById("root")!).render(<App />);
