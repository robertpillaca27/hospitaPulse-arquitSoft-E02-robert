"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";

import {
  changePassword,
  changePersonnelRole,
  changePersonnelStatus,
  createPersonnel,
  importPersonnel,
  getCurrentSession,
  listPersonnel,
  login,
  logout,
  PersonnelApiError,
  resetPersonnelPassword,
  type ImportedPersonnel,
  type PersonnelRole,
  type PersonnelUser,
  type SessionUser,
} from "@/lib/api/personnel";

type ScreenState =
  | { status: "loading" }
  | { status: "anonymous"; error?: string }
  | { status: "authenticated"; user: SessionUser }
  | { status: "unavailable"; message: string };

const roleLabels: Record<PersonnelRole, string> = {
  admin: "Administrador",
  supervisor: "Supervisor",
  staff: "Personal",
};

function isPersonnelRole(value: string): value is PersonnelRole {
  return value === "admin" || value === "supervisor" || value === "staff";
}

const roleDescriptions: Record<PersonnelRole, string> = {
  admin: "Gestiona cuentas, roles y accesos.",
  supervisor: "Consulta indicadores agregados del hospital.",
  staff: "Participa en las encuestas anónimas.",
};

function formatDate(dateString: string): string {
  return new Intl.DateTimeFormat("es-PE", {
    dateStyle: "medium",
  }).format(new Date(dateString));
}

