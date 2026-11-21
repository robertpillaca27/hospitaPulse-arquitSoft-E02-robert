# Especificación SDD — Backend de HospitaPulse

## 1. Propósito y alcance

Especificar los contratos, reglas de dominio, autorización, persistencia y
criterios de aceptación del backend para autenticación, gestión de personal,
encuestas anónimas, indicadores agregados y el asistente Gemini.

- **Tecnologías:** Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy y PostgreSQL.
- **Arquitectura:** Clean Architecture en un monolito modular.
- **Módulos implementados:** `auth`, `usuarios`, `encuestas`, `asistente` y
  `institucional` (MVP para sugerencias, planes, reconocimientos, organigrama,
  eventos, comunicaciones y consulta de auditoría).
- **Restricción crítica:** privacidad de resultados con tamaño de muestra mínimo
  `N ≥ 5`.

El proyecto menciona SSO/Keycloak en documentación de análisis, pero el alcance
de esta iteración usa credenciales locales y JWT en cookie HttpOnly. SSO/Keycloak
no se considera implementado por esta especificación.

> **Estado de alcance:** los requisitos marcados como preparación para producción
> describen capacidades necesarias antes de incorporar personas o datos reales.
> No implican que el envío de correo, la recuperación por correo o el despliegue
> productivo ya estén implementados.
>
> Los módulos institucionales cuentan con almacenamiento y endpoints MVP bajo
> `/institucional`. No se deben confundir con una solución lista para producción:
> retención, despliegue controlado de migraciones, monitoreo, auditoría completa
> de autenticación y varios flujos avanzados siguen pendientes. Existe una
> migración inicial Alembic; los respaldos son manuales y locales.

## 2. Reglas de arquitectura

1. Los casos de uso de aplicación dependen de interfaces/puertos y no de
   FastAPI, SQLAlchemy ni detalles de presentación.
2. El dominio contiene reglas puras y no depende de infraestructura.
3. La presentación valida DTOs, invoca casos de uso y traduce errores a HTTP.
4. La infraestructura implementa persistencia y servicios criptográficos
   consumidos mediante abstracciones.
5. La autorización se aplica en el backend para cada ruta protegida; el control
   visual del frontend no es suficiente.

## 3. Infraestructura de desarrollo

### BE-INF-01 — PostgreSQL mediante Docker Compose

Para el entorno local de desarrollo, PostgreSQL debe poder ejecutarse mediante
Docker Compose desde el servicio `db` definido en `compose.yaml`.

- Usar PostgreSQL 16 Alpine.
- Configurar la base, el usuario y la contraseña mediante `POSTGRES_DB`,
  `POSTGRES_USER` y `POSTGRES_PASSWORD`, definidos localmente en `.env` y no
  versionados con credenciales reales.
- El backend debe conectarse usando `DATABASE_URL`, cuyos valores de host, puerto,
  base de datos, usuario y contraseña deben corresponder al servicio configurado.
- En el entorno local, publicar PostgreSQL solo en loopback (`127.0.0.1:5432`).
- Conservar los datos del contenedor en el volumen nombrado
  `hospitapulse-postgres-data`.
- El servicio debe incluir un healthcheck con `pg_isready` para detectar cuándo
  la base está disponible.
- Los pasos de configuración y los comandos operativos se documentan en el
  [README](../README.md); esta especificación define el comportamiento esperado.

Esta configuración describe el entorno local de desarrollo, no una política de
despliegue de producción.

### BE-INF-02 — Caché Redis de indicadores

- Redis se ejecuta en desarrollo mediante el servicio `redis` de `compose.yaml`,
  publicado solo en `127.0.0.1:6379` y con healthcheck.
- El backend conecta mediante `REDIS_URL`; el TTL se configura con
  `REDIS_INDICATORS_TTL_SECONDS` y su valor predeterminado es 60 segundos.
- Cachear únicamente el resultado seguro tras aplicar la regla de privacidad:
  agregados con `N ≥ 5` o un resultado enmascarado sin conteos ni promedios con
  `N < 5`. Nunca cachear respuestas individuales, credenciales, tokens ni identidad.
- La clave se delimita por año y mes. Al persistir una nueva respuesta, invalidar
  la clave del periodo correspondiente.
- Si Redis falla, registrar la incidencia y consultar PostgreSQL; el TTL limita
  la antigüedad máxima de una clave si una invalidación no pudiera realizarse.
- Redis es una optimización: la indisponibilidad de la caché no debe cambiar la
  autorización ni la regla de privacidad.

### BE-INF-03 — Chequeo y ejecución local de los servicios

El backend debe permanecer disponible en `http://127.0.0.1:8000` en el entorno
local y exponer `GET /api/v1/health` con una respuesta de estado compatible con
monitoreo básico.

La raíz `GET /` y la raíz versionada `GET /api/v1/` deben responder `200 OK` con
información básica de disponibilidad y enlaces relativos a la documentación y
al chequeo de salud. Estas rutas no sustituyen el healthcheck ni exponen datos
de negocio.

```json
{
  "status": "ok",
  "service": "hospitaPulse-api"
}
```

