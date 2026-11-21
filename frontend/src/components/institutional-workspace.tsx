"use client";

import { useCallback, useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";

import {
  cancelEventAttendance,
  confirmEventAttendance,
  createInstitutionalRecord,
  getInstitutionalSession,
  InstitutionalApiError,
  listNominationDirectory,
  listInstitutionalRecords,
  publishInstitutionalRecord,
  updateInstitutionalRecord,
  updateRecognitionConsent,
  type InstitutionalModule,
  type InstitutionalRecord,
  type DirectoryPerson,
} from "@/lib/api/institutional";
import type { SessionUser } from "@/lib/api/personnel";

const moduleMeta: Record<InstitutionalModule, { title: string; description: string; icon: string }> = {
  sugerencias: {
    title: "Buzón de sugerencias",
    description: "Comparte una propuesta de forma anónima y consulta su estado de atención.",
    icon: "✦",
  },
  "planes-mejora": {
    title: "Planes de mejora",
    description: "Acciones institucionales con responsables, plazos y seguimiento de avance.",
    icon: "↗",
  },
  reconocimientos: {
    title: "Reconocimientos",
    description: "Celebra contribuciones positivas con moderación y consentimiento explícito.",
    icon: "♡",
  },
  organigrama: {
    title: "Organigrama institucional",
    description: "Consulta la estructura de áreas y servicios del hospital.",
    icon: "⌘",
  },
  eventos: {
    title: "Actividades y eventos",
    description: "Explora la agenda institucional y confirma voluntariamente tu asistencia.",
    icon: "▦",
  },
  comunicaciones: {
    title: "Comunicaciones",
    description: "Consulta avisos institucionales vigentes y por audiencia.",
    icon: "◉",
  },
  auditoria: {
    title: "Seguridad y auditoría",
    description: "Registro de operaciones administrativas, sin secretos ni respuestas individuales.",
    icon: "⌑",
  },
};

function isManager(user: SessionUser | null): boolean {
  return user?.rol === "admin" || user?.rol === "supervisor";
}

function display(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) return value.map(String).join(" · ");
  if (typeof value === "boolean") return value ? "Sí" : "No";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function FormField({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return <label className="institutional-field"><span>{label}</span>{children}</label>;
}

export default function InstitutionalWorkspace({ module }: { module: InstitutionalModule }) {
  const [records, setRecords] = useState<InstitutionalRecord[]>([]);
  const [directory, setDirectory] = useState<DirectoryPerson[]>([]);
  const [user, setUser] = useState<SessionUser | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [searchText, setSearchText] = useState("");
  const [auditFilters, setAuditFilters] = useState({
    accion: "",
    resultado: "",
    actor_id: "",
    desde: "",
    hasta: "",
  });
  const meta = moduleMeta[module];
  const manager = useMemo(() => isManager(user), [user]);
  const admin = user?.rol === "admin";

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const sessionUser = await getInstitutionalSession();
      const [results, nominationDirectory] = await Promise.all([
        module === "sugerencias" && sessionUser.rol === "staff"
          ? Promise.resolve([])
          : listInstitutionalRecords(
            module,
            module === "auditoria"
              ? Object.fromEntries(Object.entries(auditFilters)
                .filter(([, value]) => value)
                .map(([key, value]) => [
                  key,
                  key === "desde" || key === "hasta" ? new Date(value).toISOString() : value,
                ]))
              : {},
          ),
        module === "reconocimientos" ? listNominationDirectory() : Promise.resolve([]),
      ]);
      setUser(sessionUser);
      setRecords(results);
      setDirectory(nominationDirectory);
    } catch (loadError: unknown) {
      setError(loadError instanceof Error ? loadError.message : "No se pudo cargar el módulo.");
      if (loadError instanceof InstitutionalApiError && loadError.status === 401) {
        window.location.assign("/");
      }
    } finally {
      setLoading(false);
    }
  }, [auditFilters, module]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  function setField(key: string, value: string) {
    setFields((current) => ({ ...current, [key]: value }));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking(true);
    setError(null);
    setNotice(null);
    try {
      const body = getRequestBody(module, fields);
      await createInstitutionalRecord(module, body);
      setFields({});
      setNotice(module === "sugerencias"
        ? "Tu sugerencia anónima fue recibida. Gracias por contribuir."
        : module === "reconocimientos"
          ? "La nominación fue enviada. Su publicación requiere moderación y consentimiento."
          : "El registro se guardó correctamente.");
      await loadData();
    } catch (submitError: unknown) {
      setError(submitError instanceof Error ? submitError.message : "No se pudo guardar el registro.");
    } finally {
      setWorking(false);
    }
  }

  async function runAction(action: () => Promise<unknown>, success: string) {
    setWorking(true);
    setError(null);
    setNotice(null);
    try {
      await action();
      setNotice(success);
      await loadData();
    } catch (actionError: unknown) {
      setError(actionError instanceof Error ? actionError.message : "No se pudo completar la operación.");
    } finally {
      setWorking(false);
    }
  }

  const hasCreateForm = module !== "auditoria"
    && (module !== "reconocimientos" || Boolean(user))
    && (module !== "organigrama" || admin)
    && (module !== "eventos" || manager)
    && (module !== "comunicaciones" || manager)
    && (module !== "planes-mejora" || manager);
  const visibleRecords = module === "organigrama" && searchText.trim()
    ? records.filter((record) => `${record.nombre ?? ""} ${record.tipo ?? ""} ${record.cargo ?? ""}`.toLocaleLowerCase("es-PE").includes(searchText.trim().toLocaleLowerCase("es-PE")))
    : records;

  return (
    <main className="institutional-page">
      <header className="institutional-topbar">
        <a className="survey-brand" href="/">hospita<span>pulse</span></a>
        <nav aria-label="Navegación" className="institutional-breadcrumb">
          <a href="/">Resumen</a><span>/</span><strong>{meta.title}</strong>
        </nav>
        <span className="institutional-user">{user?.nombre_completo ?? "Sesión"}</span>
      </header>
      <div className="institutional-content">
        <a className="institutional-back" href="/">← Volver al resumen</a>
        <section className="institutional-heading">
          <span className="institutional-icon" aria-hidden="true">{meta.icon}</span>
          <div>
            <p className="institutional-kicker">GESTIÓN INSTITUCIONAL</p>
            <h1>{meta.title}</h1>
            <p>{meta.description}</p>
          </div>
        </section>

        {module === "sugerencias" && (
          <div className="institutional-privacy" role="note">
            El sistema no guarda tu cuenta, sesión ni dirección de red junto con el contenido. Evita incluir nombres o datos personales en el texto.
          </div>
        )}
        {error && <p className="institutional-alert error" role="alert">{error}</p>}
        {notice && <p className="institutional-alert success" role="status">{notice}</p>}

        {hasCreateForm && (
          <form className="institutional-card institutional-form" onSubmit={(event) => void submit(event)}>
            <div className="institutional-card-heading">
              <h2>{module === "sugerencias" ? "Comparte tu propuesta" : createTitle(module)}</h2>
              <span>{module === "sugerencias" ? "Envío anónimo" : "Formulario"}</span>
            </div>
            {renderFormFields(module, fields, setField, directory)}
            <button className="personnel-primary-button" type="submit" disabled={working}>
              {working ? "Guardando…" : submitLabel(module)}
            </button>
          </form>
        )}

        <section className="institutional-list-section">
          <div className="institutional-card-heading">
            <div><h2>{listTitle(module)}</h2><p>{module === "auditoria" ? "Últimas operaciones registradas" : `${records.length} ${records.length === 1 ? "registro" : "registros"}`}</p></div>
            <button className="institutional-refresh" onClick={() => void loadData()} type="button" disabled={loading}>Actualizar</button>
          </div>
          {module === "organigrama" && (
            <label className="institutional-search">
              <span>Buscar por unidad, área o cargo</span>
              <input value={searchText} onChange={(event) => setSearchText(event.target.value)} />
            </label>
          )}
          {module === "auditoria" && (
            <div className="institutional-filters">
              <label>Acción<input value={auditFilters.accion} onChange={(event) => setAuditFilters((current) => ({ ...current, accion: event.target.value }))} /></label>
              <label>Resultado<input value={auditFilters.resultado} onChange={(event) => setAuditFilters((current) => ({ ...current, resultado: event.target.value }))} /></label>
              <label>Actor ID<input value={auditFilters.actor_id} onChange={(event) => setAuditFilters((current) => ({ ...current, actor_id: event.target.value }))} /></label>
              <label>Desde<input type="datetime-local" value={auditFilters.desde} onChange={(event) => setAuditFilters((current) => ({ ...current, desde: event.target.value }))} /></label>
              <label>Hasta<input type="datetime-local" value={auditFilters.hasta} onChange={(event) => setAuditFilters((current) => ({ ...current, hasta: event.target.value }))} /></label>
            </div>
          )}
          {loading ? (
            <div className="institutional-empty" role="status">Cargando información…</div>
          ) : visibleRecords.length === 0 ? (
            <div className="institutional-empty">
              {module === "sugerencias" && user?.rol === "staff"
                ? "Por privacidad, no se puede consultar el contenido enviado ni vincularlo a una cuenta."
                : "Aún no hay registros disponibles."}
            </div>
          ) : (
            <div className="institutional-records">
              {visibleRecords.map((record) => (
                <article
                  className="institutional-record"
                  key={record.id}
                  style={module === "organigrama" ? { marginLeft: `${getNodeDepth(record, records) * 18}px` } : undefined}
                >
                  <div className="institutional-record-top">
                    <div>
                      <span className="institutional-record-tag">{display(record.estado ?? record.accion ?? record.tipo)}</span>
                      <h3>{recordTitle(module, record)}</h3>
                    </div>
                    {recordDate(record) && <time>{recordDate(record)}</time>}
                  </div>
                  <p className="institutional-record-description">{recordDescription(module, record, records)}</p>
                  {renderRecordActions(module, record, {
                    manager,
                    admin: Boolean(admin),
                    working,
                    onAction: runAction,
                    onEdit: async (id, body, success) => {
                      await runAction(() => updateInstitutionalRecord(module, id, body), success);
                    },
                  })}
                </article>
              ))}
            </div>
          )}
        </section>
        <footer className="institutional-footer">
          <a href="/">HospitaPulse · Hospital Regional de Ayacucho</a>
          <span>Acceso según rol · Datos protegidos</span>
        </footer>
      </div>
    </main>
  );
}

