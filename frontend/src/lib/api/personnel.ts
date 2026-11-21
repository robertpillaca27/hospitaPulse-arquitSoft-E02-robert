import { apiUrl } from "./base";

export type PersonnelRole = "admin" | "supervisor" | "staff";

export interface SessionUser {
  id: string;
  username: string;
  nombre_completo: string;
  email: string;
  rol: PersonnelRole;
  activo: boolean;
  debe_cambiar_password: boolean;
}

export interface PersonnelUser extends SessionUser {
  creado_en: string;
}

export interface CreatedPersonnel {
  usuario: PersonnelUser;
  password_temporal: string;
}

export interface ImportedPersonnelCreated {
  fila: number;
  nombre: string;
  usuario: string;
  password_temporal: string;
}

export interface ImportedPersonnelError {
  fila: number;
  nombre: string | null;
  usuario: string | null;
  error: string;
}

export interface ImportedPersonnel {
  procesados: number;
  creados: number;
  omitidos: number;
  creados_detalle: ImportedPersonnelCreated[];
  errores: ImportedPersonnelError[];
}

export class PersonnelApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "PersonnelApiError";
  }
}

const SESSION_EXPIRES_AT_KEY = "hospitapulse_session_expires_at";
const SESSION_DURATION_MS = 10 * 60 * 1000;
const SESSION_STARTED_EVENT = "hospitapulse-session-started";
const SESSION_ENDED_EVENT = "hospitapulse-session-ended";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isRole(value: unknown): value is PersonnelRole {
  return value === "admin" || value === "supervisor" || value === "staff";
}

function isSessionUser(value: unknown): value is SessionUser {
  return isRecord(value)
    && typeof value.id === "string"
    && typeof value.username === "string"
    && typeof value.nombre_completo === "string"
    && typeof value.email === "string"
    && isRole(value.rol)
    && typeof value.activo === "boolean"
    && typeof value.debe_cambiar_password === "boolean";
}

function isPersonnelUser(value: unknown): value is PersonnelUser {
  return isRecord(value)
    && isSessionUser(value)
    && typeof value.creado_en === "string";
}

function isCreatedPersonnel(value: unknown): value is CreatedPersonnel {
  return isRecord(value)
    && isPersonnelUser(value.usuario)
    && typeof value.password_temporal === "string";
}

async function request<T>(
  path: string,
  init: RequestInit,
  validate?: (value: unknown) => value is T,
): Promise<T> {
  const response = await fetch(apiUrl(path), {
    ...init,
    credentials: "include",
    headers: {
      Accept: "application/json",
      ...(init.body && !(init.body instanceof FormData) ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
    cache: "no-store",
  });
  if (response.status === 204) return undefined as T;
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const message = isRecord(payload) && typeof payload.detail === "string"
      ? payload.detail
      : `La API respondió con HTTP ${response.status}.`;
    throw new PersonnelApiError(message, response.status);
  }
  if (validate && !validate(payload)) {
    throw new Error("La API devolvió un formato de autorización no válido.");
  }
  return payload as T;
}

export function getCurrentSession(): Promise<SessionUser> {
  return request("/api/v1/auth/me", { method: "GET" }, isSessionUser);
}

export function login(username: string, password: string): Promise<SessionUser> {
  return request(
    "/api/v1/auth/login",
    { method: "POST", body: JSON.stringify({ username, password }) },
    isSessionUser,
  ).then((user) => {
    if (typeof window !== "undefined") {
      window.sessionStorage.setItem(
        SESSION_EXPIRES_AT_KEY,
        String(Date.now() + SESSION_DURATION_MS),
      );
      window.dispatchEvent(new Event(SESSION_STARTED_EVENT));
    }
    return user;
  });
}

export function logout(): Promise<void> {
  return request("/api/v1/auth/logout", { method: "POST" }).then(() => {
    if (typeof window !== "undefined") {
      window.sessionStorage.removeItem(SESSION_EXPIRES_AT_KEY);
      window.dispatchEvent(new Event(SESSION_ENDED_EVENT));
    }
  });
}

export function changePassword(
  passwordActual: string,
  passwordNueva: string,
): Promise<SessionUser> {
  return request(
    "/api/v1/auth/password",
    {
      method: "PATCH",
      body: JSON.stringify({
        password_actual: passwordActual,
        password_nueva: passwordNueva,
      }),
    },
    isSessionUser,
  ).then((user) => {
    if (typeof window !== "undefined") {
      window.sessionStorage.setItem(
        SESSION_EXPIRES_AT_KEY,
        String(Date.now() + SESSION_DURATION_MS),
      );
      window.dispatchEvent(new Event(SESSION_STARTED_EVENT));
    }
    return user;
  });
}

export function listPersonnel(): Promise<PersonnelUser[]> {
  return request(
    "/api/v1/personal",
    { method: "GET" },
    (value: unknown): value is PersonnelUser[] =>
      Array.isArray(value) && value.every(isPersonnelUser),
  );
}

export function createPersonnel(input: {
  username: string;
  nombre_completo: string;
  email: string;
  rol: PersonnelRole;
}): Promise<CreatedPersonnel> {
  return request(
    "/api/v1/personal",
    { method: "POST", body: JSON.stringify(input) },
    isCreatedPersonnel,
  );
}

export function importPersonnel(file: File): Promise<ImportedPersonnel> {
  const formData = new FormData();
  formData.append("archivo", file);
  return request(
    "/api/v1/personal/importar",
    { method: "POST", body: formData },
  ) as Promise<ImportedPersonnel>;
}

export function changePersonnelRole(
  userId: string,
  rol: PersonnelRole,
): Promise<PersonnelUser> {
  return request(
    `/api/v1/personal/${encodeURIComponent(userId)}/rol`,
    { method: "PATCH", body: JSON.stringify({ rol }) },
    isPersonnelUser,
  );
}

export function changePersonnelStatus(
  userId: string,
  activo: boolean,
): Promise<PersonnelUser> {
  return request(
    `/api/v1/personal/${encodeURIComponent(userId)}/estado`,
    { method: "PATCH", body: JSON.stringify({ activo }) },
    isPersonnelUser,
  );
}

export function resetPersonnelPassword(userId: string): Promise<CreatedPersonnel> {
  return request(
    `/api/v1/personal/${encodeURIComponent(userId)}/restablecer-password`,
    { method: "POST" },
    isCreatedPersonnel,
  );
}