Al iniciar Docker Compose, los servicios `db` y `redis` deben estar saludables
antes de ejecutar flujos que dependan de persistencia o caché. PostgreSQL se
publica únicamente en `127.0.0.1:5432` y Redis únicamente en
`127.0.0.1:6379` para el desarrollo local.

El prefijo público `/api/v1` forma parte de los paths HTTP y no debe omitirse
cuando el cliente envía solicitudes al backend. El archivo `.env` debe contener
los valores locales de base de datos, Redis, JWT y administrador; las credenciales
reales no deben agregarse a la documentación ni a los ejemplos versionados.

En Docker Compose, la API debe resolver PostgreSQL con el nombre de servicio
`db` y Redis con `redis`, no con `localhost` desde dentro de la red de contenedores.

## 4. Roles y permisos del backend

| Rol | Rutas autorizadas | Rutas denegadas |
|---|---|---|
| `staff` | Login/sesión, encuestas, enviar sugerencias/nominaciones, consultar planes publicados, organigrama, eventos, comunicaciones y reconocimientos propios/publicados. | Indicadores y moderación/administración institucional. |
| `supervisor` | Login/sesión, indicadores, moderar sugerencias/reconocimientos, gestionar planes/eventos y preparar sus comunicaciones. | Encuestas, cuentas, organigrama y auditoría. |
| `admin` | Login/sesión, indicadores y administración de cuentas y módulos institucionales, incluida auditoría. | Obtener encuestas y registrar respuestas. |

Una cuenta debe estar activa para autenticarse. Una cuenta que debe cambiar su
contraseña no puede acceder a funciones protegidas hasta completar el cambio.

## 5. Requisitos funcionales

### BE-RF-01 — Autenticación

Autenticar por nombre de usuario y contraseña. Verificar el hash con bcrypt,
rechazar cuentas inactivas y devolver el mismo error público para usuario
inexistente, contraseña incorrecta o cuenta inactiva, evitando enumeración de
cuentas.

### BE-RF-02 — Sesión segura

Al autenticar correctamente, generar un JWT firmado y establecerlo en cookie
HttpOnly. Los atributos `Secure`, `SameSite`, `Path` y expiración deben definirse
por configuración segura del entorno. El JWT y la cookie deben expirar
absolutamente a los 10 minutos del login, aunque la persona siga usando la
aplicación. El endpoint de logout elimina la cookie.

### BE-RF-03 — Cambio obligatorio de contraseña

Permitir el cambio de contraseña a una sesión válida. Verificar la contraseña
actual, exigir que la nueva sea distinta, persistir únicamente su hash y limpiar
la marca de cambio obligatorio. Renovar la cookie/sesión tras el cambio.

### BE-RF-04 — Encuesta mensual idempotente

Obtener o crear la encuesta correspondiente al mes actual. Solicitudes
repetidas, incluidas las concurrentes, deben producir como máximo una encuesta
por periodo.

### BE-RF-05 — Registro anónimo

Autorizar el envío únicamente para `staff`. Persistir las respuestas sin
`usuario_id` ni una relación directa o indirecta recuperable que identifique al
participante. La identidad autenticada sirve únicamente para autorizar el envío.

### BE-RF-06 — Validación de respuestas

Cada ítem debe incluir un `pregunta_id` válido y un `valor` entero estricto en el
rango inclusivo `1..5`. Rechazar colecciones vacías, campos adicionales y tipos
coercionados.

### BE-RF-07 — Indicadores

Autorizar indicadores solo a `admin` y `supervisor`. Con `N ≥ 5`, devolver el
total de respuestas, promedio general y promedios por dimensión. Con `N < 5`,
enmascarar el resultado y no divulgar ninguno de esos valores.

### BE-RF-08 — Administración

Restringir la creación de cuentas y asignación de roles a `admin`. La contraseña
temporal debe generarse de forma segura, almacenarse como hash y mostrarse una
sola vez. Permitir a `admin` restablecer la contraseña de otra cuenta con una
credencial temporal aleatoria, almacenar solo su hash y exigir cambio al
siguiente login. El retiro de acceso se realiza desactivando la cuenta, sin
borrado físico. Las credenciales de administrador inicial deben obtenerse de
configuración externa, no de valores hardcodeados.

La operación de restablecimiento se ofrece en
`POST /personal/{usuario_id}/restablecer-password`; devuelve `usuario` y
`password_temporal` en la respuesta autorizada, con `409` si el administrador
intenta restablecer su propia cuenta y `404` si el usuario no existe. El estado
se administra mediante `PATCH /personal/{usuario_id}/estado`.

#### Importación masiva de personal

Un administrador puede subir un archivo `.xlsx` de hasta 5 MB a
`POST /personal/importar`. Las columnas admitidas son `Nombre`, `DNI`,
`Teléfono`, `Usuario`, `Email` y `Rol`. La importación no almacena el archivo.

- `Nombre` o `Nombre completo` es obligatorio.
- `Usuario` es opcional: si está vacío se deriva del DNI.
- `Email` es opcional: si está vacío se genera una dirección interna basada en
 el usuario.
- `Rol` admite Personal/Staff, Supervisor o Administrador.
- Cada fila falla o se crea de forma independiente; el resultado indica fila,
 cuenta creada o motivo de omisión.
