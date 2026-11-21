# Estructura objetivo e integración backend-frontend

> **Proyecto:** HospitaPulse · Hospital Regional de Ayacucho
> **Arquitectura:** Monolito modular con Clean Architecture + SPA web
> **Backend:** Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy, PostgreSQL, Redis
> **Frontend propuesto:** Next.js App Router, React, TypeScript
> **Estado:** Diseño objetivo con scaffolding inicial de ejecución e integración.
> La API de negocio de los módulos aún debe conectarse; por ahora, la integración
> ejecutable es el health check.

## 1. Organización del repositorio

Se conserva `src/app` como raíz actual del backend. El frontend vive en `frontend/`;
ambas aplicaciones se desarrollan y despliegan separadamente, y se comunican solo
mediante la API HTTP versionada.

```text
.
├── src/                                  # Backend FastAPI
│   ├── app/
│   │   ├── main.py                       # Construye la aplicación FastAPI
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── router.py             # Agrega routers públicos de módulos
│   │   │       └── errors.py             # Traducción central de errores HTTP
│   │   ├── shared/
│   │   │   ├── config.py                 # Configuración desde entorno
│   │   │   ├── database/
│   │   │   │   ├── base.py               # Metadata/base SQLAlchemy compartida
│   │   │   │   └── session.py            # Engine y dependencias de sesión
│   │   │   ├── security/
│   │   │   │   └── current_user.py       # Validación de identidad/token
│   │   │   └── web/
│   │   │       └── pagination.py         # Tipos comunes de paginación
│   │   └── modulos/
│   │       ├── auth/
│   │       ├── usuarios/
│   │       ├── areas/
│   │       ├── encuestas/
│   │       ├── supresion/
│   │       ├── reportes/
│   │       ├── auditoria/
│   │       └── notificaciones/
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── contract/
├── frontend/                             # Next.js + TypeScript
│   ├── src/
│   │   ├── app/                          # Rutas, layouts y páginas
│   │   ├── features/                     # Funcionalidades por módulo
│   │   ├── components/                   # Componentes visuales compartidos
│   │   ├── lib/
│   │   │   ├── api/                      # Cliente OpenAPI y configuración HTTP
│   │   │   ├── auth/                     # Sesión y permisos de interfaz
│   │   │   └── validation/               # Validación de formularios
│   │   └── types/
│   ├── public/
│   └── tests/
├── docs/
│   └── 02-arquitectura-software/
└── README.md
```

## 2. Módulos backend con Clean Architecture

Cada módulo posee sus reglas, puertos y adaptadores. La API pública del módulo
debe exportarse desde `index.py`; otro módulo no importa repositorios ni tablas
internas ajenas.

