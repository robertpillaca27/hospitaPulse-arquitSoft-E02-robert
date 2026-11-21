import { apiUrl } from "./api/base";

export class HelpAssistantApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "HelpAssistantApiError";
  }
}

interface AssistantResponse {
  respuesta: string;
}

function isAssistantResponse(value: unknown): value is AssistantResponse {
  return typeof value === "object"
    && value !== null
    && "respuesta" in value
    && typeof value.respuesta === "string"
    && value.respuesta.trim().length > 0;
}

export async function askHelpAssistant(question: string): Promise<string> {
  const response = await fetch(apiUrl("/asistente/chat"), {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ pregunta: question }),
    cache: "no-store",
  });
  const payload: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const message = typeof payload === "object"
      && payload !== null
      && "detail" in payload
      && typeof payload.detail === "string"
      ? payload.detail
      : `El asistente respondió con HTTP ${response.status}.`;
    throw new HelpAssistantApiError(message, response.status);
  }

  if (!isAssistantResponse(payload)) {
    throw new Error("El asistente devolvió una respuesta no válida.");
  }
  return payload.respuesta.trim();
}