- Las cuentas importadas requieren cambio de contraseña en su primer acceso.

### BE-RF-09 — Invitación a cuentas mediante correo institucional

Como preparación para producción, permitir que un administrador invite a una
persona mediante su correo institucional autorizado. El correo debe incluir un
enlace con token aleatorio, de un solo uso y con expiración. Persistir únicamente
un hash del token. Al aceptar la invitación, la persona establece su propia
contraseña y la cuenta queda activada según la política de verificación definida.
No enviar contraseñas temporales en texto plano por correo.

La lista de dominios institucionales permitidos y las credenciales del proveedor
de correo deben ser configuración externa por entorno. No registrar tokens de
invitación ni credenciales en logs.

### BE-RF-10 — Recuperación de acceso

Como preparación para producción, permitir solicitar restablecimiento de
contraseña usando el correo verificado de la cuenta. La respuesta pública debe
ser genérica para evitar revelar si una dirección está registrada. El enlace
debe usar un token aleatorio de un solo uso, con expiración y almacenado como
hash. Tras un cambio exitoso, invalidar el token y las sesiones activas de la
cuenta, y notificar al correo verificado.

Las solicitudes deben tener limitación de frecuencia. No se debe enviar la
contraseña anterior o nueva por correo.

En el MVP sin correo saliente configurado, la página pública debe informar a la
persona que contacte a un administrador. Solo el administrador autenticado puede
emitir una contraseña temporal mediante la gestión de personal; no se debe
presentar como enviado un correo que el sistema no envió.

### BE-RF-11 — Asistente de preguntas abiertas

Exponer `POST /asistente/chat` para recibir una única pregunta de hasta 1200
caracteres y responderla mediante Gemini configurado en el backend.
La clave API debe residir exclusivamente en configuración secreta del servidor,
mediante `GEMINI_API_KEY`. El modelo se configura con `GEMINI_MODEL`, cuyo valor
predeterminado es `gemini-3.5-flash-lite`.
Enviar a Gemini únicamente la pregunta actual y las instrucciones de sistema; no enviar
historial, identidad, respuestas de encuestas ni indicadores. No persistir los
mensajes. Aplicar límite de frecuencia por cliente y límite de salida. Si falta
la clave, la cuota está agotada o el modelo configurado no está disponible,
devolver `503` con un mensaje que indique la acción necesaria; ante otros
errores del proveedor o una respuesta inválida, devolver un error explícito `502`.

### BE-RF-12 — Buzón anónimo de sugerencias

Permitir crear sugerencias sin persistir identidad, sesión, dirección IP ni
metadatos que permitan asociar el texto con su remitente. El formulario puede
contener categoría, título y detalle; el backend valida longitud y bloquea
campos de identidad no declarados. `admin` y `supervisor` pueden clasificar,
asignar y cambiar el estado de una sugerencia. La respuesta institucional se
publica de forma general; no se crea un canal individual de seguimiento.

### BE-RF-13 — Planes de mejora

Permitir a `admin` y `supervisor` crear y actualizar planes con objetivo,
dimensión agregada, responsable institucional, acciones, plazos, estado y
medida de avance. El personal puede consultar planes publicados. Las referencias
a indicadores deben cumplir N ≥ 5 y evitar inferencia por comparación; no se
deben asociar planes a respuestas individuales ni a grupos suprimidos.

### BE-RF-14 — Reconocimientos

Permitir nominaciones voluntarias entre cuentas activas. La publicación requiere
moderación y consentimiento explícito de la persona reconocida, que podrá
retirarlo. No generar nominaciones desde encuestas ni almacenar información
sensible en el motivo. El acceso de gestión corresponde a `admin` y
`supervisor`; los usuarios autenticados consultan reconocimientos publicados.

### BE-RF-15 — Organigrama institucional

Permitir consultar la jerarquía institucional y administrar nodos, unidades,
servicios y relaciones solo a `admin`. Los datos visibles se limitan a nombre
institucional, cargo/rol laboral y unidad autorizados. No incluir teléfono,
correo personal ni relaciones con encuestas.

### BE-RF-16 — Actividades y eventos

Permitir a `admin` y `supervisor` crear, editar, cancelar y publicar eventos con
horario, ubicación, audiencia y cupo opcional. Usuarios autenticados pueden
consultar eventos vigentes y confirmar o cancelar asistencia cuando se habilite.
La asistencia se limita a la gestión del evento, tiene retención definida y no
se utiliza para inferir participación o respuestas de encuestas.

### BE-RF-17 — Comunicaciones institucionales

Permitir redactar, previsualizar, programar, publicar, editar y archivar
comunicaciones con audiencia, prioridad y vigencia. `admin` publica; `supervisor`
puede preparar borradores sujetos a aprobación. Los usuarios autenticados solo
consultan comunicaciones publicadas para su audiencia. Los acuses de lectura,
si se activan, se limitan al propósito de comunicación y no contienen secretos.

### BE-RF-18 — Seguridad y auditoría