```text
src/app/modulos/
├── auth/
│   ├── dominio/
│   │   ├── identidad.py
│   │   └── identity_provider_port.py
│   ├── aplicacion/
│   │   ├── login_use_case.py
│   │   └── validar_token_use_case.py
│   ├── infraestructura/
│   │   └── keycloak_oidc_adapter.py
│   ├── presentacion/
│   │   └── auth_routes.py
│   ├── auth_module.py
│   └── index.py
├── usuarios/
│   ├── dominio/
│   │   ├── usuario.py
│   │   ├── rol.py
│   │   └── usuario_repository.py
│   ├── aplicacion/
│   │   ├── crear_usuario_use_case.py
│   │   ├── obtener_usuario_use_case.py
│   │   └── listar_usuarios_use_case.py
│   ├── infraestructura/
│   │   ├── usuario_orm.py
│   │   └── postgres_usuario_repository.py
│   ├── presentacion/
│   │   ├── usuarios_routes.py
│   │   └── usuarios_schemas.py
│   ├── usuarios_module.py
│   └── index.py
├── areas/
│   ├── dominio/                          # Servicio, jerarquía, puertos
│   ├── aplicacion/                       # Consultar/administrar catálogo
│   ├── infraestructura/                  # ORM y repositorios
│   ├── presentacion/                     # Rutas y schemas
│   ├── areas_module.py
│   └── index.py
├── encuestas/
│   ├── dominio/
│   │   ├── encuesta_pulse.py
│   │   ├── respuesta_anonima.py
│   │   ├── estado_encuesta.py
│   │   ├── encuesta_repository.py
│   │   └── supresion_port.py
│   ├── aplicacion/
│   │   ├── registrar_respuesta_use_case.py
│   │   ├── registrar_respuesta_command.py
│   │   └── gestionar_encuesta_use_case.py
│   ├── infraestructura/
│   │   ├── encuesta_orm.py
│   │   └── postgres_encuesta_repository.py
│   ├── presentacion/
│   │   ├── encuestas_routes.py
│   │   └── encuestas_schemas.py
│   ├── encuestas_module.py
│   └── index.py
├── supresion/
│   ├── dominio/
│   │   └── supresion_port.py
│   ├── aplicacion/
│   │   └── evaluar_anonimato_use_case.py
│   ├── infraestructura/
│   │   └── postgres_supresion_adapter.py
│   ├── supresion_module.py
│   └── index.py
├── reportes/
│   ├── dominio/                          # Indicadores y puerto de lectura
│   ├── aplicacion/
│   │   └── generar_reporte_use_case.py
│   ├── infraestructura/
│   │   ├── postgres_reportes_repository.py
│   │   └── cached_reportes_repository.py
│   ├── presentacion/
│   │   ├── reportes_routes.py
│   │   └── reportes_schemas.py
│   ├── reportes_module.py
│   └── index.py
├── auditoria/
│   ├── dominio/                          # Evento y puerto append-only
│   ├── aplicacion/
│   │   └── registrar_auditoria_use_case.py
│   ├── infraestructura/
│   │   ├── auditoria_evento.py
│   │   └── postgres_auditoria_repository.py
│   ├── auditoria_module.py
│   └── index.py
└── notificaciones/
    ├── dominio/                          # Eventos y puerto de notificación
    ├── aplicacion/
    ├── infraestructura/                  # Adaptador de correo/mensajería
    ├── notificaciones_module.py
    └── index.py
```

Dentro de cada módulo:

- **Dominio:** entidades, objetos de valor, reglas e interfaces propias.
- **Aplicación:** casos de uso y comandos; depende del dominio, no de FastAPI/ORM.
- **Infraestructura:** SQLAlchemy, PostgreSQL, Redis y servicios externos.
- **Presentación:** rutas FastAPI y DTO HTTP; traduce petición/respuesta.
- **Composición:** construye implementaciones e inyecta dependencias.

La autenticación se centraliza en Keycloak/OIDC conforme al ADR02. El caso de uso
local de login con contraseña solo debe mantenerse si se decide expresamente no
delegar la autenticación; no deben coexistir dos autoridades de credenciales por
accidente.

## 3. Módulos frontend

```text
frontend/src/
├── app/
│   ├── (publico)/
│   │   └── login/page.tsx
│   ├── (privado)/
│   │   ├── layout.tsx                    # Protección de rutas autenticadas
│   │   ├── encuestas/page.tsx
│   │   ├── encuestas/[encuestaId]/page.tsx
│   │   ├── reportes/page.tsx
│   │   ├── usuarios/page.tsx
│   │   └── administracion/areas/page.tsx
│   ├── api/                              # Route handlers BFF si se habilitan
│   ├── layout.tsx
│   └── page.tsx
├── features/
│   ├── auth/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── services/
│   ├── encuestas/
│   │   ├── components/
│   │   ├── schemas/
│   │   └── services/
│   ├── reportes/
│   ├── usuarios/
│   └── areas/
├── components/
│   ├── ui/
│   └── layout/
└── lib/
    ├── api/
    │   ├── generated/                    # Cliente generado de OpenAPI
    │   └── http.ts
    ├── auth/
    └── config.ts
```

El frontend solo contiene presentación, estado de interfaz y validación de
formularios. Las reglas de autorización, privacidad, consistencia y cálculo de
indicadores se vuelven a validar siempre en el backend.

## 4. Integración entre frontend y backend

### Contrato y transporte

1. FastAPI publica el contrato en `/openapi.json` y Swagger UI en `/docs` para
   desarrollo.
2. El cliente TypeScript se genera desde ese OpenAPI; no se mantienen a mano
   interfaces duplicadas de request/response.
3. Las llamadas usan HTTPS y JSON, con prefijo `/api/v1`.
4. `NEXT_PUBLIC_API_BASE_URL` apunta al backend en desarrollo. En producción se
   recomienda un mismo dominio con proxy o BFF; si el navegador llama a otro
   origen, FastAPI permite CORS solo para los orígenes frontend configurados.
5. Se usa una respuesta de error uniforme y versionada, por ejemplo:

```json
{
  "code": "PRIVACY_SAMPLE_TOO_SMALL",
  "message": "No se puede mostrar el reporte para esta muestra.",
  "details": null,
  "request_id": "..."
}
```

Los códigos HTTP los decide la capa de presentación: `200` para consultas,
`201` para creación, `204` para operaciones sin cuerpo, `401/403` para
autenticación/autorización, `404` para recursos inexistentes y `422` para
validación o reglas de negocio rechazadas.

### Ejemplos iniciales de endpoints

| Método | Ruta | Módulo | Uso desde UI |
|---|---|---|---|
| `GET` | `/api/v1/usuarios/me` | Usuarios/Auth | Cargar perfil y rol |
| `GET` | `/api/v1/areas/servicios` | Áreas | Poblar selectores de servicio |
| `GET` | `/api/v1/encuestas/activas` | Encuestas | Mostrar campañas disponibles |
| `POST` | `/api/v1/encuestas/{encuesta_id}/respuestas` | Encuestas | Enviar respuesta Likert |
| `GET` | `/api/v1/reportes/servicios/{servicio_id}?anio=2026&mes=11` | Reportes | Consultar promedios agregados |
| `POST` | `/api/v1/usuarios` | Usuarios | Crear perfil (solo rol autorizado) |

Los endpoints distintos de salud son una propuesta de contrato; deben
implementarse en routers, schemas, OpenAPI y cliente antes de considerarse
disponibles.

### Autenticación

- Se recomienda flujo OIDC Authorization Code + PKCE con Keycloak.
- La API valida issuer, audiencia, firma, expiración y claims requeridos; no
  confía en un rol enviado por el navegador.
- Preferir cookie `HttpOnly`, `Secure`, `SameSite` mediante BFF cuando se
  requiera reducir exposición del token a JavaScript. Si se usa bearer desde
  el navegador, no guardar tokens de larga duración en `localStorage`.
- Aplicar autorización RBAC en FastAPI para cada endpoint; ocultar botones en
  frontend mejora UX, pero no es un control de seguridad.

### Flujo de envío de encuesta

```text
Personal → UI Next.js → POST FastAPI
        → validar esquema y permisos
        → consultar N del servicio
        → Supresión verifica N >= 5
        → persistir solo si está autorizado
        → responder JSON / error normalizado
        → UI muestra confirmación o mensaje de privacidad
```

### Flujo de reporte y regla N < 5

El caso de uso consulta primero el total del periodo. Si `N < 5`, no solicita ni
devuelve promedios; el frontend presenta un mensaje de muestra insuficiente.
Para preservar privacidad estricta, se recomienda no revelar el conteo exacto
`1..4`: usar `total_participantes: null` o un rango como `"<5"` junto con
`enmascarado: true`. Si se decide devolver el valor exacto como número, ese dato
por sí solo puede revelar información de grupos pequeños.

## 5. Configuración de desarrollo e integración local

Variables de entorno (ejemplo de nombres; guardar secretos solo en el entorno):

```text
BACKEND:
  DATABASE_URL
  REDIS_URL
  KEYCLOAK_ISSUER
  KEYCLOAK_AUDIENCE
  CORS_ALLOWED_ORIGINS

FRONTEND:
  NEXT_PUBLIC_API_BASE_URL
  KEYCLOAK_ISSUER                 # solo si el cliente inicia OIDC
  KEYCLOAK_CLIENT_ID
```

En local, levantar PostgreSQL y Redis, iniciar FastAPI y Next.js por separado,
permitir solo el origen local del frontend en CORS y apuntar el cliente al
`/api/v1` del backend. En CI, generar/verificar el cliente TypeScript desde
OpenAPI y ejecutar pruebas de contrato para detectar cambios incompatibles.

## 6. Pruebas necesarias para declarar la integración lista

- Unitarias de casos de uso y reglas (`N=4` bloqueado, `N=5` permitido).
- Integración de repositorios con PostgreSQL y migraciones.
- Pruebas de API de autenticación, RBAC, validación y errores.
- Pruebas de contrato del cliente TypeScript contra `/openapi.json`.
- E2E: autenticación, responder encuesta, consulta de reporte con muestra
  suficiente e insuficiente.
- Verificar que errores de Supresión o base de datos no se transformen en
  respuestas de éxito ni permitan persistir/reportar sin autorización.
