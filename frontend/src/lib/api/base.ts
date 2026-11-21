export function getApiBaseUrl(): string {
  if (typeof window !== "undefined" && window.location.protocol === "https:") {
    return "";
  }

  const configured = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (!configured) {
    throw new Error("Falta configurar NEXT_PUBLIC_API_BASE_URL.");
  }

  return configured
    .replace(/\/+$/, "")
    .replace(/\/api\/v1$/, "");
}

export function apiUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${getApiBaseUrl()}${normalizedPath.startsWith("/api/v1/") ? normalizedPath : `/api/v1${normalizedPath}`}`;
}