Registrar eventos de autenticación y cambios administrativos relevantes en un
registro protegido contra modificación ordinaria. Cada entrada contiene fecha,
acción, resultado, recurso y actor autenticado cuando exista. `admin` puede
consultarlo en modo de solo lectura. Excluir contraseñas, tokens, claves,
respuestas individuales, texto completo de sugerencias y datos personales
innecesarios; definir retención y control de exportación antes del despliegue.

## 6. Contratos HTTP

Los paths siguientes se expresan debajo del prefijo de API configurado.

### 6.0 `GET /health`

El chequeo operativo integrado expone `GET /api/v1/health`. Responde `200 OK`
con el estado y nombre del servicio; no requiere autenticación.

### 6.1 `POST /auth/login`

**Request**

```json
{
  "username": "usuario",
  "password": "contraseña"
}
```

- `username`: `StrictStr`, longitud 1–64.
- `password`: `StrictStr`, longitud 1–128.
- Rechazar campos adicionales.

**Respuestas**

- `200 OK`: devuelve la identidad segura de sesión (id, username, nombre
  completo, correo, rol, estado activo y `debe_cambiar_password`) y establece la
  cookie JWT HttpOnly.
- `401 Unauthorized`: credenciales no válidas o cuenta inactiva.
- `422 Unprocessable Entity`: request inválido.
- `503 Service Unavailable`: configuración de autenticación ausente.

**Nota de evolución del contrato:** el pedido inicial indicó `access_token`,
`token_type`, `rol` y `servicio_id` en el cuerpo. El flujo integrado actual usa
cookie HttpOnly y devuelve la identidad segura de sesión; el JWT no se expone en
el JSON.

### 6.2 `GET /auth/me`

Requiere cookie válida. Devuelve la identidad y los permisos asociados a la
sesión. Una cookie ausente, expirada o inválida produce `401 Unauthorized`.

### 6.3 `POST /auth/logout`

Elimina la cookie de sesión y responde `204 No Content`.

### 6.4 `PATCH /auth/password`

**Request**

```json
{
  "password_actual": "contraseña-temporal",
  "password_nueva": "nueva-contraseña-segura"
}
```

- Ambos campos son cadenas estrictas.
- `password_actual`: longitud 1–128.
- `password_nueva`: mínimo 12 caracteres y máximo 72 bytes UTF-8 por
  compatibilidad con bcrypt.
- La nueva contraseña debe diferir de la actual.
- Requiere sesión válida; un cambio correcto renueva la cookie.

### 6.5 `GET /encuestas/actual`

Requiere `staff` activo y sin cambio de contraseña pendiente. Devuelve la
encuesta del periodo actual o la crea idempotentemente si todavía no existe.

### 6.6 `POST /encuestas/{encuesta_id}/respuestas`

**Request**

```json
{
  "respuestas": [
    {
      "pregunta_id": "id-pregunta",
      "valor": 4
    }
  ]
}
```

- Lista `respuestas` no vacía.
- `pregunta_id`: cadena estricta no vacía.
- `valor`: entero estricto entre 1 y 5.
- Rechazar campos adicionales.
- Requiere rol `staff`.

**Respuestas**

- `201 Created`: respuestas aceptadas; acuse anónimo sin identidad del
  participante.
- `404 Not Found`: encuesta inexistente.
- `409 Conflict`: encuesta cerrada.
- `422 Unprocessable Entity`: solicitud inválida o regla de dominio incumplida.
- `401 Unauthorized` / `403 Forbidden`: sesión ausente o rol no autorizado.

### 6.7 `GET /encuestas/indicadores?anio={anio}&mes={mes}`

- Requiere rol `admin` o `supervisor`.
- `anio`: entero entre 2000 y 2100.
- `mes`: entero entre 1 y 12.
- Con `N < 5`: `enmascarado=true`; `total_respuestas` y
  `promedio_general` nulos; no devolver promedios por dimensión.
- Con `N ≥ 5`: devolver `total_respuestas`, `promedio_general` y dimensiones.

### 6.8 `POST /asistente/chat`

**Request**

```json
{
  "pregunta": "¿Cómo se diseña una arquitectura de software?"
}
```

- `pregunta`: cadena recortada, de 1 a 1200 caracteres.
- Rechazar campos adicionales, incluido cualquier historial de conversación.
- No requiere sesión para que también ayude en el acceso inicial.

**Respuestas**

- `200 OK`: `{ "respuesta": "..." }`.
- `422 Unprocessable Entity`: pregunta vacía, demasiado larga o campos extra.
- `429 Too Many Requests`: más de 12 preguntas por minuto para el cliente.
- `502 Bad Gateway`: falla del proveedor o respuesta inválida.
- `503 Service Unavailable`: `GEMINI_API_KEY` no está configurada o Gemini
  reporta una cuota agotada o el modelo configurado no está disponible.

Solo se envían a Gemini la pregunta actual y las instrucciones del sistema. No
se envían identidad, historial, respuestas ni indicadores. Las preguntas no se
persisten en HospitaPulse. El proveedor procesa el texto conforme a sus políticas
y a la configuración de la cuenta del servicio.

### 6.9 Módulos institucionales (MVP implementado)

Todas las rutas usan el prefijo `/institucional` y requieren una sesión válida
sin cambio de contraseña pendiente. FastAPI valida las entradas con DTO
estrictos que rechazan campos no declarados.

