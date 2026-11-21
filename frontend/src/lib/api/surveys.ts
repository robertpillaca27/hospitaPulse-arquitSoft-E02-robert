import { apiUrl } from "./base";

export interface SurveyQuestion {
  id: string;
  orden: number;
  dimension: string;
  texto: string;
}

export interface MonthlySurvey {
  id: string;
  anio: number;
  mes: number;
  titulo: string;
  descripcion: string;
  estado: string;
  preguntas: SurveyQuestion[];
}

export interface SurveyReceipt {
  status: string;
  mensaje: string;
  anonima: boolean;
}

export class SurveyApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "SurveyApiError";
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isSurveyQuestion(value: unknown): value is SurveyQuestion {
  if (!isRecord(value)) return false;
  return typeof value.id === "string"
    && typeof value.orden === "number"
    && typeof value.dimension === "string"
    && typeof value.texto === "string";
}

function isMonthlySurvey(value: unknown): value is MonthlySurvey {
  if (!isRecord(value)) return false;
  return typeof value.id === "string"
    && typeof value.anio === "number"
    && typeof value.mes === "number"
    && typeof value.titulo === "string"
    && typeof value.descripcion === "string"
    && typeof value.estado === "string"
    && Array.isArray(value.preguntas)
    && value.preguntas.every(isSurveyQuestion);
}

function isSurveyReceipt(value: unknown): value is SurveyReceipt {
  return isRecord(value)
    && typeof value.status === "string"
    && typeof value.mensaje === "string"
    && typeof value.anonima === "boolean";
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
      "Content-Type": "application/json",
      ...init.headers,
    },
    cache: "no-store",
  });
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = isRecord(payload) && typeof payload.detail === "string"
      ? payload.detail
      : `La API respondió con HTTP ${response.status}.`;
    throw new SurveyApiError(detail, response.status);
  }
  if (!validate(payload)) {
    throw new Error("La API devolvió un formato de encuesta no válido.");
  }
  return payload;
}

export function fetchCurrentSurvey(signal?: AbortSignal): Promise<MonthlySurvey> {
  return request("/api/v1/encuestas/actual", { method: "GET", signal }, isMonthlySurvey);
}

export function submitSurveyResponse(
  surveyId: string,
  answers: Array<{ pregunta_id: string; valor: number }>,
): Promise<SurveyReceipt> {
  return request(
    `/api/v1/encuestas/${encodeURIComponent(surveyId)}/respuestas`,
    {
      method: "POST",
      body: JSON.stringify({ respuestas: answers }),
    },
    isSurveyReceipt,
  );
}