function createTitle(module: InstitutionalModule): string {
  if (module === "planes-mejora") return "Registrar plan";
  if (module === "reconocimientos") return "Enviar nominación";
  if (module === "organigrama") return "Añadir unidad";
  if (module === "eventos") return "Crear evento";
  return "Redactar comunicación";
}

function listTitle(module: InstitutionalModule): string {
  if (module === "sugerencias") return "Propuestas recibidas";
  if (module === "planes-mejora") return "Seguimiento de planes";
  if (module === "reconocimientos") return "Reconocimientos y consentimiento";
  if (module === "organigrama") return "Estructura publicada";
  if (module === "eventos") return "Agenda institucional";
  if (module === "comunicaciones") return "Avisos vigentes";
  return "Registro de actividad";
}

function submitLabel(module: InstitutionalModule): string {
  return module === "sugerencias" ? "Enviar de forma anónima" : module === "reconocimientos" ? "Enviar nominación" : "Guardar borrador";
}

function getRequestBody(module: InstitutionalModule, fields: Record<string, string>): Record<string, unknown> {
  if (module === "sugerencias") return { categoria: fields.categoria, titulo: fields.titulo || null, detalle: fields.detalle };
  if (module === "planes-mejora") return {
    titulo: fields.titulo,
    objetivo: fields.objetivo,
    dimension: fields.dimension,
    responsable: fields.responsable,
    acciones: fields.acciones.split("\n").map((item) => item.trim()).filter(Boolean),
    fecha_inicio: fields.fecha_inicio,
    fecha_fin: fields.fecha_fin,
  };
  if (module === "reconocimientos") return {
    destinatario_id: fields.destinatario_id,
    categoria: fields.categoria,
    motivo: fields.motivo,
  };
  if (module === "organigrama") return {
    nombre: fields.nombre,
    tipo: fields.tipo,
    cargo: fields.cargo || null,
    padre_id: fields.padre_id || null,
    orden: Number(fields.orden || "0"),
  };
  if (module === "eventos") return {
    titulo: fields.titulo,
    descripcion: fields.descripcion,
    inicio: new Date(fields.inicio).toISOString(),
    ubicacion: fields.ubicacion,
    audiencia: fields.audiencia,
    cupo: fields.cupo ? Number(fields.cupo) : null,
  };
  if (module === "comunicaciones") return {
    titulo: fields.titulo,
    contenido: fields.contenido,
    audiencia: fields.audiencia,
    prioridad: fields.prioridad,
    vigente_desde: fields.vigente_desde ? new Date(fields.vigente_desde).toISOString() : null,
    vigente_hasta: fields.vigente_hasta ? new Date(fields.vigente_hasta).toISOString() : null,
  };
  return {};
}