| Ruta | Operación implementada | Acceso |
|---|---|---|
| `/sugerencias` | `POST` crear; `GET` listar con `limit`; `PATCH /{id}` moderar categoría, estado y respuesta pública | Envío solo `staff`; listado/moderación `admin`/`supervisor`. El contenido no guarda actor, cuenta, sesión ni IP; no hay canal de seguimiento individual. |
| `/planes-mejora` | `GET`; `POST`; `PATCH /{id}` | Lectura autenticada; personal solo ve estados distintos de borrador; gestión `admin`/`supervisor`. |
| `/reconocimientos` | `GET`; `POST`; `PATCH /{id}` moderar; `POST /{id}/consentimiento` | Nominación autenticada; moderación `admin`/`supervisor`; consulta y consentimiento limitados a persona destinataria. |
| `/directorio` | `GET` personas activas por nombre e ID mínimo | Sesión autenticada; se usa para seleccionar destinatario de reconocimiento. |
| `/organigrama` | `GET`; `POST`; `PATCH /{id}` | Consulta autenticada; escritura solo `admin`; se rechazan relaciones cíclicas. |
| `/eventos` | `GET`; `POST`; `PATCH /{id}`; `POST /{id}/publicar`; `PUT` y `DELETE /{id}/asistencia` | Consulta según audiencia; gestión `admin`/`supervisor`; asistencia autenticada y limitada por cupo. |
| `/comunicaciones` | `GET`; `POST`; `PATCH /{id}`; `POST /{id}/publicar` | Lectura según audiencia/vigencia; `supervisor` redacta/edita sus borradores; solo `admin` publica o archiva. |
| `/auditoria` | `GET` con `limit`, `accion`, `resultado`, `actor_id`, `desde` y `hasta` | Solo `admin`; sin endpoints de edición o borrado. |

El envío de una sugerencia no genera un evento de auditoría con el actor, porque
eso volvería a vincular la identidad con el contenido. La tabla de auditoría
actual registra acciones administrativas genéricas y asistencia a eventos; aún
no registra todos los intentos de login/logout ni aplica retención inmutable.
La asistencia se almacena separada de las respuestas de encuestas.

Este contrato no implementa programación avanzada, notificaciones, acuses de
lectura, exportaciones ni filtros avanzados de eventos/planes. Existe una
migración inicial Alembic para el esquema; el inicio de la aplicación aún usa
`create_all` y el workflow de despliegue ECS no aplica migraciones. Antes de
producción se requieren migraciones controladas y política de retención aprobada.

**Deuda arquitectónica del MVP:** las rutas de `institucional_routes.py`
coordinan directamente operaciones SQLAlchemy. Esto no satisface todavía la
regla de Clean Architecture de que la presentación invoque casos de uso y estos
dependan de puertos. Antes de considerar el módulo terminado, se debe extraer
validación/orquestación a casos de uso y encapsular consultas/persistencia en
adaptadores, conservando los contratos HTTP y las pruebas de privacidad.

## 7. Requisitos no funcionales

- **Seguridad:** nunca almacenar contraseñas en texto plano; secretos JWT y
  credenciales iniciales provienen de configuración externa.
- **Configuración de base de datos:** el backend obtiene su conexión de
  `DATABASE_URL`; no debe codificar credenciales ni depender de una configuración
  distinta a la documentada para el entorno.
- **Privacidad:** aplicar el umbral en el backend antes de construir cualquier
  resultado divulgable.
- **Anonimato:** la persistencia de respuestas no contiene identificadores de
  usuario ni claves de correlación hacia la cuenta.
- **Tipado:** DTOs con Pydantic v2 estricto, límites explícitos y `extra="forbid"`
  donde aplique.
- **Errores:** traducir errores de forma explícita a HTTP; no filtrar existencia
  de cuentas ni datos privados.
- **Idempotencia:** asegurar unicidad de la encuesta por periodo mediante la
  regla de aplicación y una garantía de persistencia apropiada.

### RNF-07 — Despliegue de producción

Antes de habilitar cuentas o datos reales, el backend debe desplegarse en una
infraestructura autorizada por la institución, detrás de HTTPS y con secretos
inyectados desde un gestor seguro o mecanismo equivalente del proveedor.
Credenciales de base de datos, claves JWT y credenciales de correo no deben
estar en Git, imágenes de contenedor, logs ni código del frontend.

La base de datos de producción no debe exponerse directamente a Internet. El
despliegue debe contar con política de actualización, migraciones controladas,
copias de seguridad y un procedimiento probado de restauración. Docker Compose
descrito en este documento es para desarrollo local y no se considera por sí
mismo una arquitectura de producción.

El repositorio incluye `scripts/db-backup.sh` y `scripts/db-restore.sh` para
operación manual de PostgreSQL en Docker Compose. No programan copias ni prueban
restauración en AWS; esos controles siguen pendientes para producción.

