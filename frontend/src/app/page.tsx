"use client";

import { Fragment, useEffect, useState, type FormEvent } from "react";
import { usePathname } from "next/navigation";

import { fetchApiHealth, type HealthResponse } from "@/lib/api/health";
import {
  fetchMonthlyIndicators,
  IndicatorsApiError,
  type MonthlyIndicators,
} from "@/lib/api/indicators";
import {
  changePassword,
  getCurrentSession,
  login,
  logout,
  PersonnelApiError,
  type SessionUser,
} from "@/lib/api/personnel";

type ApiState =
  | { status: "loading" }
  | { status: "connected"; data: HealthResponse }
  | { status: "error"; message: string };

type IndicatorState =
  | { status: "loading" }
  | { status: "ready"; data: MonthlyIndicators }
  | { status: "error"; message: string };

type ViewerState =
  | { status: "checking" }
  | { status: "anonymous" }
  | { status: "authorized"; user: SessionUser }
  | { status: "forbidden"; user: SessionUser }
  | { status: "unavailable"; message: string };

interface PeriodOption {
  value: string;
  label: string;
}

const PRIVACY_MINIMUM_SAMPLE = 5;

const navigation = [
  { group: "PRINCIPAL", label: "Resumen", href: "#resumen", icon: "◫" },
  { group: "PRINCIPAL", label: "Encuestas", href: "/encuestas", icon: "▤" },
  { group: "PRINCIPAL", label: "Indicadores", href: "#indicadores", icon: "▥", active: false },
  { group: "PARTICIPACIÓN Y CULTURA", label: "Sugerencias", href: "/modulos/sugerencias", icon: "✦" },
  { group: "PARTICIPACIÓN Y CULTURA", label: "Reconocimientos", href: "/modulos/reconocimientos", icon: "♡" },
  { group: "PARTICIPACIÓN Y CULTURA", label: "Actividades y eventos", href: "/modulos/eventos", icon: "▦" },
  { group: "PARTICIPACIÓN Y CULTURA", label: "Comunicaciones", href: "/modulos/comunicaciones", icon: "◉" },
  { group: "GESTIÓN", label: "Planes de mejora", href: "/modulos/planes-mejora", icon: "↗" },
  { group: "GESTIÓN", label: "Organigrama", href: "/modulos/organigrama", icon: "⌘" },
  { group: "ADMINISTRACIÓN", label: "Usuarios y roles", href: "/personal", icon: "♙" },
  { group: "ADMINISTRACIÓN", label: "Seguridad y auditoría", href: "/modulos/auditoria", icon: "⌑" },
];

function getRecentPeriods(year: number, month: number): PeriodOption[] {
  return Array.from({ length: 12 }, (_, index) => {
    const date = new Date(year, month - 1 - index, 1);
    return {
      value: `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`,
      label: new Intl.DateTimeFormat("es-PE", { month: "long", year: "numeric" }).format(date),
    };
  });
}

function getLimaPeriod(date: Date): { year: number; month: number } {
  const parts = new Intl.DateTimeFormat("en-US", {
    month: "2-digit",
    timeZone: "America/Lima",
    year: "numeric",
  }).formatToParts(date);
  const year = parts.find((part) => part.type === "year")?.value;
  const month = parts.find((part) => part.type === "month")?.value;
  if (!year || !month) {
    throw new Error("No se pudo determinar el periodo actual de Lima.");
  }
  return { year: Number(year), month: Number(month) };
}

function getUserInitials(fullName: string): string {
  return fullName
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toLocaleUpperCase("es-PE"))
    .join("") || "HP";
}

function getRoleLabel(role: SessionUser["rol"]): string {
  if (role === "admin") return "Administrador";
  if (role === "supervisor") return "Supervisor";
  return "Personal";
}

