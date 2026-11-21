import { apiUrl } from "./base";

export interface DimensionIndicator {
  dimension: string;
  promedio: number;
}

export interface MonthlyIndicators {
  anio: number;
  mes: number;
  enmascarado: boolean;
  total_respuestas: number | null;
  promedio_general: number | null;
  dimensiones: DimensionIndicator[];
}

export class IndicatorsApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "IndicatorsApiError";
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isDimensionIndicator(value: unknown): value is DimensionIndicator {
  return isRecord(value)
    && typeof value.dimension === "string"
    && typeof value.promedio === "number";
}

function isMonthlyIndicators(value: unknown): value is MonthlyIndicators {
  return isRecord(value)
    && typeof value.anio === "number"
    && typeof value.mes === "number"
    && typeof value.enmascarado === "boolean"
    && (typeof value.total_respuestas === "number" || value.total_respuestas === null)
    && (typeof value.promedio_general === "number" || value.promedio_general === null)
    && Array.isArray(value.dimensiones)
    && value.dimensiones.every(isDimensionIndicator);
}

export async function fetchMonthlyIndicators(
  year: number,
  month: number,
  signal?: AbortSignal,
): Promise<MonthlyIndicators> {
  const query = new URLSearchParams({ anio: String(year), mes: String(month) });
  const response = await fetch(`${apiUrl("/encuestas/indicadores")}?${query}`, {
    headers: { Accept: "application/json" },
    credentials: "include",
    signal,
    cache: "no-store",
  });
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = isRecord(payload) && typeof payload.detail === "string"
      ? payload.detail
      : `La API respondió con HTTP ${response.status}.`;
    throw new IndicatorsApiError(detail, response.status);
  }
  if (!isMonthlyIndicators(payload)) {
    throw new Error("La API devolvió un formato de indicadores no válido.");
  }
  return payload;
}
