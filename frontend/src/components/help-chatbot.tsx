"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";

import { askHelpAssistant } from "@/lib/help-assistant";

interface ChatMessage {
  id: number;
  role: "assistant" | "user";
  text: string;
}

const suggestedQuestions = [
  "¿Cómo se protege mi privacidad?",
  "¿Cómo respondo una encuesta?",
  "¿Quién puede ver los indicadores?",
];

export default function HelpChatbot() {
  const [isOpen, setIsOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 0,
      role: "assistant",
      text: "¡Hola! Puedes hacerme preguntas abiertas sobre cualquier tema. Para dudas sobre políticas internas, no tengo acceso a información privada del hospital.",
    },
  ]);
  const nextMessageId = useRef(1);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ block: "nearest" });
  }, [messages]);

  useEffect(() => {
    if (isOpen) inputRef.current?.focus();
  }, [isOpen]);

  async function sendQuestion(text: string) {
    const normalizedQuestion = text.trim();
    if (!normalizedQuestion || isSending) return;

    const questionId = nextMessageId.current;
    nextMessageId.current += 1;
    const answerId = nextMessageId.current;
    nextMessageId.current += 1;

    setMessages((currentMessages) => [
      ...currentMessages,
      { id: questionId, role: "user", text: normalizedQuestion },
    ]);
    setQuestion("");
    setIsSending(true);

    try {
      const answer = await askHelpAssistant(normalizedQuestion);
      setMessages((currentMessages) => [
        ...currentMessages,
        { id: answerId, role: "assistant", text: answer },
      ]);
    } catch (error: unknown) {
      const message = error instanceof Error
        ? error.message
        : "No se pudo obtener una respuesta del asistente.";
      setMessages((currentMessages) => [
        ...currentMessages,
        { id: answerId, role: "assistant", text: message },
      ]);
    } finally {
      setIsSending(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void sendQuestion(question);
  }

  return (
    <aside className="help-chatbot" aria-label="Asistente de ayuda">
      {isOpen && (
        <section className="help-chat-panel" aria-labelledby="help-chat-title">
          <header className="help-chat-header">
            <span className="help-chat-avatar" aria-hidden="true">+</span>
            <div>
              <h2 id="help-chat-title">Ayuda HospitaPulse</h2>
              <p>Respuestas sobre el uso de la plataforma</p>
            </div>
            <button
              type="button"
              className="help-chat-close"
              onClick={() => setIsOpen(false)}
              aria-label="Cerrar asistente de ayuda"
            >
              ×
            </button>
          </header>

          <div className="help-chat-messages" aria-live="polite" aria-relevant="additions" aria-busy={isSending}>
            {messages.map((message) => (
              <p
                className={`help-chat-message ${message.role}`}
                key={message.id}
              >
                {message.text}
              </p>
            ))}
            {isSending && <p className="help-chat-message assistant" role="status">Preparando respuesta…</p>}
            <div ref={messagesEndRef} />
          </div>

          {messages.length === 1 && (
            <div className="help-chat-suggestions" aria-label="Preguntas sugeridas">
              {suggestedQuestions.map((suggestion) => (
                <button
                  type="button"
                  key={suggestion}
                  disabled={isSending}
                  onClick={() => void sendQuestion(suggestion)}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          )}

          <form className="help-chat-form" onSubmit={handleSubmit}>
            <label className="visually-hidden" htmlFor="help-chat-question">
              Escribe una pregunta sobre la plataforma
            </label>
            <input
              id="help-chat-question"
              ref={inputRef}
              maxLength={1200}
              disabled={isSending}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Escribe tu pregunta…"
              value={question}
            />
            <button type="submit" disabled={!question.trim() || isSending} aria-label="Enviar pregunta">
              {isSending ? "Enviando…" : "Enviar"}
            </button>
          </form>
          <p className="help-chat-privacy">
            Gemini procesa la pregunta actual. HospitaPulse no guarda el chat ni envía
            historial o datos internos. El tratamiento del proveedor se rige por sus
            políticas. No incluyas datos personales ni respuestas de encuestas.
          </p>
        </section>
      )}

      <button
        type="button"
        className="help-chat-toggle"
        aria-expanded={isOpen}
        aria-label={isOpen ? "Cerrar asistente de ayuda" : "Abrir asistente de ayuda"}
        onClick={() => setIsOpen((open) => !open)}
      >
        <span aria-hidden="true">{isOpen ? "×" : "?"}</span>
        <span>{isOpen ? "Cerrar ayuda" : "¿Necesitas ayuda?"}</span>
      </button>
    </aside>
  );
}