En AWS ECS, PostgreSQL debe montar almacenamiento persistente sobre EFS en
`/var/lib/postgresql/data`. La tarea debe resolver la base por AWS Cloud Map,
usar acceso privado entre tareas y conservar los datos durante reemplazos o
reinicios del servicio. La persistencia debe verificarse reiniciando la tarea de
PostgreSQL y la API, y comprobando que encuestas, respuestas anónimas y usuarios
siguen disponibles. Las respuestas individuales migradas entre ambientes deben
contener únicamente datos anonimizados de encuesta; no deben trasladarse
identificadores de cuenta ni claves de correlación.

La presentación temporal por Internet puede realizarse mediante Cloudflare Quick
Tunnel sobre el Application Load Balancer. El túnel entrega HTTPS para frontend
y rutas `/api/v1`, mientras ECS mantiene separados los procesos de frontend,
backend, PostgreSQL, Redis y `cloudflared`. Esta modalidad es válida para
demostración; su URL no es estable y no reemplaza un certificado/dominio
institucional, WAF ni los controles operativos de producción.

La persistencia desplegada debe superar el siguiente criterio: después de forzar
un nuevo despliegue de PostgreSQL y de la API, el endpoint de indicadores debe
conservar el conteo y los agregados existentes. Durante la validación de
noviembre de 2026, se conservaron 28 respuestas anónimas con promedio general
2.64/5 y resultados de cinco dimensiones tras reiniciar ambas tareas.

### RNF-08 — Correo institucional

El envío de invitaciones y recuperación debe usar un proveedor de correo
transaccional autorizado por TI. El dominio remitente y los dominios permitidos
de usuarios deben ser configurables. Configurar y verificar SPF, DKIM y DMARC
para el dominio remitente cuando la organización gestione dicho dominio.

### RNF-09 — Protección de privacidad en operación

Antes de procesar datos reales, obtener aprobación institucional y documentar
finalidad, base legal, aviso a participantes, retención, acceso y procedimiento
de eliminación de datos personales, de acuerdo con las políticas aplicables.
Minimizar los datos y la retención de logs. No registrar credenciales, tokens ni
respuestas individuales junto con identificadores de cuenta.

La regla agregada `N ≥ 5` no es garantía suficiente de anonimato por sí sola.
Revisar si marcas de tiempo, dirección IP, servicio, secuencia de respuestas u
otros metadatos permiten correlacionar una respuesta con una persona. La
configuración de logging y analítica debe evitar esa correlación; no se debe
prometer anonimato si la arquitectura o los metadatos permiten reidentificación.

## 8. Criterios de aceptación del backend