function renderFormFields(
  module: InstitutionalModule,
  fields: Record<string, string>,
  setField: (key: string, value: string) => void,
  directory: DirectoryPerson[],
): ReactNode {
  const input = (key: string, label: string, required = true, type = "text") => (
    <FormField key={key} label={label}>
      <input type={type} required={required} value={fields[key] ?? ""} onChange={(event) => setField(key, event.target.value)} />
    </FormField>
  );
  const textarea = (key: string, label: string, required = true) => (
    <FormField key={key} label={label}>
      <textarea required={required} value={fields[key] ?? ""} onChange={(event) => setField(key, event.target.value)} rows={4} />
    </FormField>
  );
  const select = (key: string, label: string, choices: string[]) => (
    <FormField key={key} label={label}>
      <select value={fields[key] ?? choices[0]} onChange={(event) => setField(key, event.target.value)}>
        {choices.map((choice) => <option key={choice} value={choice}>{choice.replaceAll("_", " ")}</option>)}
      </select>
    </FormField>
  );

  if (module === "sugerencias") return <div className="institutional-fields">
    {select("categoria", "Categoría", ["bienestar", "comunicacion", "procesos", "seguridad", "otra"])}
    {input("titulo", "Asunto", false)}
    {textarea("detalle", "Tu sugerencia")}
  </div>;
  if (module === "planes-mejora") return <div className="institutional-fields">
    {input("titulo", "Nombre del plan")}{textarea("objetivo", "Objetivo")}
    {input("dimension", "Dimensión")}{input("responsable", "Responsable institucional")}
    {textarea("acciones", "Acciones (una por línea)")}{input("fecha_inicio", "Fecha de inicio", true, "date")}
    {input("fecha_fin", "Fecha de término", true, "date")}
  </div>;
  if (module === "reconocimientos") return <div className="institutional-fields">
    <FormField label="Persona reconocida">
      <select required value={fields.destinatario_id ?? ""} onChange={(event) => setField("destinatario_id", event.target.value)}>
        <option value="" disabled>Selecciona una persona</option>
        {directory.map((person) => <option key={person.id} value={person.id}>{person.nombre_completo}</option>)}
      </select>
    </FormField>
    {select("categoria", "Categoría", ["trabajo_en_equipo", "vocacion_de_servicio", "innovacion", "liderazgo", "otra"])}
    {textarea("motivo", "Motivo del reconocimiento")}
  </div>;
  if (module === "organigrama") return <div className="institutional-fields">
    {input("nombre", "Nombre de unidad o cargo")}
    {select("tipo", "Tipo", ["institucion", "area", "servicio", "cargo"])}
    {input("cargo", "Cargo responsable", false)}{input("padre_id", "ID de unidad superior", false)}
    {input("orden", "Orden", false, "number")}
  </div>;
  if (module === "eventos") return <div className="institutional-fields">
    {input("titulo", "Nombre del evento")}{textarea("descripcion", "Descripción")}
    {input("inicio", "Fecha y hora de inicio", true, "datetime-local")}
    {input("ubicacion", "Lugar")}{select("audiencia", "Audiencia", ["todos", "staff", "supervisores"])}
    {input("cupo", "Cupo (opcional)", false, "number")}
  </div>;
  if (module === "comunicaciones") return <div className="institutional-fields">
    {input("titulo", "Título")}{textarea("contenido", "Contenido")}
    {select("audiencia", "Audiencia", ["todos", "staff", "supervisores"])}
    {select("prioridad", "Prioridad", ["normal", "alta", "urgente"])}
    {input("vigente_desde", "Vigente desde", false, "datetime-local")}
    {input("vigente_hasta", "Vigente hasta", false, "datetime-local")}
  </div>;
  return null;
}