export default function PersonalPage() {
  const [screen, setScreen] = useState<ScreenState>({ status: "loading" });
  const [personnel, setPersonnel] = useState<PersonnelUser[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [working, setWorking] = useState(false);
  const [loginUsername, setLoginUsername] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [loginError, setLoginError] = useState<string | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);
  const [newAccount, setNewAccount] = useState<{
    nombre_completo: string;
    username: string;
    email: string;
    rol: PersonnelRole;
  }>({ nombre_completo: "", username: "", email: "", rol: "staff" });
  const [createdCredentials, setCreatedCredentials] = useState<{
    nombre: string;
    username: string;
    password: string;
  } | null>(null);
  const [currentPassword, setCurrentPassword] = useState("");
  const [nextPassword, setNextPassword] = useState("");
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [importResult, setImportResult] = useState<ImportedPersonnel | null>(null);
  const [importError, setImportError] = useState<string | null>(null);

  async function loadPersonnel() {
    setLoadError(null);
    try {
      setPersonnel(await listPersonnel());
    } catch (error: unknown) {
      setLoadError(error instanceof Error ? error.message : "No se pudo cargar el personal.");
    }
  }

  useEffect(() => {
    let active = true;
    getCurrentSession()
      .then(async (user) => {
        if (!active) return;
        setScreen({ status: "authenticated", user });
        if (user.rol === "admin" && !user.debe_cambiar_password) {
          await loadPersonnel();
        }
      })
      .catch((error: unknown) => {
        if (!active) return;
        if (error instanceof PersonnelApiError && error.status === 401) {
          setScreen({ status: "anonymous" });
          return;
        }
        setScreen({
          status: "unavailable",
          message: error instanceof Error ? error.message : "No se pudo consultar la sesión.",
        });
      });
    return () => { active = false; };
  }, []);

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking(true);
    setLoginError(null);
    try {
      const user = await login(loginUsername.trim(), loginPassword);
      setLoginPassword("");
      setScreen({ status: "authenticated", user });
      if (user.rol === "admin" && !user.debe_cambiar_password) await loadPersonnel();
    } catch (error: unknown) {
      setLoginError(error instanceof Error ? error.message : "No se pudo iniciar sesión.");
    } finally {
      setWorking(false);
    }
  }

  async function handleLogout() {
    setWorking(true);
    try {
      await logout();
      setPersonnel([]);
      setScreen({ status: "anonymous" });
    } catch (error: unknown) {
      setLoadError(error instanceof Error ? error.message : "No se pudo cerrar sesión.");
    } finally {
      setWorking(false);
    }
  }

  async function handlePasswordChange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking(true);
    setPasswordError(null);
    try {
      const user = await changePassword(currentPassword, nextPassword);
      setCurrentPassword("");
      setNextPassword("");
      setScreen({ status: "authenticated", user });
      if (user.rol === "admin") await loadPersonnel();
    } catch (error: unknown) {
      setPasswordError(error instanceof Error ? error.message : "No se pudo cambiar la contraseña.");
    } finally {
      setWorking(false);
    }
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking(true);
    setCreateError(null);
    try {
      const result = await createPersonnel(newAccount);
      setCreatedCredentials({
        nombre: result.usuario.nombre_completo,
        username: result.usuario.username,
        password: result.password_temporal,
      });
      setNewAccount({ nombre_completo: "", username: "", email: "", rol: "staff" });
      await loadPersonnel();
    } catch (error: unknown) {
      setCreateError(error instanceof Error ? error.message : "No se pudo crear la cuenta.");
    } finally {
      setWorking(false);
    }
  }

  async function handleImport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const input = event.currentTarget.elements.namedItem("archivo") as HTMLInputElement | null;
    const file = input?.files?.[0];
    if (!file) {
      setImportError("Selecciona un archivo Excel .xlsx.");
      return;
    }
    setWorking(true);
    setImportError(null);
    setImportResult(null);
    try {
      const result = await importPersonnel(file);
      setImportResult(result);
      await loadPersonnel();
    } catch (error: unknown) {
      setImportError(error instanceof Error ? error.message : "No se pudo importar el Excel.");
    } finally {
      setWorking(false);
    }
  }

  async function handleRoleChange(userId: string, rol: PersonnelRole) {
    setWorking(true);
    setLoadError(null);
    try {
      const updated = await changePersonnelRole(userId, rol);
      setPersonnel((current) => current.map((user) => user.id === userId ? updated : user));
    } catch (error: unknown) {
      setLoadError(error instanceof Error ? error.message : "No se pudo cambiar el rol.");
    } finally {
      setWorking(false);
    }
  }

  async function handleStatusChange(user: PersonnelUser) {
    setWorking(true);
    setLoadError(null);
    try {
      const updated = await changePersonnelStatus(user.id, !user.activo);
      setPersonnel((current) => current.map((item) => item.id === user.id ? updated : item));
    } catch (error: unknown) {
      setLoadError(error instanceof Error ? error.message : "No se pudo cambiar el estado.");
    } finally {
      setWorking(false);
    }
  }

  async function handlePasswordReset(user: PersonnelUser) {
    if (!window.confirm(`¿Restablecer la contraseña de ${user.nombre_completo}? La contraseña actual dejará de funcionar.`)) {
      return;
    }
    setWorking(true);
    setLoadError(null);
    setCreatedCredentials(null);
    try {
      const result = await resetPersonnelPassword(user.id);
      setCreatedCredentials({
        nombre: result.usuario.nombre_completo,
        username: result.usuario.username,
        password: result.password_temporal,
      });
      setPersonnel((current) => current.map((item) => item.id === user.id ? result.usuario : item));
    } catch (error: unknown) {
      setLoadError(error instanceof Error ? error.message : "No se pudo restablecer la contraseña.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <main className="personnel-page">
      <header className="personnel-header">
        <Link className="survey-back-link" href="/">← Volver al resumen</Link>
        <Link className="survey-brand" href="/">Hospita<span>Pulse</span></Link>
      </header>

      <section className="personnel-content">
        <div className="survey-page-kicker"><span /> ACCESOS Y PERMISOS</div>
        <div className="personnel-title-row">
          <div>
            <h1>Gestión de personal</h1>
            <p>Administra quién puede acceder y qué acciones tiene permitidas.</p>
          </div>
          {screen.status === "authenticated" && (
            <button className="personnel-logout" type="button" onClick={handleLogout} disabled={working}>
              Cerrar sesión
            </button>
          )}
        </div>

        {screen.status === "loading" && <div className="personnel-card" role="status">Verificando acceso…</div>}
        {screen.status === "unavailable" && <div className="personnel-card personnel-error" role="alert">{screen.message}</div>}
        {screen.status === "anonymous" && (
          <form className="personnel-card personnel-login" onSubmit={handleLogin}>
            <div className="personnel-card-heading">
              <span className="personnel-icon">⌑</span>
              <div><h2>Inicia sesión</h2><p>Solo los administradores pueden autorizar cuentas.</p></div>
            </div>
            <label>Usuario<input autoComplete="username" value={loginUsername} onChange={(event) => setLoginUsername(event.target.value)} required /></label>
            <label>Contraseña<input type="password" autoComplete="current-password" value={loginPassword} onChange={(event) => setLoginPassword(event.target.value)} required /></label>
            <Link className="forgot-password-link" href="/recuperar-contrasena">¿Olvidaste tu contraseña?</Link>
            {screen.error && <p className="personnel-form-error" role="alert">{screen.error}</p>}
            {loginError && <p className="personnel-form-error" role="alert">{loginError}</p>}
            <button className="personnel-primary-button" type="submit" disabled={working}>{working ? "Ingresando…" : "Ingresar"}</button>
            <p className="personnel-login-help">La cuenta inicial se configura mediante <code>ADMIN_USERNAME</code> y <code>ADMIN_PASSWORD</code> en el `.env` del backend.</p>
          </form>
        )}
        {screen.status === "authenticated" && screen.user.debe_cambiar_password && (
          <form className="personnel-card personnel-login" onSubmit={handlePasswordChange}>
            <div className="personnel-card-heading">
              <span className="personnel-icon">⌑</span>
              <div><h2>Cambia tu contraseña temporal</h2><p>Debes definir una contraseña personal antes de continuar.</p></div>
            </div>
            <label>Contraseña temporal<input type="password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required /></label>
            <label>Nueva contraseña<input type="password" autoComplete="new-password" minLength={12} maxLength={72} value={nextPassword} onChange={(event) => setNextPassword(event.target.value)} required /><small>Usa al menos 12 caracteres.</small></label>
            {passwordError && <p className="personnel-form-error" role="alert">{passwordError}</p>}
            <button className="personnel-primary-button" type="submit" disabled={working}>{working ? "Guardando…" : "Cambiar contraseña"}</button>
          </form>
        )}
        {screen.status === "authenticated" && !screen.user.debe_cambiar_password && screen.user.rol !== "admin" && (
          <div className="personnel-card personnel-denied" role="status">
            <span className="personnel-icon">⌑</span>
            <h2>Esta sección requiere permisos de administrador</h2>
            <p>Tu rol actual es <strong>{roleLabels[screen.user.rol]}</strong>. Si necesitas gestionar accesos, solicita autorización a un administrador.</p>
          </div>
        )}
        {screen.status === "authenticated" && !screen.user.debe_cambiar_password && screen.user.rol === "admin" && (
          <>
            <div className="personnel-current-user">
              <span className="personnel-avatar">{screen.user.nombre_completo.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase()}</span>
              <span><strong>{screen.user.nombre_completo}</strong><small>Sesión de administrador · {screen.user.username}</small></span>
            </div>
            {loadError && <p className="personnel-form-error personnel-global-error" role="alert">{loadError}</p>}
            {createdCredentials && (
              <section className="temporary-credentials" aria-live="polite">
                <button className="temporary-close" type="button" onClick={() => setCreatedCredentials(null)} aria-label="Cerrar">×</button>
                <span className="temporary-kicker">CONTRASEÑA TEMPORAL · GUARDA ESTOS DATOS</span>
                <h2>{createdCredentials.nombre}</h2>
                <p>Usuario: <code>{createdCredentials.username}</code></p>
                <p>Contraseña temporal: <code>{createdCredentials.password}</code></p>
                <small>Se muestra solo ahora. La persona deberá cambiarla al iniciar sesión.</small>
              </section>
            )}
            <section className="personnel-card personnel-import">
              <div className="personnel-card-heading">
                <span className="personnel-icon">⇧</span>
                <div>
                  <h2>Crear usuarios desde Excel</h2>
                  <p>Archivo .xlsx con columnas Nombre, DNI, Teléfono, Usuario, Email y Rol.</p>
                </div>
              </div>
              <form onSubmit={handleImport}>
                <label>Archivo Excel<input name="archivo" type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" disabled={working} required /></label>
                <small>Usuario usa DNI si la columna Usuario está vacía. El rol admite Personal, Supervisor o Administrador.</small>
                {importError && <p className="personnel-form-error" role="alert">{importError}</p>}
                <button className="personnel-primary-button" type="submit" disabled={working}>{working ? "Importando…" : "Importar usuarios"}</button>
              </form>
              {importResult && (
                <div className="personnel-import-result" aria-live="polite">
                  <strong>{importResult.creados} creados · {importResult.omitidos} omitidos</strong>
                  {importResult.creados_detalle.map((item) => (
                    <div key={`${item.fila}-${item.usuario}`}>
                      <span>Fila {item.fila}: <b>{item.nombre}</b></span>
                      <code>{item.usuario}</code>
                      <code>{item.password_temporal}</code>
                    </div>
                  ))}
                  {importResult.errores.map((item) => (
                    <p key={`${item.fila}-${item.usuario ?? "fila"}`}>Fila {item.fila}: {item.error}</p>
                  ))}
                </div>
              )}
            </section>
            <div className="personnel-layout">
              <section className="personnel-card personnel-create">
                <div className="personnel-card-heading">
                  <span className="personnel-icon">＋</span>
                  <div><h2>Agregar personal</h2><p>La contraseña temporal aparecerá una sola vez.</p></div>
                </div>
                <form onSubmit={handleCreate}>
                  <label>Nombre completo<input value={newAccount.nombre_completo} onChange={(event) => setNewAccount({ ...newAccount, nombre_completo: event.target.value })} minLength={3} maxLength={160} required /></label>
                  <label>Usuario<input autoComplete="off" value={newAccount.username} onChange={(event) => setNewAccount({ ...newAccount, username: event.target.value })} minLength={3} maxLength={64} pattern="[a-zA-Z0-9._\\-]+" required /><small>Solo letras, números, punto, guion y guion bajo.</small></label>
                  <label>Correo institucional<input type="email" autoComplete="off" value={newAccount.email} onChange={(event) => setNewAccount({ ...newAccount, email: event.target.value })} maxLength={254} required /></label>
                  <label>Rol inicial<select value={newAccount.rol} onChange={(event) => {
                    if (isPersonnelRole(event.target.value)) {
                      setNewAccount({ ...newAccount, rol: event.target.value });
                    }
                  }}><option value="staff">Personal</option><option value="supervisor">Supervisor</option><option value="admin">Administrador</option></select><small>{roleDescriptions[newAccount.rol]}</small></label>
                  {createError && <p className="personnel-form-error" role="alert">{createError}</p>}
                  <button className="personnel-primary-button" type="submit" disabled={working}>{working ? "Creando…" : "Crear cuenta"}</button>
                </form>
              </section>

              <section className="personnel-card personnel-list">
                <div className="personnel-card-heading">
                  <span className="personnel-icon">♙</span>
                  <div><h2>Personal y autorizaciones</h2><p>{personnel.length} cuentas registradas</p></div>
                </div>
                {personnel.length === 0 && !loadError && <p className="personnel-empty">Aún no hay cuentas de personal.</p>}
                <div className="personnel-table-wrap">
                  {personnel.length > 0 && (
                    <table className="personnel-table">
                      <thead><tr><th>PERSONA</th><th>ROL Y PERMISOS</th><th>ESTADO</th><th>ACCESO</th><th>CONTRASEÑA</th></tr></thead>
                      <tbody>
                        {personnel.map((user) => (
                          <tr key={user.id}>
                            <td><strong>{user.nombre_completo}</strong><small>@{user.username} · {user.email}</small><small>Alta: {formatDate(user.creado_en)}</small></td>
                            <td><select aria-label={`Rol de ${user.nombre_completo}`} value={user.rol} onChange={(event) => {
                              if (isPersonnelRole(event.target.value)) {
                                void handleRoleChange(user.id, event.target.value);
                              }
                            }} disabled={working}><option value="staff">Personal</option><option value="supervisor">Supervisor</option><option value="admin">Administrador</option></select><small>{roleDescriptions[user.rol]}</small></td>
                            <td><span className={`personnel-status ${user.activo ? "enabled" : "disabled"}`}>{user.activo ? "Activo" : "Inactivo"}</span>{user.debe_cambiar_password && <small>Debe cambiar clave</small>}</td>
                            <td><button className={`personnel-toggle ${user.activo ? "turn-off" : "turn-on"}`} type="button" onClick={() => void handleStatusChange(user)} disabled={working}>{user.activo ? "Desactivar" : "Activar"}</button></td>
                            <td>{user.id !== screen.user.id && <button className="personnel-reset-password" type="button" onClick={() => void handlePasswordReset(user)} disabled={working}>Restablecer</button>}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </section>
            </div>
            <section className="personnel-roles-note">
              <strong>Roles disponibles</strong>
              <span><b>Administrador</b> · autoriza cuentas y asigna roles.</span>
              <span><b>Supervisor</b> · consulta indicadores agregados con privacidad N ≥ 5.</span>
              <span><b>Personal</b> · participa en encuestas anónimas.</span>
              <span>Desactivar una cuenta retira su acceso sin borrar sus registros ni el historial institucional.</span>
            </section>
          </>
        )}
      </section>
    </main>
  );
}