| ID | Dado | Cuando | Entonces |
|---|---|---|---|
| BE-AC-01 | Credenciales válidas de cuenta activa | Se ejecuta login | Se crea cookie HttpOnly y se devuelve identidad segura. |
| BE-AC-02 | Cuenta inactiva o credenciales erróneas | Se ejecuta login | Se devuelve `401` sin revelar si el usuario existe. |
| BE-AC-03 | Sesión ausente/inválida o rol no autorizado | Se solicita ruta protegida | La operación se rechaza en backend. |
| BE-AC-04 | Usuario `admin` o `supervisor` | Solicita encuesta o registra respuestas | Se rechaza la operación. |
| BE-AC-05 | Usuario `staff` autorizado y envío válido | Registra respuestas | Recibe `201`; el almacenamiento no asocia respuestas con su id. |
| BE-AC-06 | Respuesta vacía, valor fuera de 1..5 o tipo no estricto | Envía respuesta | Se devuelve `422`. |
| BE-AC-07 | Muestra con N=0 o N=4 | Consulta indicadores | No se devuelve conteo ni promedios. |
| BE-AC-08 | Muestra con N=5 o N>5 | Consulta indicadores autorizada | Se devuelven total, promedio general y promedios por dimensión. |
| BE-AC-09 | Cambio de contraseña pendiente | Intenta usar una función protegida | Debe cambiar la contraseña antes de continuar. |
| BE-AC-10 | Encuesta del periodo ya existente | Se solicita obtener/crear encuesta actual | No se crea una segunda encuesta para el periodo. |
| BE-AC-11 | `.env` de desarrollo configurado | Se inicia el servicio `db` con Docker Compose | PostgreSQL queda disponible en `127.0.0.1:5432` y conserva datos en `hospitapulse-postgres-data`. |
| BE-AC-12 | PostgreSQL está saludable y `DATABASE_URL` coincide | Se inicia el backend | El backend puede conectarse a la base sin credenciales hardcodeadas. |
| BE-AC-13 | Administrador autorizado y correo institucional permitido | Invita a una persona | Se genera un enlace temporal de un solo uso; solo se persiste el hash del token y no se envía contraseña. |
| BE-AC-14 | Usuario solicita recuperación para una dirección existente o inexistente | Envía solicitud | La respuesta pública no revela si la cuenta existe y el flujo aplica limitación de frecuencia. |
| BE-AC-15 | Token de recuperación válido | Usuario establece nueva contraseña | El token se invalida y se revocan las sesiones activas de la cuenta. |
| BE-AC-16 | Se configura despliegue productivo | Se publica el backend | Se usa HTTPS, secretos externos y base de datos no expuesta públicamente; existen copias y restauración probada. |
| BE-AC-17 | Se prepara incorporación de usuarios reales | Se habilita el procesamiento | Hay aprobación institucional y revisión documentada de privacidad, retención y riesgo de reidentificación. |
| BE-AC-18 | Redis contiene o no contiene el periodo consultado | Se solicitan indicadores autorizados | Un acierto evita consultar PostgreSQL; el resultado conserva la regla N ≥ 5. |
| BE-AC-19 | Se registra una respuesta del periodo | Se consulta de nuevo sus indicadores | La entrada del caché se invalida y se reflejan los datos persistidos. |
| BE-AC-20 | Redis no está disponible | Se consultan o guardan indicadores | Se registra una advertencia y la API usa PostgreSQL sin exponer datos bajo N<5. |
| BE-AC-21 | Backend local con Redis y cuenta autorizada | Se ejecuta `tests/load/indicators.js` | La prueba de solo lectura rechaza destinos no locales, consulta indicadores con 50 VUs durante 2 min y comprueba error HTTP <1 % y p95 <500 ms. |
| BE-AC-22 | Gemini está configurado | Se envía una pregunta válida | Se responde con el proveedor desde el backend y solo se envía la pregunta actual, sin historial ni datos internos. |
| BE-AC-23 | Pregunta vacía, mayor a 1200 caracteres o con campos adicionales | Se solicita respuesta | Se devuelve `422` sin llamar al proveedor. |
| BE-AC-24 | Falta API key, se supera el límite local, se agota la cuota o falla Gemini | Se solicita respuesta | Se devuelve respectivamente `503`, `429`, `503` o `502` sin fingir una respuesta exitosa. |
| BE-AC-25 | Personal envía una sugerencia | Se persiste y luego se modera | No se guarda identidad, IP ni dato de sesión; solo roles autorizados pueden moderarla. |
| BE-AC-26 | Se crea o publica un plan con indicadores | Un rol consulta el plan | La escritura exige `admin`/`supervisor`, la lectura pública exige publicación y cualquier indicador cumple N ≥ 5. |
| BE-AC-27 | Reconocimiento pendiente de consentimiento | Se intenta publicarlo | El sistema impide publicarlo; revocar consentimiento retira la publicación. |
| BE-AC-28 | Usuario autenticado consulta o administra el organigrama | Ejecuta lectura o cambio | Lectura respeta autenticación; escritura está restringida a `admin` y omite datos personales no autorizados. |
| BE-AC-29 | Usuario registra asistencia a un evento o consulta una comunicación | Ejecuta la operación | Se valida vigencia/audiencia; la asistencia no se usa en encuestas y las comunicaciones se publican según aprobación. |
| BE-AC-30 | Se registra un evento de seguridad | `admin` consulta auditoría | El evento es de solo lectura y no contiene secretos, respuestas individuales ni texto completo de sugerencias. |
| BE-AC-31 | Usuario activo inicia sesión o cambia su contraseña | Se emite una sesión | JWT y cookie expiran 10 minutos después, sin ampliarse por actividad posterior. |
| BE-AC-32 | Administrador restablece una cuenta distinta de la suya | Se procesa la solicitud | Se devuelve una contraseña temporal de una sola lectura; se persiste solo el hash y se exige cambiarla al siguiente acceso. |
| BE-AC-33 | Usuario solicita recuperación sin correo habilitado | Abre la página de recuperación | La API no afirma que envió correo; la persona es dirigida a solicitar ayuda al administrador. |
| BE-AC-34 | Administrador retira acceso a una cuenta | Desactiva la cuenta | La cuenta no puede iniciar sesión y sus registros no se eliminan. |
| BE-AC-35 | Se inicia Docker Compose con `db` y `redis` | Se consulta el chequeo de salud del backend | `GET /api/v1/health` responde `200` sin autenticación y los servicios locales quedan publicados solo en loopback. |

## 9. Prompts técnicos de implementación — Backend

### BE-PROMPT-01 — Autenticación

> Implementa la autenticación del módulo `auth` en la capa de aplicación con
> Clean Architecture. Define una entrada con `username` y `password`; verifica
> el hash bcrypt y el estado activo; evita enumerar cuentas; genera JWT firmado
> mediante dependencia inyectada y establece la sesión en cookie HttpOnly. Usa
> DTOs Pydantic v2 estrictos en la frontera HTTP, tipos explícitos y puertos para
> persistencia/criptografía. No expongas el token en el cuerpo JSON del flujo
> integrado.

### BE-PROMPT-02 — Registro anónimo

> Implementa el caso de uso para registrar respuestas de encuesta. Valida que la
> encuesta esté abierta, que las preguntas pertenezcan a ella y que cada valor
> sea un entero estricto de 1 a 5. Autoriza solo `staff`; almacena las respuestas
> sin `usuario_id` ni vínculo recuperable con la cuenta. Mantén FastAPI y
> SQLAlchemy fuera del dominio y del caso de uso. Traduce explícitamente errores
> de dominio a códigos HTTP.

### BE-PROMPT-03 — Indicadores privados

> Implementa indicadores mensuales para `admin` y `supervisor`. Si N es menor que
> cinco, devuelve resultado enmascarado y omite conteo, promedio general y
> dimensiones. Si N es cinco o más, devuelve esos agregados. Añade pruebas
> específicas para N=0, N=4, N=5 y N>5, verificando los campos ausentes o nulos y
> la ausencia de fuga de información.