function recordTitle(module: InstitutionalModule, record: InstitutionalRecord): string {
  const field = module === "sugerencias" ? "titulo"
    : module === "organigrama" ? "nombre"
      : module === "auditoria" ? "recurso" : "titulo";
  if (typeof record[field] === "string" && record[field]) return String(record[field]);
  if (module === "reconocimientos") return `Reconocimiento · ${display(record.categoria)}`;
  if (module === "sugerencias") return `Sugerencia · ${display(record.categoria)}`;
  if (module === "auditoria") return `${display(record.accion)} · ${display(record.resultado)}`;
  return `${moduleMeta[module].title} · ${record.id.slice(0, 8)}`;
}

function recordDescription(
  module: InstitutionalModule,
  record: InstitutionalRecord,
  records: InstitutionalRecord[],
): string {
  if (module === "sugerencias") return display(record.detalle);
  if (module === "planes-mejora") return `${display(record.objetivo)} · Acciones: ${display(record.acciones)} · ${display(record.fecha_inicio)} a ${display(record.fecha_fin)} · ${display(record.progreso)}% completado · Responsable: ${display(record.responsable)}`;
  if (module === "reconocimientos") return `${display(record.motivo)} · Consentimiento: ${display(record.consentido)}`;
  if (module === "organigrama") {
    const parent = records.find((item) => item.id === record.padre_id);
    return `${display(record.tipo)}${record.cargo ? ` · ${display(record.cargo)}` : ""} · Superior: ${display(parent?.nombre)}`;
  }
  if (module === "eventos") return `${display(record.descripcion)} · ${display(record.ubicacion)} · ${display(record.audiencia)}`;
  if (module === "comunicaciones") return `${display(record.contenido)} · ${display(record.prioridad)} · Audiencia: ${display(record.audiencia)} · Vigencia: ${display(record.vigente_desde)} a ${display(record.vigente_hasta)}`;
  return `${display(record.accion)} · Actor: ${display(record.actor_id)} · ${display(record.detalle)}`;
}