function ApiStatus({ state }: { state: ApiState }) {
  if (state.status === "loading") {
    return <span className="api-status"><span className="status-dot pending" />Conectando API</span>;
  }
  if (state.status === "error") {
    return <span className="api-status" title={state.message}><span className="status-dot offline" />API desconectada</span>;
  }
  return <span className="api-status"><span className="status-dot online" />Sistema operativo</span>;
}

export default function HomePage() {
  const [apiState, setApiState] = useState<ApiState>({ status: "loading" });
  const [indicatorState, setIndicatorState] = useState<IndicatorState>({ status: "loading" });
  const [viewer, setViewer] = useState<ViewerState>({ status: "checking" });
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);
  const [authWorking, setAuthWorking] = useState(false);
  const [temporaryPassword, setTemporaryPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [selectedPeriod, setSelectedPeriod] = useState("");
  const [periodOptions, setPeriodOptions] = useState<PeriodOption[]>([]);
  const [currentDate, setCurrentDate] = useState<Date | null>(null);
  const pathname = usePathname();

  useEffect(() => {
    const now = new Date();
    const limaPeriod = getLimaPeriod(now);
    setCurrentDate(now);
    setSelectedPeriod(`${limaPeriod.year}-${String(limaPeriod.month).padStart(2, "0")}`);
    setPeriodOptions(getRecentPeriods(limaPeriod.year, limaPeriod.month));
    const clockInterval = window.setInterval(() => setCurrentDate(new Date()), 30_000);

    const controller = new AbortController();
    fetchApiHealth(controller.signal)
      .then((data) => setApiState({ status: "connected", data }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        const message = error instanceof Error ? error.message : "Error desconocido";
        setApiState({ status: "error", message });
      });
    getCurrentSession()
      .then((user) => {
        if (controller.signal.aborted) return;
        setViewer(
          (user.rol === "admin" || user.rol === "supervisor") && !user.debe_cambiar_password
            ? { status: "authorized", user }
            : { status: "forbidden", user },
        );
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof PersonnelApiError && error.status === 401) {
          setViewer({ status: "anonymous" });
          return;
        }
        setViewer({
          status: "unavailable",
          message: error instanceof Error ? error.message : "No se pudo verificar la sesión.",
        });
      });
    return () => {
      controller.abort();
      window.clearInterval(clockInterval);
    };
  }, []);

  useEffect(() => {
    if (!selectedPeriod || viewer.status !== "authorized") return;
    const [year, month] = selectedPeriod.split("-").map(Number);
    const controller = new AbortController();
    setIndicatorState({ status: "loading" });
    fetchMonthlyIndicators(year, month, controller.signal)
      .then((data) => setIndicatorState({ status: "ready", data }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof IndicatorsApiError && error.status === 401) {
          setViewer({ status: "anonymous" });
          return;
        }
        const message = error instanceof Error ? error.message : "No se pudieron cargar los indicadores.";
        setIndicatorState({ status: "error", message });
      });
    return () => controller.abort();
  }, [selectedPeriod, viewer]);

  async function handleIndicatorLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAuthWorking(true);
    setAuthError(null);
    try {
      const user = await login(username.trim(), password);
      setPassword("");
      if (user.debe_cambiar_password) {
        window.location.assign(user.rol === "staff" ? "/encuestas" : "/personal");
        return;
      }
      if (user.rol === "staff") {
        setViewer({ status: "forbidden", user });
        return;
      }
      if ((user.rol === "admin" || user.rol === "supervisor") && !user.debe_cambiar_password) {
        setViewer({ status: "authorized", user });
      } else {
        setViewer({ status: "forbidden", user });
      }
    } catch (error: unknown) {
      setAuthError(error instanceof Error ? error.message : "No se pudo iniciar sesión.");
    } finally {
      setAuthWorking(false);
    }
  }

  async function handleTemporaryPasswordChange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAuthWorking(true);
    setAuthError(null);
    try {
      const user = await changePassword(temporaryPassword, newPassword);
      setTemporaryPassword("");
      setNewPassword("");
      if (user.rol === "staff") {
        setViewer({ status: "forbidden", user });
      } else {
        setViewer({ status: "authorized", user });
      }
    } catch (error: unknown) {
      setAuthError(error instanceof Error ? error.message : "No se pudo cambiar la contraseña.");
    } finally {
      setAuthWorking(false);
    }
  }

  async function handleIndicatorLogout() {
    setAuthWorking(true);
    setAuthError(null);
    try {
      await logout();
      setIndicatorState({ status: "loading" });
      setViewer({ status: "anonymous" });
    } catch (error: unknown) {
      setAuthError(error instanceof Error ? error.message : "No se pudo cerrar sesión.");
    } finally {
      setAuthWorking(false);
    }
  }

  const indicatorBadge = indicatorState.status === "loading"
    ? "CARGANDO INDICADORES"
    : viewer.status === "checking"
      ? "VERIFICANDO ACCESO"
      : viewer.status === "anonymous"
        ? "INICIA SESIÓN PARA VER INDICADORES"
        : viewer.status === "forbidden"
          ? "ACCESO NO AUTORIZADO"
          : indicatorState.status === "error"
      ? "INDICADORES NO DISPONIBLES"
      : indicatorState.data.enmascarado
        ? "MUESTRA PROTEGIDA"
        : "DATOS ACTUALIZADOS";
  const visibleNavigation = navigation.filter((item) => {
    if (viewer.status === "forbidden" && viewer.user.rol === "staff") {
      return item.href !== "/personal"
        && item.href !== "/modulos/auditoria"
        && item.href !== "#indicadores";
    }
    if (viewer.status !== "authorized") return true;
    if (item.href === "/encuestas") return false;
    if (item.href === "/personal") return viewer.user.rol === "admin";
    if (item.href === "/modulos/auditoria") return viewer.user.rol === "admin";
    return true;
  });
  const canLogoutFromMenu = viewer.status === "authorized"
    || (viewer.status === "forbidden" && viewer.user.rol === "staff");

  if (viewer.status === "checking" || viewer.status === "anonymous" || viewer.status === "unavailable") {
    return (
      <main className="entry-page">
        <section className="entry-card">
          <a className="entry-brand" href="/" aria-label="HospitaPulse">
            <span className="brand-mark"><span>+</span></span>
            <span className="brand-copy"><strong>hospita<span>pulse</span></strong><small>CLIMA ORGANIZACIONAL</small></span>
          </a>
          {viewer.status === "checking" && (
            <p className="entry-status" role="status">Verificando tu sesión…</p>
          )}
          {viewer.status === "unavailable" && (
            <p className="entry-error" role="alert">{viewer.message}</p>
          )}
          {viewer.status === "anonymous" && (
            <form className="entry-form" onSubmit={handleIndicatorLogin}>
              <div>
                <span className="panel-kicker">ACCESO SEGURO</span>
                <h1>Inicia sesión</h1>
                <p>Ingresa con la cuenta que te autorizó el administrador.</p>
              </div>
              <label>Usuario
                <input autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} required />
              </label>
              <label>Contraseña
                <input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required />
              </label>
              <a className="forgot-password-link" href="/recuperar-contrasena">¿Olvidaste tu contraseña?</a>
              {authError && <p className="entry-error" role="alert">{authError}</p>}
              <button className="personnel-primary-button" type="submit" disabled={authWorking}>
                {authWorking ? "Ingresando…" : "Ingresar"}
              </button>
              <p className="entry-help">Tu rol determinará qué opciones estarán disponibles en el menú.</p>
            </form>
          )}
        </section>
      </main>
    );
  }

  if (viewer.status === "forbidden" && viewer.user.debe_cambiar_password) {
    return (
      <main className="entry-page">
        <form className="entry-card entry-form" onSubmit={handleTemporaryPasswordChange}>
          <div className="entry-brand">
            <span className="brand-mark"><span>+</span></span>
            <span className="brand-copy"><strong>hospita<span>pulse</span></strong><small>CLIMA ORGANIZACIONAL</small></span>
          </div>
          <div>
            <span className="panel-kicker">ACTUALIZACIÓN OBLIGATORIA</span>
            <h1>Cambia tu contraseña</h1>
            <p>Debes reemplazar la contraseña temporal antes de entrar al sistema.</p>
          </div>
          <label>Contraseña temporal
            <input type="password" autoComplete="current-password" value={temporaryPassword} onChange={(event) => setTemporaryPassword(event.target.value)} required />
          </label>
          <label>Nueva contraseña
            <input type="password" autoComplete="new-password" minLength={12} maxLength={72} value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required />
            <small>Usa al menos 12 caracteres.</small>
          </label>
          {authError && <p className="entry-error" role="alert">{authError}</p>}
          <button className="personnel-primary-button" type="submit" disabled={authWorking}>
            {authWorking ? "Guardando…" : "Cambiar contraseña y continuar"}
          </button>
        </form>
      </main>
    );
  }

  const sessionUser = viewer.user;
  const displayDate = currentDate
    ? new Intl.DateTimeFormat("es-PE", {
        day: "numeric",
        month: "short",
        timeZone: "America/Lima",
        year: "numeric",
      }).format(currentDate)
    : "Actualizando…";
  const displayTime = currentDate
    ? new Intl.DateTimeFormat("es-PE", {
        hourCycle: "h23",
        hour: "2-digit",
        minute: "2-digit",
        timeZone: "America/Lima",
      }).format(currentDate)
    : "--:--";
  const displayWeekday = currentDate
    ? new Intl.DateTimeFormat("es-PE", {
        day: "numeric",
        month: "long",
        timeZone: "America/Lima",
        weekday: "long",
      }).format(currentDate).toLocaleUpperCase("es-PE")
    : "ACTUALIZANDO FECHA";

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#resumen" aria-label="HospitaPulse, inicio">
          <span className="brand-mark"><span>+</span></span>
          <span className="brand-copy"><strong>hospita<span>pulse</span></strong><small>CLIMA ORGANIZACIONAL</small></span>
        </a>

        <div className="workspace-label">ESPACIO DE TRABAJO</div>
        <div className="hospital-selector" role="group" aria-label="Espacio de trabajo actual">
          <span className="hospital-icon" aria-hidden="true">H</span>
          <span><strong>Hospital Regional</strong><small>Ayacucho, Perú</small></span>
        </div>

        <nav className="main-nav" aria-label="Navegación principal">
          {visibleNavigation.map((item, index) => (
            <Fragment key={item.label}>
              {(index === 0 || visibleNavigation[index - 1].group !== item.group) && (
                <span className="nav-caption">{item.group}</span>
              )}
              <a
                className={`nav-link${(item.href.startsWith("/modulos/")
                ? pathname === item.href
                : item.href === "/encuestas"
                  ? pathname === "/encuestas"
                  : item.href === "/personal"
                    ? pathname === "/personal"
                    : pathname === "/" && item.label === "Resumen") ? " active" : ""}`}
                href={item.href}
              >
                <span className="nav-icon" aria-hidden="true">{item.icon}</span>
                <span>{item.label}</span>
              </a>
            </Fragment>
          ))}
        </nav>

        <div className="sidebar-spacer" />
        <div className="privacy-sidebar">
          <span className="privacy-shield" aria-hidden="true">✓</span>
          <strong>Tu privacidad importa</strong>
          <p>Las respuestas son anónimas. Los resultados solo se muestran en grupos de al menos {PRIVACY_MINIMUM_SAMPLE} respuestas.</p>
          <a href="#privacidad" aria-label="Ver cómo HospitaPulse protege tu privacidad">
            Conoce cómo te protegemos <span aria-hidden="true">↗</span>
          </a>
        </div>
        <button className="nav-link settings-link" type="button">
          <span className="nav-icon" aria-hidden="true">⚙</span><span>Configuración</span>
        </button>
        <div className="profile">
          <div className="avatar" aria-hidden="true">{getUserInitials(sessionUser.nombre_completo)}</div>
          <span className="profile-copy">
            <strong title={sessionUser.nombre_completo}>{sessionUser.nombre_completo}</strong>
            <small>{getRoleLabel(sessionUser.rol)}</small>
          </span>
        </div>
      </aside>

      <section className="main-area" id="resumen">
        <header className="topbar">
          <div className="breadcrumbs"><span>HospitaPulse</span><b>/</b><strong>Resumen</strong></div>
          <div className="topbar-actions">
            <ApiStatus state={apiState} />
            {canLogoutFromMenu && (
              <>
                {authError && <span className="entry-error session-logout-error" role="alert">{authError}</span>}
                <button
                  type="button"
                  className="personnel-logout"
                  onClick={() => void handleIndicatorLogout()}
                  disabled={authWorking}
                >
                  {authWorking ? "Cerrando…" : "Cerrar sesión"}
                </button>
              </>
            )}
            <button type="button" className="icon-button notification-button" aria-label="Notificaciones">
              ♧<i />
            </button>
            <div className="topbar-date">
              <span>HOY · {displayTime}</span>
              <strong>{displayDate}</strong>
            </div>
          </div>
        </header>

        <div className="dashboard-content">
          <div className="welcome-row">
            <div>
              <div className="eyebrow"><span className="eyebrow-line" /> {displayWeekday}</div>
              <h1>Un hospital que escucha,<br /><span>un equipo que crece.</span></h1>
              <p className="welcome-description">Conoce cómo se siente nuestro equipo y construyamos juntos un mejor lugar para cuidar.</p>
            </div>
            <div className="welcome-actions">
              <span className="demo-badge"><span /> {indicatorBadge}</span>
              {viewer.status !== "authorized" && (
                <button className="primary-button" type="button" onClick={() => window.location.assign("/encuestas")}>
                  Explorar encuestas <span>→</span>
                </button>
              )}
            </div>
          </div>

          <section className="hero-card" aria-label="Campaña de bienestar">
            <div className="hero-content">
              <span className="hero-kicker"><span className="sparkle">✳</span> PULSO DE BIENESTAR · NOVIEMBRE</span>
              <h2>Tu voz puede<br />hacer la diferencia.</h2>
              <p>Comparte cómo te sientes. Es breve, confidencial y nos ayuda a cuidar mejor de quienes cuidan.</p>
              {viewer.status !== "authorized" && (
                <button className="hero-button" type="button" onClick={() => window.location.assign("/encuestas")}>
                  Ver encuesta activa <span>↗</span>
                </button>
              )}
            </div>
            <div className="hero-art" aria-hidden="true">
              <div className="art-orbit orbit-one" />
              <div className="art-orbit orbit-two" />
              <div className="art-sun"><span>+</span></div>
              <div className="art-leaf leaf-one" />
              <div className="art-leaf leaf-two" />
              <div className="art-leaf leaf-three" />
              <div className="art-dot dot-one" />
              <div className="art-dot dot-two" />
              <div className="art-label">BIENESTAR<br /><b>EN EQUIPO</b></div>
            </div>
            <span className="hero-index">01 — 03</span>
          </section>

          {viewer.status === "authorized" && (
          <section className="metrics-section" id="indicadores">
            <div className="section-heading">
              <div><h2>El pulso de nuestra comunidad</h2><p>Resultados de las respuestas recibidas en el periodo</p></div>
              <label className="period-picker">
                <span className="visually-hidden">Periodo de indicadores</span>
                <select
                  className="period-button"
                  value={selectedPeriod}
                  onChange={(event) => setSelectedPeriod(event.target.value)}
                  disabled={!selectedPeriod}
                >
                  {periodOptions.map((period) => (
                    <option key={period.value} value={period.value}>{period.label}</option>
                  ))}
                </select>
              </label>
            </div>
            <div className="metrics-grid">
              <article className="metric-card">
                <div className="metric-top"><span className="metric-icon mint">♙</span><span className="metric-tag">POR PERIODO</span></div>
                <span className="metric-label">RESPUESTAS RECIBIDAS</span>
                <div className="metric-value">
                  {indicatorState.status === "loading" ? "…" :
                    indicatorState.status === "ready" && !indicatorState.data.enmascarado
                      ? indicatorState.data.total_respuestas
                      : "—"}
                </div>
                <div className="metric-foot"><span>
                  {indicatorState.status === "error" ? "No disponible" :
                    indicatorState.status === "ready" && indicatorState.data.enmascarado
                      ? "Muestra protegida (N < 5)"
                      : "Envíos anónimos completados"}
                </span></div>
              </article>
              <article className="metric-card">
                <div className="metric-top"><span className="metric-icon lavender">♡</span><span className="metric-tag">ESCALA 1–5</span></div>
                <span className="metric-label">PROMEDIO GENERAL</span>
                <div className="metric-value">
                  {indicatorState.status === "loading" ? "…" :
                    indicatorState.status === "ready" && indicatorState.data.promedio_general !== null
                      ? <>{indicatorState.data.promedio_general.toFixed(2)}<span className="metric-unit">/5</span></>
                      : "—"}
                </div>
                <div className="metric-foot"><span>
                  {indicatorState.status === "error" ? "No disponible" :
                    indicatorState.status === "ready" && indicatorState.data.enmascarado
                      ? "Se muestra al alcanzar N ≥ 5"
                      : "Promedio de las respuestas del periodo"}
                </span></div>
              </article>
              <article className="metric-card">
                <div className="metric-top"><span className="metric-icon peach">▥</span><span className="metric-tag">POR DIMENSIÓN</span></div>
                <span className="metric-label">DIMENSIONES CON RESULTADOS</span>
                <div className="metric-value">
                  {indicatorState.status === "loading" ? "…" :
                    indicatorState.status === "ready" && !indicatorState.data.enmascarado
                      ? indicatorState.data.dimensiones.length
                      : "—"}
                </div>
                <div className="metric-foot"><span>
                  {indicatorState.status === "error" ? "No disponible" :
                    indicatorState.status === "ready" && indicatorState.data.enmascarado
                      ? "Datos ocultos por privacidad"
                      : "Calculadas con respuestas reales"}
                </span></div>
              </article>
            </div>
            <p className="demo-caption">Se contabilizan respuestas recibidas, no personas identificadas. Los datos se ocultan si hay menos de 5 respuestas.</p>
            <section className="dimension-results" aria-live="polite">
              <div className="dimension-results-heading">
                <h3>Promedio por dimensión</h3>
                <span>{indicatorState.status === "ready" && !indicatorState.data.enmascarado ? "Datos del periodo seleccionado" : "Protección de privacidad N ≥ 5"}</span>
              </div>
              {indicatorState.status === "loading" && <p className="indicator-message" role="status">Cargando indicadores…</p>}
              {indicatorState.status === "error" && <p className="indicator-message indicator-error" role="alert">{indicatorState.message}</p>}
              {indicatorState.status === "ready" && indicatorState.data.enmascarado && (
                <p className="indicator-message">Los resultados de este periodo están protegidos. Se mostrarán cuando se reciban al menos 5 respuestas.</p>
              )}
              {indicatorState.status === "ready" && !indicatorState.data.enmascarado && indicatorState.data.dimensiones.length === 0 && (
                <p className="indicator-message">Aún no hay respuestas para este periodo.</p>
              )}
              {indicatorState.status === "ready" && !indicatorState.data.enmascarado && indicatorState.data.dimensiones.map((item) => (
                <div className="dimension-row" key={item.dimension}>
                  <span>{item.dimension}</span>
                  <div
                    className="dimension-track"
                    role="progressbar"
                    aria-label={`${item.dimension}: ${item.promedio.toFixed(2)} de 5`}
                    aria-valuemin={0}
                    aria-valuemax={5}
                    aria-valuenow={item.promedio}
                  >
                    <span style={{ width: `${Math.min(100, Math.max(0, item.promedio / 5 * 100))}%` }} />
                  </div>
                  <strong>{item.promedio.toFixed(2)}<small>/5</small></strong>
                </div>
              ))}
            </section>
          </section>
          )}

          <div className="bottom-grid">
            {viewer.status !== "authorized" && (<section className="panel survey-panel" id="encuestas">
              <div className="panel-heading">
                <div><span className="panel-kicker">PARTICIPA</span><h2>Encuestas para ti</h2></div>
                <a className="text-link" href="/encuestas">Ver encuesta <span>→</span></a>
              </div>
              <article className="survey-item">
                <div className="survey-symbol">✳</div>
                <div className="survey-info"><div className="survey-title-row"><h3>Pulso de bienestar mensual</h3><span className="live-tag"><i /> MENSUAL</span></div><p>Se genera automáticamente al inicio de cada periodo.</p><div className="survey-meta"><span>◷ 3 min</span><span>◉ Anónima</span><span className="deadline">Escala 1–5</span></div></div>
                <a className="round-arrow" href="/encuestas" aria-label="Responder encuesta mensual">↗</a>
              </article>
              <article className="survey-item second-survey">
                <div className="survey-symbol blue-symbol">☼</div>
                <div className="survey-info"><div className="survey-title-row"><h3>Clima de equipo</h3><span className="upcoming-tag">PRÓXIMAMENTE</span></div><p>Una mirada a cómo colaboramos día a día.</p><div className="survey-meta"><span>◷ 5 min</span><span>◉ Anónima</span></div></div>
                <button className="round-arrow disabled-arrow" type="button" aria-label="Encuesta próximamente" disabled>↗</button>
              </article>
            </section>)}

            <section className="panel privacy-panel" id="privacidad">
              <div className="panel-heading">
                <div><span className="panel-kicker">CONFIDENCIALIDAD</span><h2>Privacidad primero</h2></div>
                <span className="lock-icon">⌑</span>
              </div>
              <div className="privacy-visual">
                <div className="privacy-ring"><div className="ring-inner"><span>✳</span><strong>100%</strong><small>ANÓNIMO</small></div></div>
                <div className="privacy-copy"><strong>Tu identidad nunca<br />se comparte.</strong><p>Los resultados solo se muestran cuando hay suficientes respuestas para proteger a todos.</p></div>
              </div>
              <div className="privacy-rule">
                <span className="rule-check">✓</span>
                <span><strong>Regla de muestra mínima</strong><small>Los grupos menores a {PRIVACY_MINIMUM_SAMPLE} se mantienen ocultos.</small></span>
                <span className="rule-value">N ≥ {PRIVACY_MINIMUM_SAMPLE}</span>
              </div>
            </section>
          </div>

          <footer className="page-footer"><span>HospitaPulse <b>·</b> Cuidar a quienes cuidan.</span><span><ApiStatus state={apiState} /></span></footer>
        </div>
      </section>
      <nav className="mobile-nav" aria-label="Navegación móvil">
        {visibleNavigation.map((item) => (
          <a href={item.href} className={pathname === item.href ? "active" : ""} key={item.label}>
            <span aria-hidden="true">{item.icon}</span><small>{item.label}</small>
          </a>
        ))}
      </nav>
    </main>
  );
}