### BE-PROMPT-04 — Autorización por rol

> Protege en backend todas las rutas según el rol: `staff` responde encuestas;
> `supervisor` consulta indicadores; `admin` consulta indicadores y gestiona
> cuentas. `admin` y `supervisor` no pueden responder encuestas. Exige cuenta
> activa y bloquea funciones hasta completar el cambio obligatorio de contraseña.
> Añade pruebas positivas y negativas por rol.

### BE-PROMPT-05 — Gestión de cuentas

> Permite crear cuentas y asignar roles únicamente a `admin`. Genera contraseña
> temporal segura, almacénala como hash, muéstrala una sola vez y exige cambio en
> el primer acceso. Carga las credenciales de bootstrap desde configuración
> externa; no las hardcodees.

### BE-PROMPT-06 — Idempotencia mensual

> Implementa obtener/crear encuesta mensual idempotente, incluso ante
> solicitudes concurrentes. Asegura como máximo una encuesta por periodo usando
> una garantía apropiada en persistencia y cubre el comportamiento con pruebas.

### BE-PROMPT-07 — Preparación para producción

> Prepara el backend para despliegue productivo sin reutilizar valores de
> desarrollo. Lee los requisitos RNF-07 a RNF-09 y los criterios BE-AC-16 y
> BE-AC-17 de `docs/spec-backend.md`. Exige HTTPS, secretos inyectados desde un
> gestor seguro, base de datos no pública, migraciones controladas, backups con
> restauración probada y logging minimizado. Documenta qué configuración debe
> proporcionar TI y cuáles controles siguen pendientes. No afirmes que la
> aplicación cumple privacidad o seguridad institucional sin evidencia y
> aprobación correspondientes.

### BE-PROMPT-08 — Invitaciones y recuperación por correo

> Implementa invitación de cuentas y recuperación de contraseña según BE-RF-09 y
> BE-RF-10 de `docs/spec-backend.md`. Usa tokens aleatorios de un solo uso,
> expirables y persistidos solo como hash; verifica el correo institucional
> conforme a una allowlist configurable; evita enumerar cuentas, aplica límites
> de frecuencia y no envíes contraseñas por correo. Integra el envío mediante un
> puerto de correo y un proveedor configurado fuera del código. Añade pruebas
> para expiración, reutilización, direcciones no autorizadas, respuestas
> genéricas y revocación de sesiones tras recuperación. Trata esta funcionalidad
> como pendiente hasta que esté implementada, configurada y verificada en el
> entorno institucional.

### BE-PROMPT-09 — Caché Redis y prueba de carga

> Implementa caché Redis solo para los indicadores agregados, según BE-INF-02.
> Usa claves por año/mes, TTL configurable con valor predeterminado de 60
> segundos e invalidación tras una respuesta guardada. Nunca caches respuestas
> individuales ni datos identificables. Si Redis falla, registra una advertencia
> y consulta PostgreSQL, preservando la supresión N<5. Añade pruebas unitarias
> para hit, miss, TTL, invalidación, fallback y privacidad. Crea una prueba k6 de
> solo lectura con 50 usuarios virtuales durante 2 minutos, límites de latencia y
> errores, restringida a localhost. Documenta cómo ejecutarla y deja claro que
> sus resultados no certifican capacidad de producción.

## 10. Evidencia y estado de validación

- **Caché Redis:** se implementó el adaptador y la integración con indicadores;
  la clave se invalida después de persistir una respuesta.
- **Pruebas unitarias de caché:** seis pruebas pasan, incluyendo round-trip con
  TTL, rechazo de agregados con muestra menor que cinco, resultado enmascarado,
  cache hit, invalidación y fallback cuando Redis no está disponible.
- **Redis local:** el servicio Docker Compose pasó su healthcheck y se verificó
  `PING`/`PONG`; también se comprobó directamente lectura, almacenamiento e
  invalidación con el adaptador.
- **Comprobaciones estáticas:** sintaxis Python, sintaxis del script JavaScript
  y configuración Docker Compose validadas.
- **Migración y respaldos:** se agregó una migración inicial Alembic y scripts
  manuales para PostgreSQL local. La migración del entorno AWS y la restauración
  desde un respaldo no se han ejecutado/validado aquí.
- **CI y E2E:** GitHub Actions contiene jobs de pruebas, build de contenedores y
  un smoke E2E Playwright (login administrativo e indicadores). No se afirma
  que el workflow ni el E2E se hayan ejecutado en GitHub/AWS.
- **Prueba k6:** ejecución local contra servicios aislados, registrada en
  `docs/evidence/k6-indicators-output.txt`: 50 VUs durante 2 minutos, 57,173
  solicitudes, 0 % de errores HTTP y p95 de 182.64 ms. Cumplió los umbrales
  `http_req_failed < 1 %` y `p95 < 500 ms`. Es evidencia de un entorno local,
  no una garantía de capacidad en producción.
- **Límite de evidencia:** pasar pruebas locales no constituye certificación de
  seguridad, privacidad ni capacidad para un despliegue productivo.
