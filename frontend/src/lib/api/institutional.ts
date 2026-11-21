import type { SessionUser } from "@/lib/api/personnel";

import { apiUrl } from "./base";

export type InstitutionalModule =
  | "sugerencias"
  | "planes-mejora"
  | "reconocimientos"
  | "organigrama"
  | "eventos"
  | "comunicaciones"
  | "auditoria";

export type InstitutionalRecord = Record<string, unknown> & { id: string };
export interface DirectoryPerson {
  id: string;
  nombre_completo: string;
}

export class InstitutionalApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "InstitutionalApiError";
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isRecordList(value: unknown): value is InstitutionalRecord[] {
  return Array.isArray(value) && value.every(
    (item): item is InstitutionalRecord => isRecord(item) && typeof item.id === "string",
  );
}

function isInstitutionalRecord(value: unknown): value is InstitutionalRecord {
  return isRecord(value) && typeof value.id === "string";
}

async function request<T>(
  path: string,
  init: RequestInit,
  validate: (value: unknown) => value is T,
): Promise<T> {
  const response = await fetch(apiUrl(path), {
    ...init,
    credentials: "include",
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
    cache: "no-store",
  });
  const payload: unknown = response.status === 204 ? undefined : await response.json().catch(() => null);
  if (!response.ok) {
    const message = isRecord(payload) && typeof payload.detail === "string"
      ? payload.detail
      : `La API respondió con HTTP ${response.status}.`;
    throw new InstitutionalApiError(message, response.status);
  }
  if (!validate(payload)) throw new Error("La API devolvió un formato institucional no válido.");
  return payload;
}

function modulePath(module: InstitutionalModule): string {
  return `/api/v1/institucional/${module}`;
}

export function listInstitutionalRecords(
  module: InstitutionalModule,
  filters: Record<string, string> = {},
): Promise<InstitutionalRecord[]> {
  const query = new URLSearchParams(filters).toString();
  return request(`${modulePath(module)}${query ? `?${query}` : ""}`, { method: "GET" }, isRecordList);
}

export function listNominationDirectory(): Promise<DirectoryPerson[]> {
  return request("/api/v1/institucional/directorio", { method: "GET" }, (value): value is DirectoryPerson[] =>
    Array.isArray(value) && value.every(
      (item) => isRecord(item)
        && typeof item.id === "string"
        && typeof item.nombre_completo === "string",
    ));
}

export function createInstitutionalRecord(
  module: InstitutionalModule,
  body: Record<string, unknown>,
): Promise<InstitutionalRecord> {
  return request(modulePath(module), { method: "POST", body: JSON.stringify(body) }, isInstitutionalRecord);
}

export function updateInstitutionalRecord(
  module: InstitutionalModule,
  id: string,
  body: Record<string, unknown>,
): Promise<InstitutionalRecord> {
  return request(`${modulePath(module)}/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  }, isInstitutionalRecord);
}

export function confirmEventAttendance(eventId: string): Promise<{ evento_id: string; confirmada: boolean }> {
  return request(`/api/v1/institucional/eventos/${encodeURIComponent(eventId)}/asistencia`, {
    method: "PUT",
  }, (value): value is { evento_id: string; confirmada: boolean } =>
    isRecord(value) && typeof value.evento_id === "string" && typeof value.confirmada === "boolean");
}

export function cancelEventAttendance(eventId: string): Promise<void> {
  return request(`/api/v1/institucional/eventos/${encodeURIComponent(eventId)}/asistencia`, {
    method: "DELETE",
  }, (value): value is undefined => value === undefined);
}

export function publishInstitutionalRecord(
  module: "eventos" | "comunicaciones",
  id: string,
): Promise<InstitutionalRecord> {
  const action = module === "eventos" ? "publicar" : "publicar";
  return request(`${modulePath(module)}/${encodeURIComponent(id)}/${action}`, {
    method: "POST",
  }, isInstitutionalRecord);
}

export function updateRecognitionConsent(id: string, consentido: boolean): Promise<{ estado: string }> {
  return request(`/api/v1/institucional/reconocimientos/${encodeURIComponent(id)}/consentimiento`, {
    method: "POST",
    body: JSON.stringify({ consentido }),
  }, (value): value is { estado: string } => isRecord(value) && typeof value.estado === "string");
}

export function getInstitutionalSession(): Promise<SessionUser> {
  return request("/api/v1/auth/me", { method: "GET" }, (value): value is SessionUser =>
    isRecord(value)
    && typeof value.id === "string"
    && typeof value.nombre_completo === "string"
    && (value.rol === "admin" || value.rol === "supervisor" || value.rol === "staff")
    && typeof value.debe_cambiar_password === "boolean");
}
