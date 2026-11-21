import { afterEach, describe, expect, it, vi } from "vitest";

import { askHelpAssistant, HelpAssistantApiError } from "../src/lib/help-assistant";

describe("help assistant API client", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("sends only the current open-ended question to the backend", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ respuesta: "Respuesta abierta." }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(askHelpAssistant("¿Qué es la arquitectura de software?"))
      .resolves.toBe("Respuesta abierta.");

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/asistente/chat",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ pregunta: "¿Qué es la arquitectura de software?" }),
      }),
    );
  });

  it("surfaces API errors instead of showing a successful answer", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "Asistente no configurado." }), {
        status: 503,
        headers: { "Content-Type": "application/json" },
      }),
    ));

    await expect(askHelpAssistant("¿Qué es HospitaPulse?"))
      .rejects.toEqual(expect.objectContaining<Partial<HelpAssistantApiError>>({
        message: "Asistente no configurado.",
        status: 503,
      }));
  });
});
