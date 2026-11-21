"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";

import {
  fetchCurrentSurvey,
  SurveyApiError,
  submitSurveyResponse,
  type MonthlySurvey,
} from "@/lib/api/surveys";
import {
  changePassword,
  getCurrentSession,
  login,
  logout,
  PersonnelApiError,
  type SessionUser,
} from "@/lib/api/personnel";

type LoadState =
  | { status: "loading" }
  | { status: "ready"; survey: MonthlySurvey }
  | { status: "forbidden"; message: string }
  | { status: "error"; message: string };

const options = [
  { value: 1, label: "Totalmente en desacuerdo" },
  { value: 2, label: "En desacuerdo" },
  { value: 3, label: "Ni de acuerdo ni en desacuerdo" },
  { value: 4, label: "De acuerdo" },
  { value: 5, label: "Totalmente de acuerdo" },
];

export default function SurveysPage() {
  const [loadState, setLoadState] = useState<LoadState>({ status: "loading" });
  const [user, setUser] = useState<SessionUser | null>(null);
  const [sessionChecked, setSessionChecked] = useState(false);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [receipt, setReceipt] = useState<string | null>(null);
  const [authWorking, setAuthWorking] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [passwordActual, setPasswordActual] = useState("");
  const [passwordNueva, setPasswordNueva] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    getCurrentSession()
      .then(async (sessionUser) => {
        if (controller.signal.aborted) return;
        setUser(sessionUser);
        setSessionChecked(true);
        if (sessionUser.debe_cambiar_password) return;
        const survey = await fetchCurrentSurvey(controller.signal);
        if (!controller.signal.aborted) setLoadState({ status: "ready", survey });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof PersonnelApiError && error.status === 401) {
          setUser(null);
          setSessionChecked(true);
          setLoadState({ status: "loading" });
          return;
        }
        setSessionChecked(true);
        if (error instanceof SurveyApiError && error.status === 403) {
          setLoadState({ status: "forbidden", message: error.message });
          return;
        }
        if (error instanceof SurveyApiError && error.status === 401) {
          setUser(null);
          setLoadState({ status: "loading" });
          return;
        }
        const message = error instanceof Error ? error.message : "No se pudo cargar la encuesta.";
        setLoadState({ status: "error", message });
      });
    return () => controller.abort();
  }, []);

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAuthWorking(true);
    setAuthError(null);
    try {
      const sessionUser = await login(username.trim(), password);
      setPassword("");
      setUser(sessionUser);
      setSessionChecked(true);
      setReceipt(null);
      setAnswers({});
      if (sessionUser.rol !== "staff") {
        setLoadState({
          status: "forbidden",
          message: "Las cuentas de administrador y supervisor no pueden responder encuestas. Usa una cuenta con rol Personal.",
        });
      } else if (!sessionUser.debe_cambiar_password) {
        const survey = await fetchCurrentSurvey();
        setLoadState({ status: "ready", survey });
      }
    } catch (error: unknown) {
      if (error instanceof SurveyApiError && error.status === 403) {
        setLoadState({ status: "forbidden", message: error.message });
        return;
      }
      setAuthError(error instanceof Error ? error.message : "No se pudo iniciar sesión.");
    } finally {
      setAuthWorking(false);
    }
  }

  async function handlePasswordChange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAuthWorking(true);
    setAuthError(null);
    try {
      const sessionUser = await changePassword(passwordActual, passwordNueva);
      setPasswordActual("");
      setPasswordNueva("");
      setUser(sessionUser);
      if (sessionUser.rol !== "staff") {
        setLoadState({
          status: "forbidden",
          message: "Las cuentas de administrador y supervisor no pueden responder encuestas. Usa una cuenta con rol Personal.",
        });
        return;
      }
      const survey = await fetchCurrentSurvey();
      setLoadState({ status: "ready", survey });
    } catch (error: unknown) {
      setAuthError(error instanceof Error ? error.message : "No se pudo cambiar la contraseña.");
    } finally {
      setAuthWorking(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loadState.status !== "ready") return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const response = await submitSurveyResponse(
        loadState.survey.id,
        loadState.survey.preguntas.map((pregunta) => ({
          pregunta_id: pregunta.id,
          valor: answers[pregunta.id],
        })),
      );
      setReceipt(response.mensaje);
    } catch (error: unknown) {
      if (error instanceof SurveyApiError && error.status === 401) {
        setUser(null);
        setLoadState({ status: "loading" });
        setSubmitError("Tu sesión expiró. Inicia sesión nuevamente para responder.");
        return;
      }
      setSubmitError(error instanceof Error ? error.message : "No se pudo enviar la respuesta.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleLogout() {
    setAuthWorking(true);
    setAuthError(null);
    try {
      await logout();
      setUser(null);
      setSessionChecked(true);
      setLoadState({ status: "loading" });
      setAnswers({});
      setSubmitError(null);
      setPassword("");
      setPasswordActual("");
      setPasswordNueva("");
    } catch (error: unknown) {
      setAuthError(error instanceof Error ? error.message : "No se pudo cerrar la sesión.");
    } finally {
      setAuthWorking(false);
    }
  }

  return (
    <main className="survey-page">
      <header className="survey-page-header">
        <Link className="survey-back-link" href="/">← Volver al resumen</Link>
        <div className="survey-header-account">
          <span className="survey-brand">Hospita<span>Pulse</span></span>
          {user?.rol === "staff" && !user.debe_cambiar_password && (
            <>
              <span className="survey-account-name">{user.nombre_completo}</span>
              <button className="personnel-logout" type="button" onClick={() => void handleLogout()} disabled={authWorking}>
                {authWorking ? "Cerrando…" : "Cerrar sesión"}
              </button>
            </>
          )}
        </div>
      </header>

      <section className="survey-content">
        <div className="survey-page-kicker"><span /> ENCUESTA MENSUAL ANÓNIMA</div>
        {user === null && !sessionChecked && (
          <div className="survey-state-card" role="status">Verificando tu sesión…</div>
        )}
        {user === null && sessionChecked && loadState.status === "loading" && (
          <form className="survey-state-card survey-auth-form" onSubmit={handleLogin}>
            <h1>Inicia sesión para responder</h1>
            <p>Usa la cuenta que te autorizó el administrador. Tu identidad no se guardará junto con las respuestas.</p>
            <label>Usuario<input autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} required /></label>
            <label>Contraseña<input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
            <Link className="forgot-password-link" href="/recuperar-contrasena">¿Olvidaste tu contraseña?</Link>
            {receipt && <p className="survey-logout-receipt" role="status">Respuesta enviada. La sesión se cerró correctamente.</p>}
            {submitError && <p className="survey-form-error" role="alert">{submitError}</p>}
            {authError && <p className="survey-form-error" role="alert">{authError}</p>}
            <button className="survey-submit-button" type="submit" disabled={authWorking}>{authWorking ? "Ingresando…" : "Iniciar sesión"}</button>
          </form>
        )}
        {user?.debe_cambiar_password && (
          <form className="survey-state-card survey-auth-form" onSubmit={handlePasswordChange}>
            <h1>Cambia tu contraseña temporal</h1>
            <p>Debes definir una contraseña personal antes de responder la encuesta.</p>
            <label>Contraseña temporal<input type="password" autoComplete="current-password" value={passwordActual} onChange={(event) => setPasswordActual(event.target.value)} required /></label>
            <label>Nueva contraseña<input type="password" autoComplete="new-password" minLength={12} maxLength={72} value={passwordNueva} onChange={(event) => setPasswordNueva(event.target.value)} required /><small>Usa al menos 12 caracteres.</small></label>
            {authError && <p className="survey-form-error" role="alert">{authError}</p>}
            <button className="survey-submit-button" type="submit" disabled={authWorking}>{authWorking ? "Guardando…" : "Cambiar contraseña y continuar"}</button>
          </form>
        )}
        {user !== null && !user.debe_cambiar_password && loadState.status === "loading" && (
          <div className="survey-state-card" role="status">Cargando la encuesta mensual…</div>
        )}
        {loadState.status === "forbidden" && (
          <div className="survey-state-card survey-error" role="alert">
            <h1>Encuesta exclusiva para Personal</h1>
            <p>{loadState.message}</p>
            <p>Inicia sesión con una cuenta cuyo rol sea Personal. Administradores y supervisores usan sus propios menús de gestión e indicadores.</p>
            <Link className="survey-secondary-button" href="/">Volver al menú</Link>
          </div>
        )}
        {loadState.status === "error" && (
          <div className="survey-state-card survey-error" role="alert">
            <h1>No se pudo abrir Encuestas</h1>
            <p>{loadState.message}</p>
            <p>Verifica la conexión con PostgreSQL y el backend. La encuesta mensual se crea automáticamente.</p>
            <Link className="survey-secondary-button" href="/">Volver al resumen</Link>
          </div>
        )}
        {user !== null && !user.debe_cambiar_password && loadState.status === "ready" && (
          <>
            <div className="survey-page-heading">
              <div>
                <h1>{loadState.survey.titulo}</h1>
                <p>{loadState.survey.descripcion}</p>
              </div>
              <span className={`survey-status-pill ${loadState.survey.estado === "abierta" ? "is-open" : ""}`}>
                {loadState.survey.estado === "abierta" ? "Abierta" : "Cerrada"}
              </span>
            </div>
            <div className="survey-privacy-note">
              <span aria-hidden="true">✓</span>
              <p><strong>Tu respuesta no incluye tu nombre ni servicio.</strong> Los resultados solo se muestran en grupos de al menos 5 respuestas (N ≥ 5).</p>
            </div>
            {receipt ? (
              <div className="survey-success" role="status">
                <span>✓</span>
                <h2>¡Gracias por participar!</h2>
                <p>{receipt}</p>
                <button className="personnel-logout survey-success-logout" type="button" onClick={() => void handleLogout()} disabled={authWorking}>
                  {authWorking ? "Cerrando sesión…" : "Cerrar sesión"}
                </button>
                <Link className="survey-secondary-button" href="/">Volver al resumen</Link>
              </div>
            ) : (
              <form className="survey-form" onSubmit={handleSubmit}>
                <div className="likert-legend"><span>Tu opinión</span><span>Selecciona una opción del 1 al 5</span></div>
                {loadState.survey.preguntas.map((pregunta, index) => (
                  <fieldset className="survey-question" key={pregunta.id}>
                    <legend>
                      <span className="question-number">{String(index + 1).padStart(2, "0")}</span>
                      <span><small>{pregunta.dimension}</small>{pregunta.texto}</span>
                    </legend>
                    <div className="likert-options">
                      {options.map((option) => (
                        <label className="likert-option" key={option.value}>
                          <input
                            type="radio"
                            name={pregunta.id}
                            value={option.value}
                            checked={answers[pregunta.id] === option.value}
                            onChange={() => setAnswers((current) => ({ ...current, [pregunta.id]: option.value }))}
                            disabled={loadState.survey.estado !== "abierta" || submitting}
                            required
                          />
                          <span>{option.value}</span>
                          <small>{option.label}</small>
                        </label>
                      ))}
                    </div>
                  </fieldset>
                ))}
                {submitError && <p className="survey-form-error" role="alert">{submitError}</p>}
                <div className="survey-submit-row">
                  <span>{Object.keys(answers).length} de {loadState.survey.preguntas.length} respondidas</span>
                  <button
                    className="survey-submit-button"
                    type="submit"
                    disabled={loadState.survey.estado !== "abierta" || submitting || Object.keys(answers).length !== loadState.survey.preguntas.length}
                  >
                    {submitting ? "Enviando…" : "Enviar respuesta anónima"} <span>→</span>
                  </button>
                </div>
              </form>
            )}
          </>
        )}
      </section>
    </main>
  );
}