function recordDate(record: InstitutionalRecord): string | null {
  const value = record.creada_en ?? record.creado_en ?? record.inicio;
  if (typeof value !== "string") return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("es-PE", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

function renderRecordActions(
  module: InstitutionalModule,
  record: InstitutionalRecord,
  controls: {
    manager: boolean;
    admin: boolean;
    working: boolean;
    onAction: (action: () => Promise<unknown>, success: string) => Promise<void>;
    onEdit: (id: string, body: Record<string, unknown>, success: string) => Promise<void>;
  },
): ReactNode {
  if (module === "sugerencias" && controls.manager) {
    return <div className="institutional-record-actions">
      <select aria-label="Estado de sugerencia" defaultValue={String(record.estado)} id={`suggestion-${record.id}`}>
        <option value="en_revision">En revisión</option><option value="respondida">Respondida</option><option value="cerrada">Cerrada</option>
      </select>
      <input aria-label="Respuesta pública" id={`reply-${record.id}`} placeholder="Respuesta pública (opcional)" defaultValue={String(record.respuesta_publica ?? "")} />
      <button disabled={controls.working} onClick={() => {
        const state = document.getElementById(`suggestion-${record.id}`) as HTMLSelectElement | null;
        const reply = document.getElementById(`reply-${record.id}`) as HTMLInputElement | null;
        if (state) void controls.onEdit(record.id, { estado: state.value, respuesta_publica: reply?.value || null }, "Estado actualizado.");
      }} type="button">Actualizar</button>
    </div>;
  }
  if (module === "planes-mejora" && controls.manager) {
    return <div className="institutional-record-actions">
      <label>Progreso <input aria-label="Progreso" type="number" min="0" max="100" defaultValue={String(record.progreso)} id={`progress-${record.id}`} />%</label>
      <select aria-label="Estado del plan" defaultValue={String(record.estado)} id={`plan-${record.id}`}>
        <option value="activo">Activo</option><option value="pausado">Pausado</option><option value="completado">Completado</option>
      </select>
      <button disabled={controls.working} onClick={() => {
        const progress = document.getElementById(`progress-${record.id}`) as HTMLInputElement | null;
        const state = document.getElementById(`plan-${record.id}`) as HTMLSelectElement | null;
        if (progress && state) void controls.onEdit(record.id, { progreso: Number(progress.value), estado: state.value }, "Avance actualizado.");
      }} type="button">Guardar avance</button>
    </div>;
  }
  if (module === "reconocimientos") {
    if (controls.manager) return <div className="institutional-record-actions">
      <button disabled={controls.working} onClick={() => void controls.onEdit(record.id, { estado: "aprobado" }, "Reconocimiento aprobado.")} type="button">Aprobar</button>
      <button className="institutional-secondary-button" disabled={controls.working} onClick={() => void controls.onEdit(record.id, { estado: "rechazado" }, "Reconocimiento rechazado.")} type="button">Rechazar</button>
    </div>;
    return <div className="institutional-record-actions">
      <button disabled={controls.working || record.consentido === true} onClick={() => void controls.onAction(() => updateRecognitionConsent(record.id, true), "Consentimiento registrado.")} type="button">Acepto su publicación</button>
      <button className="institutional-secondary-button" disabled={controls.working || record.consentido !== true} onClick={() => void controls.onAction(() => updateRecognitionConsent(record.id, false), "Consentimiento retirado.")} type="button">Retirar consentimiento</button>
    </div>;
  }
  if (module === "eventos") {
    return <div className="institutional-record-actions">
      {controls.manager && record.estado === "borrador" && <button disabled={controls.working} onClick={() => void controls.onAction(() => publishInstitutionalRecord("eventos", record.id), "Evento publicado.")} type="button">Publicar evento</button>}
      {controls.manager && record.estado !== "cancelado" && <>
        <input aria-label="Título del evento" defaultValue={String(record.titulo)} id={`event-title-${record.id}`} />
        <input aria-label="Ubicación del evento" defaultValue={String(record.ubicacion)} id={`event-location-${record.id}`} />
        <button className="institutional-secondary-button" disabled={controls.working} onClick={() => {
          const title = document.getElementById(`event-title-${record.id}`) as HTMLInputElement | null;
          const location = document.getElementById(`event-location-${record.id}`) as HTMLInputElement | null;
          if (title && location) void controls.onEdit(record.id, { titulo: title.value, ubicacion: location.value }, "Evento actualizado.");
        }} type="button">Guardar título</button>
      </>}
      {controls.manager && record.estado !== "cancelado" && <button className="institutional-secondary-button" disabled={controls.working} onClick={() => void controls.onEdit(record.id, { estado: "cancelado" }, "Evento cancelado.")} type="button">Cancelar evento</button>}
      {record.estado === "publicado" && <>
        <button disabled={controls.working} onClick={() => void controls.onAction(() => confirmEventAttendance(record.id), "Asistencia confirmada.")} type="button">Confirmar asistencia</button>
        <button className="institutional-secondary-button" disabled={controls.working} onClick={() => void controls.onAction(() => cancelEventAttendance(record.id), "Asistencia cancelada.")} type="button">Cancelar asistencia</button>
      </>}
    </div>;
  }
  if (module === "comunicaciones" && controls.manager && record.estado !== "archivada"
    && (controls.admin || record.estado === "borrador")) {
    return <div className="institutional-record-actions">
      <input aria-label="Título de comunicación" defaultValue={String(record.titulo)} id={`communication-title-${record.id}`} />
      <textarea aria-label="Contenido de comunicación" defaultValue={String(record.contenido)} id={`communication-content-${record.id}`} />
      <button className="institutional-secondary-button" disabled={controls.working} onClick={() => {
        const title = document.getElementById(`communication-title-${record.id}`) as HTMLInputElement | null;
        const content = document.getElementById(`communication-content-${record.id}`) as HTMLTextAreaElement | null;
        if (title && content) void controls.onEdit(record.id, { titulo: title.value, contenido: content.value }, "Comunicación actualizada.");
      }} type="button">Guardar título</button>
      {controls.admin && record.estado === "borrador" && <button disabled={controls.working} onClick={() => void controls.onAction(() => publishInstitutionalRecord("comunicaciones", record.id), "Comunicación publicada.")} type="button">Aprobar y publicar</button>}
      {controls.admin && record.estado === "publicada" && <button className="institutional-secondary-button" disabled={controls.working} onClick={() => void controls.onEdit(record.id, { estado: "archivada" }, "Comunicación archivada.")} type="button">Archivar</button>}
    </div>;
  }
  return null;
}

function getNodeDepth(record: InstitutionalRecord, allRecords: InstitutionalRecord[]): number {
  const byId = new Map(allRecords.map((item) => [item.id, item]));
  const seen = new Set<string>();
  let parentId = typeof record.padre_id === "string" ? record.padre_id : null;
  let depth = 0;
  while (parentId && !seen.has(parentId) && depth < 8) {
    seen.add(parentId);
    depth += 1;
    const parent = byId.get(parentId);
    parentId = parent && typeof parent.padre_id === "string" ? parent.padre_id : null;
  }
  return depth;
}
