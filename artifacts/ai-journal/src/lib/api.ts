// Tauri-aware fetch wrapper.
// In Tauri production builds __TAURI_INTERNALS__ is injected and all API calls
// must use an absolute URL because the WebView origin is not the API server.
function getBase(): string {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window
    ? "http://127.0.0.1:8080"
    : "";
}

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${getBase()}${path}`, options);
  if (!res.ok) {
    const msg = await res.text().catch(() => res.statusText);
    throw new Error(msg || `HTTP ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}
