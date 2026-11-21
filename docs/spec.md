# Especificación SDD — HospitaPulse

> Especificación maestra. Para consultar requisitos por componente, ver
> [especificación de Backend](./spec-backend.md) y
> [especificación de Frontend](./spec-frontend.md). Para la evidencia del
> despliegue AWS/Cloudflare, consultar el
> [informe técnico de implementación](./informe-implementacion-y-despliegue.md).

## 1. Propósito

Definir los requisitos funcionales, contratos, restricciones y criterios de aceptación
para el flujo de autenticación por roles, participación en encuestas anónimas,
consulta de indicadores agregados y administración de cuentas de HospitaPulse.
Esta especificación consolida los requisitos solicitados durante el desarrollo
iterativo del sistema.

## 2. Contexto y alcance

- **Producto:** HospitaPulse, sistema de gestión del clima organizacional para el
  Hospital Regional de Ayacucho.
- **Estilo arquitectónico:** Clean Architecture en un monolito modular.
- **Backend:** Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy y PostgreSQL.
- **Frontend:** Next.js.
- **Caché:** Redis para los indicadores agregados del backend; no almacena
  respuestas individuales ni datos identificables.
- **Pruebas de carga:** k6 para el endpoint de indicadores en entorno local y
  únicamente contra `localhost` o `127.0.0.1`.
- **Alcance de esta especificación:** inicio de sesión, autorización por rol,
  cambio de contraseña temporal, encuestas, anonimato, regla de privacidad y
  consulta de indicadores, administración básica de personal y asistente de
  preguntas abiertas con proveedor Gemini. También incluye versiones MVP del
  buzón de sugerencias, planes de mejora, reconocimientos, organigrama,
  actividades y eventos, comunicaciones y consulta de auditoría.

### 2.1 Decisión de alcance de autenticación

En los documentos de análisis del proyecto se menciona autenticación centralizada
SSO con Keycloak. El flujo desarrollado y solicitado en esta iteración utiliza
credenciales locales y una sesión basada en JWT almacenada en cookie HttpOnly.
Por tanto, la integración SSO/Keycloak se considera fuera del alcance de esta
especificación de iteración y no debe darse por implementada por los requisitos
descritos aquí.

### 2.2 Estado del menú institucional

El estado se refiere a capacidades comprobadas en la aplicación actual, no solo
a carpetas o nombres de módulos:

| Opción solicitada | Estado actual | Prioridad sugerida | Funcionalidad disponible o propuesta |
|---|---|---|---|
| Dashboard | Implementado como **Resumen** (`/`) | — | Resumen del periodo, selector de periodos recientes, indicadores protegidos y acceso a la encuesta según el rol. |
| Analítica institucional | Parcial, bajo **Indicadores** | P1 para evolución | Promedio general y por dimensiones para un periodo. Ampliar con tendencias y comparaciones seguras; mantener supresión y prevenir inferencias entre periodos. |
| Encuestas | Implementado | — | Encuesta mensual Likert anónima, registro para personal e indicadores agregados con regla N ≥ 5. |
| Buzón de sugerencias | MVP implementado | P1 | Recepción anónima sin identidad persistida, clasificación, moderación y respuesta pública; no hay seguimiento individual. |
| Planes de mejora | MVP implementado | P1 | Acciones, responsable, fechas, progreso y estado; referencias analíticas se limitan a datos agregados divulgables. |
| Reconocimientos | MVP implementado | P3 | Nominación, moderación y consentimiento revocable antes de publicación. |
| Organigrama institucional | MVP implementado | P2 | Consulta jerárquica de unidades/cargos y mantenimiento administrativo de nodos. |
| Actividades y eventos | MVP implementado | P2 | Creación, publicación, cancelación, audiencia y confirmación/cancelación de asistencia con cupo. |
| Comunicaciones | MVP implementado | P2 | Borradores, audiencia, prioridad, vigencia, aprobación, edición básica y archivo. |
| Asistente IA | Integrado; conexión real no verificada en esta actualización | — | Asistente de preguntas abiertas con Gemini; envía solo la pregunta actual. Requiere `GEMINI_API_KEY` y un modelo disponible. |
| Usuarios y roles | Implementado | — | Administración de cuentas, roles y estado de acceso desde Personal. |
| Seguridad y auditoría | MVP implementado | P1 | Consulta de operaciones administrativas con filtros por acción, resultado y actor; no constituye un registro completo de autenticación. |

Las opciones con estado **MVP implementado** tienen API y pantallas conectadas,
pero no representan una certificación de producción ni el cumplimiento integral
de todos los criterios de evolución descritos abajo. Se agregó una migración
inicial de Alembic, respaldos/restauración manuales para Compose, CI y un smoke
E2E; siguen pendientes la aplicación controlada de migraciones al desplegar en
AWS, respaldos automatizados y restauración probada allí, además de retención,
monitoreo, calendario/filtros avanzados, aprobaciones institucionales y
auditoría de autenticación. No se afirma que los workflows se hayan ejecutado
en GitHub. Las prioridades son una recomendación, no una aprobación de
despliegue: P1 prioriza protección y cierre del ciclo de mejora; P2 incorpora
operación institucional; P3 agrega reconocimiento y cultura.

### 2.3 Integración local de frontend, API y datos

La integración local usa dos servicios independientes:

- Backend FastAPI en `http://127.0.0.1:8000`.
- Frontend Next.js en `http://localhost:3000`.
- PostgreSQL y Redis locales iniciados con Docker Compose.

`NEXT_PUBLIC_API_BASE_URL` contiene únicamente el origen del backend, por ejemplo
`http://localhost:8000`, sin el prefijo `/api/v1`. Los clientes frontend deben
añadir explícitamente `/api/v1` a las rutas compartidas. Son rutas de referencia:
`GET /api/v1/health`, `GET /api/v1/auth/me`,
`GET /api/v1/encuestas/indicadores`, `POST /api/v1/asistente/chat` y los demás
contratos bajo `/api/v1`.

Las solicitudes protegidas deben incluir la cookie de sesión. Para navegación
desde otro equipo de la red local, el origen configurado debe apuntar a la IP LAN
del servidor y el origen exacto del navegador debe estar permitido en
`CORS_ALLOWED_ORIGINS`.

El despliegue compuesto debe iniciar API, frontend, PostgreSQL y Redis; el
frontend debe ejecutarse en modo standalone de Next.js como usuario no root y
`NEXT_PUBLIC_API_BASE_URL` debe ser la URL pública alcanzable desde el navegador,
sin incluir `/api/v1`.

### 2.4 Despliegue de demostración en Internet

La demostración desplegada usa AWS ECS Fargate en `us-east-2`: un servicio para
frontend, uno para la API, uno para Redis y uno para PostgreSQL, publicados
mediante un Application Load Balancer. PostgreSQL se ejecuta con almacenamiento
EFS cifrado y acceso privado, y la resolución interna usa AWS Cloud Map.

Para compartir temporalmente la aplicación con un enlace HTTPS sin adquirir un
dominio, un servicio ECS ejecuta Cloudflare Quick Tunnel sobre el balanceador. El
frontend detecta el contexto HTTPS y consume `/api/v1` desde el mismo origen
proporcionado por el túnel. El enlace `trycloudflare.com` es temporal y puede
cambiar si el túnel se reinicia; no constituye un dominio institucional.

Este despliegue de demostración no convierte el MVP en producción aprobada. No
implementa SSO/Keycloak. Existe una migración inicial de Alembic y scripts
manuales de respaldo/restauración local, pero el despliegue ECS no aplica
migraciones automáticamente y no se ha validado una restauración en AWS. La
configuración temporal debe ser reemplazada por HTTPS institucional, secretos
administrados, observabilidad y políticas operativas aprobadas.

## 3. Roles y autorización

Los permisos deben verificarse en el backend. Ocultar enlaces o controles en la
interfaz no constituye por sí solo un control de acceso.

| Rol | Capacidades autorizadas | Capacidades denegadas |
|---|---|---|
| `staff` (Personal) | Iniciar sesión; responder encuestas; enviar sugerencias y nominaciones; consultar planes publicados, organigrama, agenda, comunicaciones y reconocimientos propios/publicados. | Consultar indicadores y administrar módulos institucionales. |
| `supervisor` | Consultar indicadores; moderar sugerencias/reconocimientos; gestionar planes/eventos y preparar comunicaciones. | Responder encuestas, administrar cuentas/organigrama y consultar auditoría. |
| `admin` (Administrador) | Administrar cuentas, módulos institucionales y auditoría; consultar indicadores agregados que cumplan privacidad. | Responder encuestas. |

Una persona no autenticada puede acceder al flujo público de inicio de sesión y
al asistente general, que no tiene acceso a datos de HospitaPulse. Las cuentas
inactivas no pueden iniciar sesión. Si una cuenta debe cambiar su contraseña,
no puede continuar al resto de las funciones hasta completar el cambio.

## 4. Requisitos funcionales

### RF-01 — Inicio de sesión inicial

Al cargar la aplicación sin una sesión válida, el sistema debe presentar el
formulario de inicio de sesión antes de mostrar el menú y las funciones protegidas.
Después de autenticar, debe mostrar únicamente las opciones permitidas por el rol.

### RF-02 — Validación de credenciales

El backend debe autenticar mediante nombre de usuario y contraseña, verificar la
contraseña usando un hash seguro compatible con bcrypt y rechazar credenciales
incorrectas o cuentas inactivas con una respuesta de autenticación fallida que no
revele si el usuario existe.

### RF-03 — Sesión

Después de una autenticación válida, el backend debe emitir un JWT firmado y
transportarlo mediante una cookie de sesión HttpOnly con atributos seguros
configurados para el entorno. La sesión debe expirar de forma absoluta a los 10
minutos desde el login, incluso si hay actividad. El frontend debe enviar la
cookie en las solicitudes protegidas y cerrar la vista al vencer. El cierre de
sesión debe invalidar/eliminar la cookie del navegador.

### RF-04 — Cambio de contraseña temporal

Una cuenta marcada como obligada a cambiar su contraseña debe completar el cambio
antes de acceder a las funciones de su rol. La nueva contraseña debe cumplir las
validaciones de seguridad configuradas por el sistema. Tras el cambio, se debe
actualizar la sesión autenticada.

### RF-05 — Acceso a encuestas

Solo una cuenta autenticada con rol `staff` puede obtener la encuesta actual y
registrar respuestas. Las solicitudes de cuentas `admin`, `supervisor` o usuarios
no autenticados deben ser rechazadas por el backend.

### RF-06 — Registro anónimo de respuestas

El sistema debe almacenar las respuestas sin una referencia persistente al
identificador de la cuenta autenticada. La autenticación autoriza la operación,
pero no debe vincular la identidad del participante con las respuestas guardadas.

### RF-07 — Validación de respuestas

Cada respuesta debe referenciar una pregunta válida y contener un valor entero
estricto entre 1 y 5, inclusive. El contrato debe rechazar campos no declarados,
valores fuera de rango, tipos coercionados y envíos vacíos.

### RF-08 — Confirmación y navegación posterior

Al registrar correctamente las respuestas, el sistema debe confirmar el envío.
La persona debe poder volver al menú sin que la aplicación la redirija
automáticamente a la encuesta en cada navegación posterior.

### RF-09 — Cierre de sesión voluntario del personal

El personal autenticado puede cerrar sesión desde el menú principal o después
de responder, o mantenerla activa. Si cierra sesión después de responder, la
confirmación de envío debe seguir visible aunque la cookie se elimine.

### RF-10 — Indicadores

Solo `admin` y `supervisor` pueden consultar los indicadores. Cuando los datos
cumplan la regla de privacidad, la respuesta debe incluir el promedio general,
el promedio por dimensión y el total de respuestas.

### RF-11 — Regla de privacidad N ≥ 5

Los conteos y promedios solo se pueden divulgar si el tamaño de muestra del ámbito
consultado es de al menos cinco respuestas. Cuando `N < 5`, el resultado debe
marcarse como enmascarado y no debe incluir el total, el promedio general ni
promedios por dimensión.

### RF-12 — Administración de personal

Solo `admin` puede crear cuentas y asignarles un rol inicial. Una contraseña
temporal debe mostrarse una sola vez. El administrador puede restablecer la
contraseña de otra cuenta mediante una credencial temporal que se exige cambiar
al siguiente acceso. El administrador puede retirar el acceso desactivando la
cuenta; no se borran físicamente usuarios ni su historial. Las credenciales de
la cuenta administrativa inicial deben proceder de la configuración segura del
entorno, no de valores hardcodeados.

### RF-13 — Encuesta mensual

Al solicitar la encuesta actual, el sistema debe obtener o crear la encuesta del
mes correspondiente. La operación debe ser idempotente: solicitudes repetidas
durante el mismo mes no deben crear encuestas duplicadas.

### RF-14 — Caché de indicadores

El backend debe cachear los indicadores agregados por año y mes usando Redis,
con TTL configurable (60 segundos por defecto). Solo puede cachear el resultado
después de aplicar la regla de privacidad: agregados divulgables con **N ≥ 5**
o resultado enmascarado sin conteos ni promedios cuando **N < 5**. Al guardar
una nueva respuesta debe invalidar el periodo correspondiente. Si Redis no está
disponible, la consulta debe continuar desde PostgreSQL y mantener las mismas
reglas de privacidad.

### RF-15 — Prueba de carga local de indicadores

El proyecto debe incluir un escenario reproducible de k6 para consultar el
endpoint autorizado de indicadores con **50 usuarios virtuales durante 2
minutos**. El perfil inicial debe verificar una tasa de errores HTTP inferior
al 1 % y latencia p95 inferior a 500 ms. El escenario será de solo lectura y
debe rechazar cualquier destino que no sea `localhost` o `127.0.0.1`. Estos
umbrales son criterios iniciales de prueba, no una certificación de capacidad
de producción.

### RF-16 — Asistente de preguntas abiertas

La aplicación debe ofrecer un asistente capaz de responder preguntas abiertas
mediante Gemini. El frontend enviará solo la pregunta actual al backend; no se
enviarán historial, identidad, respuestas de encuestas ni indicadores. La clave
`GEMINI_API_KEY` se mantendrá en el backend. El modelo se configura con
`GEMINI_MODEL` y por defecto será `gemini-3.5-flash-lite`. Se informará que el
texto de la pregunta se procesa por Gemini y se pedirá no incluir información
personal o respuestas. Las preguntas no se persistirán en HospitaPulse. Si
falta la clave, se agota la cuota o no está disponible el modelo configurado,
la interfaz recibirá un error explícito y no mostrará una respuesta simulada.

### RF-17 — Buzón anónimo de sugerencias

Permitir al personal enviar sugerencias sin asociar la cuenta autenticada, IP,
servicio u otros identificadores persistentes al contenido. El remitente puede
seleccionar una categoría y escribir una propuesta; el sistema debe advertir que
no incluya datos personales ni información clínica. `admin` y `supervisor`
pueden clasificar, asignar estado y responder institucionalmente sin conocer la
identidad del remitente. La consulta pública no debe permitir deducir quién
envió una sugerencia. La confirmación será genérica y no prometerá seguimiento
individual.

### RF-18 — Planes de mejora

Permitir a `admin` y `supervisor` crear planes con objetivo, dimensión o tema,
responsable institucional, acciones, fechas, indicador de avance, estado y
resultado esperado. El personal puede consultar planes publicados. Los planes
pueden referenciar únicamente indicadores divulgables; no deben incluir
respuestas individuales, grupos con N < 5 ni inferencias obtenidas por comparar
cohortes pequeñas.

### RF-19 — Reconocimientos institucionales

Permitir nominaciones positivas voluntarias entre integrantes del personal,
con categoría, motivo y destinatario institucional. La publicación requiere
moderación y consentimiento explícito de la persona reconocida. No se permite
generar reconocimientos a partir de respuestas de encuestas ni publicar
información sensible. La persona nominada puede aceptar o rechazar aparecer en
la comunicación.

### RF-20 — Organigrama institucional

Mostrar a usuarios autenticados una estructura navegable de unidades, áreas,
servicios y relaciones jerárquicas. Solo `admin` puede crear, modificar o
desactivar nodos. Mostrar únicamente nombre institucional, cargo o rol laboral
y unidad que estén autorizados; no exponer datos personales de contacto ni
relacionar el organigrama con respuestas de encuestas.

### RF-21 — Actividades y eventos

Permitir a `admin` y `supervisor` publicar eventos con título, descripción,
fecha y hora, ubicación, audiencia y cupos cuando aplique. Usuarios autenticados
pueden consultar la agenda y registrar o cancelar voluntariamente su asistencia.
La asistencia se usa solo para la gestión del evento, no para medir clima ni
inferir participación en encuestas. La interfaz debe distinguir próximos,
pasados, cancelados y sin cupo.

### RF-22 — Comunicaciones institucionales

Permitir a `admin` redactar, previsualizar, programar, publicar, actualizar y
archivar anuncios con audiencia, prioridad y vigencia. `supervisor` puede
preparar borradores si un `admin` los aprueba. Usuarios autenticados consultan
comunicaciones vigentes y pueden marcar su lectura cuando se solicite. La
publicación debe mostrar autor institucional y fecha; no enviar mensajes
privados ni información sensible por este canal.

### RF-23 — Seguridad y auditoría

Permitir a `admin` consultar un registro de solo lectura de eventos relevantes:
accesos exitosos/fallidos, cierres de sesión, cambios de roles/estado de
cuentas, cambios administrativos y operaciones de publicación/moderación. Cada
evento incluirá fecha, actor cuando corresponda, acción, resultado y recurso
afectado. No registrar contraseñas, tokens, claves, contenido de encuestas,
respuestas individuales ni texto completo de sugerencias. Restringir exportación
y consulta, aplicar retención configurable y proteger el registro contra
modificación ordinaria.

### RF-24 — Experiencia profesional de Dashboard y analítica

Conservar Resumen e Indicadores como capacidades existentes y evolucionarlos
con navegación clara por periodo, tendencias, comparación de periodos, filtros
explicables y exportación autorizada. Toda desagregación y comparación debe
aplicar N ≥ 5 y controles complementarios que eviten inferencias por diferencias
entre grupos o periodos. Si la privacidad no puede garantizarse, ocultar la
comparación. Presentar estados consistentes de carga, error, ausencia de datos
y supresión de privacidad.

### RF-25 — Recuperación de acceso asistida

Los formularios de acceso deben ofrecer el enlace «¿Olvidaste tu contraseña?».
Mientras no exista correo institucional configurado, la página de recuperación
debe informar que la persona contacte a un administrador. El administrador
puede emitirle una contraseña temporal desde Usuarios y roles, que se muestra
una sola vez y debe cambiarse inmediatamente después del siguiente inicio de
sesión. No se debe fingir el envío de un correo ni revelar credenciales fuera
del flujo administrativo autorizado.

## 5. Contratos de datos y API

Los siguientes contratos describen el comportamiento esperado de esta iteración.
Los nombres de las rutas son relativos al prefijo de API configurado por el
backend.

### 5.1 Inicio de sesión

**Solicitud**

```json
{
  "username": "usuario",
  "password": "contraseña"
}
```

**Validación**

- `username`: cadena estricta, entre 1 y 64 caracteres.
- `password`: cadena estricta, entre 1 y 128 caracteres.
- No se aceptan campos adicionales.

**Respuesta de aplicación**

- `200 OK`: devuelve la identidad segura de la sesión (identificador, nombre de
  usuario, nombre completo, correo, rol, estado activo y si debe cambiar la
  contraseña); establece el JWT en una cookie HttpOnly.
- `401 Unauthorized`: credenciales inválidas o cuenta inactiva.
- `503 Service Unavailable`: autenticación no configurada.
- `422 Unprocessable Entity`: solicitud que no cumple el esquema.

**Compatibilidad con el contrato inicial solicitado:** el primer requerimiento
planteó devolver `access_token`, `token_type`, `rol` y `servicio_id` en el cuerpo.
El contrato aplicado en la iteración fue actualizado al uso de cookie HttpOnly y
respuesta de sesión segura; el token no se expone en el cuerpo JSON del login.

### 5.2 Cambio de contraseña

**Solicitud**

```json
{
  "password_actual": "contraseña-temporal",
  "password_nueva": "nueva-contraseña-segura"
}
```

- `password_actual`: cadena estricta, entre 1 y 128 caracteres.
- `password_nueva`: cadena estricta, al menos 12 caracteres y máximo 72 bytes
  UTF-8 para compatibilidad con bcrypt.
- La nueva contraseña debe ser diferente de la actual.
- Requiere una sesión válida.

### 5.3 Obtener encuesta actual

`GET /encuestas/actual`

- Requiere una sesión de `staff` que no esté obligada a cambiar contraseña.
- Devuelve metadatos de la encuesta mensual y sus preguntas.
- Si no existe la encuesta del mes, la obtiene o la crea de forma idempotente.

### 5.4 Registrar respuestas

`POST /encuestas/{encuesta_id}/respuestas`

**Solicitud**

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

- `respuestas`: lista no vacía.
- `pregunta_id`: cadena estricta no vacía.
- `valor`: entero estricto entre 1 y 5.
- No se aceptan campos adicionales.
- Requiere una sesión de `staff`.

**Respuestas esperadas**

- `201 Created`: respuestas aceptadas; acuse de recibo sin identidad del
  participante.
- `404 Not Found`: encuesta inexistente.
- `409 Conflict`: encuesta cerrada.
- `422 Unprocessable Entity`: contenido inválido o regla de dominio incumplida.
- `401 Unauthorized` o `403 Forbidden`: sesión ausente o rol no autorizado.

### 5.5 Consultar indicadores

`GET /encuestas/indicadores?anio={anio}&mes={mes}`

- Requiere el rol `admin` o `supervisor`.
- `anio`: entero entre 2000 y 2100.
- `mes`: entero entre 1 y 12.
- Si `N < 5`, `enmascarado` debe ser verdadero, y `total_respuestas`,
  `promedio_general` y `dimensiones` no deben revelar datos del grupo.
- Si `N ≥ 5`, se pueden devolver conteo, promedio general y promedio por
  dimensión.

### 5.6 Sesión y cierre de sesión

- `GET /auth/me`: devuelve la identidad asociada a la cookie válida.
- `POST /auth/logout`: elimina la cookie y devuelve `204 No Content`.
- `POST /auth/login`: establece una nueva sesión.
- `PATCH /auth/password`: cambia la contraseña autenticada y renueva la sesión.

## 6. Requisitos no funcionales y restricciones

### RNF-01 — Privacidad

La regla `N ≥ 5` es un control obligatorio. Debe aplicarse en el backend al
construir los resultados, no solo en la interfaz.

### RNF-02 — Anonimato

La entidad persistida de respuesta no debe guardar `usuario_id` ni una clave
alternativa que permita asociar directamente una respuesta a su participante.

### RNF-03 — Seguridad de credenciales

Las contraseñas no se almacenan en texto plano. Los secretos de firma JWT y las
credenciales iniciales se configuran mediante variables de entorno u otro
mecanismo seguro.

### RNF-04 — Separación de capas

Los casos de uso y el dominio no deben depender de FastAPI, SQLAlchemy ni de
detalles de presentación. La infraestructura implementa los puertos definidos
por la aplicación o el dominio.

### RNF-05 — Validación de entrada

Los DTO de entrada deben usar modelos Pydantic v2 estrictos, validar rangos y
rechazar propiedades no declaradas donde aplique.

### RNF-06 — Errores explícitos

Los errores de autenticación, autorización, validación y estado de encuesta deben
traducirse a respuestas HTTP apropiadas sin producir respuestas de éxito
alternativas ni revelar información sensible.

## 7. Escenarios de aceptación (Given/When/Then)

### AC-01 — Login previo al sitio

**Dado** que no existe una sesión válida, **cuando** una persona abre la
aplicación, **entonces** se muestra el formulario de inicio de sesión y no el
contenido protegido.

### AC-02 — Menú según rol

**Dado** que la autenticación fue correcta, **cuando** se carga el menú,
**entonces** solo se presentan las capacidades asociadas al rol de la sesión.

### AC-03 — Exclusión de roles en encuestas

**Dado** un usuario `admin` o `supervisor`, **cuando** solicita la encuesta o
registra respuestas, **entonces** el backend rechaza la operación.

### AC-04 — Participante autorizado

**Dado** un usuario `staff` activo, autenticado y sin cambio de contraseña
pendiente, **cuando** solicita la encuesta y envía respuestas válidas,
**entonces** la API devuelve un acuse de recibo y no persiste el identificador
del usuario junto a las respuestas.

### AC-05 — Validación Likert

**Dado** un envío con valor menor que 1, mayor que 5, no entero estricto o con
lista vacía, **cuando** se valida la solicitud, **entonces** se rechaza con
`422 Unprocessable Entity`.

### AC-06 — Protección de muestras pequeñas

**Dado** un ámbito con menos de cinco respuestas, **cuando** un rol autorizado
consulta los indicadores, **entonces** no se exponen conteos ni promedios.

### AC-07 — Publicación de agregados seguros

**Dado** un ámbito con cinco o más respuestas, **cuando** un rol autorizado
consulta los indicadores, **entonces** se exponen el promedio general, los
promedios por dimensión y el total de respuestas.

### AC-08 — Navegación después de responder

**Dado** que el usuario `staff` ya envió la encuesta, **cuando** vuelve al menú,
**entonces** permanece en el menú y no es redirigido automáticamente al
formulario de encuesta.

### AC-09 — Cierre voluntario

**Dado** que un usuario `staff`, `admin` o `supervisor` tiene una sesión activa,
**cuando** elige “Cerrar sesión” en la barra superior del menú, **entonces** se
elimina la sesión y se muestra el formulario de acceso. El personal también
puede cerrar sesión después de responder; si ya había respondido, se conserva la
confirmación de envío. Si no cierra sesión, puede seguir navegando autenticado.

### AC-10 — Cambio obligatorio de contraseña

**Dado** que la cuenta está marcada con cambio de contraseña pendiente,
**cuando** intenta acceder a una función protegida, **entonces** debe completar
el cambio antes de continuar.

### AC-11 — Idempotencia mensual

**Dado** que ya existe la encuesta del mes, **cuando** se solicita nuevamente la
encuesta actual, **entonces** se devuelve la existente y no se crea un duplicado.

### AC-12 — Caché y privacidad de indicadores

**Dado** que se consultan indicadores, **cuando** Redis contiene un resultado
seguro vigente, **entonces** puede devolverse el caché sin cambiar los permisos
ni la regla N ≥ 5. Solo se cachean agregados divulgables con N ≥ 5 o un
resultado enmascarado sin valores con N < 5.

### AC-13 — Invalidación y continuidad ante fallo de Redis

**Dado** que se registra una nueva respuesta, **cuando** se vuelven a consultar
los indicadores de ese periodo, **entonces** se invalida su entrada de caché. Si
Redis no está disponible, el backend consulta PostgreSQL y mantiene la supresión
de muestras pequeñas.

### AC-14 — Carga controlada en desarrollo

**Dado** que se ejecuta la prueba k6 en el entorno local, **cuando** el
escenario realiza solicitudes al endpoint de indicadores, **entonces** solo
acepta `localhost` o `127.0.0.1`, ejecuta 50 usuarios virtuales durante 2
minutos y comprueba error HTTP menor a 1 % y p95 menor a 500 ms. Estos umbrales
no certifican capacidad de producción.

### AC-15 — Respuesta abierta sin contexto interno

**Dado** que el asistente está configurado, **cuando** una persona envía una
pregunta abierta, **entonces** recibe una respuesta generada por Gemini y solo
se envía la pregunta actual, sin historial ni datos internos del hospital.

### AC-16 — Límites y errores del asistente

**Dado** que falta la clave, se envía una solicitud excesiva, se agota la cuota,
el modelo configurado no está disponible o falla el proveedor, **cuando** se
consulta el asistente, **entonces** se devuelve un error explícito `503`, `429`,
`503`, `503` o `502`, respectivamente, sin simular una respuesta exitosa.

### AC-17 — Navegación con módulos reales

**Dado** un usuario con un rol autenticado, **cuando** abre la navegación,
**entonces** solo ve enlaces autorizados a funciones disponibles, agrupados por
propósito, con el elemento activo identificado y sin opciones vacías o enlaces
rotos.

### AC-18 — Sugerencias anónimas

**Dado** que el personal envía una sugerencia, **cuando** se almacena y modera,
**entonces** no se conserva una relación entre el texto y su identidad, y solo
los roles autorizados pueden cambiar su estado.

### AC-19 — Planes de mejora protegidos

**Dado** un plan asociado a indicadores, **cuando** se crea o consulta,
**entonces** solo se permiten métricas divulgables con N ≥ 5 y únicamente roles
autorizados editan el plan.

### AC-20 — Reconocimiento con consentimiento

**Dado** que una nominación será publicada, **cuando** se modera,
**entonces** no aparece públicamente hasta contar con aprobación y consentimiento
explícito de la persona reconocida.

### AC-21 — Agenda y comunicaciones vigentes

**Dado** un usuario autenticado, **cuando** consulta eventos y anuncios,
**entonces** ve solo elementos publicados y vigentes para su audiencia, con
fecha, estado y acciones disponibles correctamente identificados.

### AC-22 — Auditoría sin datos sensibles

**Dado** un evento de seguridad o administración, **cuando** se registra y
consulta, **entonces** existe trazabilidad del actor y acción sin secretos,
respuestas individuales ni contenido confidencial, y solo un rol autorizado
puede consultar el registro.

### AC-23 — Analítica con privacidad

**Dado** un filtro o comparación que produzca un grupo menor de cinco o permita
inferirlo por diferencia, **cuando** se consulta la analítica, **entonces** se
suprime el resultado y no se exponen conteos ni promedios.

## 8. Especificaciones técnicas en formato de prompts de implementación

Los siguientes prompts representan instrucciones técnicas reutilizables para
implementar los requisitos de esta especificación. Son formulaciones
normalizadas, no transcripciones literales de los mensajes originales.

### Prompt A — Caso de uso de autenticación

> Implementa el caso de uso de autenticación del módulo `auth` en la capa de
> aplicación, siguiendo Clean Architecture. Define un comando de entrada con
> `username` y `password`, valida credenciales con bcrypt, rechaza cuentas
> inactivas, genera un JWT firmado mediante una dependencia inyectada y no
> expongas detalles que permitan enumerar usuarios. Usa tipos estrictos y DTO
> Pydantic v2 en los límites de entrada/salida. Mantén la persistencia, la
> generación criptográfica y la presentación detrás de puertos o adaptadores.
> Para el flujo integrado actual, entrega el JWT mediante cookie HttpOnly y
> devuelve únicamente los datos seguros de sesión.

### Prompt B — Caso de uso de respuesta anónima

> Implementa el flujo de registro de respuestas del módulo `encuestas` con
> separación estricta entre dominio, aplicación, infraestructura y presentación.
> Acepta una encuesta y una colección no vacía de respuestas Likert enteras de
> 1 a 5, valida que la encuesta esté abierta y que las preguntas correspondan a
> ella, y persiste las respuestas sin `usuario_id` ni vínculo recuperable con la
> identidad autenticada. La autenticación autoriza la operación, pero la
> identidad no forma parte del modelo persistido de respuesta. Traduce errores de
> dominio a respuestas HTTP explícitas y no agregues dependencias de FastAPI o
> SQLAlchemy al dominio/caso de uso.

### Prompt C — Indicadores con privacidad de muestra mínima

> Implementa la consulta de indicadores por periodo y ámbito para los roles
> `admin` y `supervisor`. Aplica en el backend una barrera de privacidad
> obligatoria: si el tamaño de muestra es menor que cinco, devuelve un resultado
> enmascarado sin total, promedio general ni promedios por dimensión. Solo con
> `N >= 5` calcula y devuelve el total de respuestas y los promedios agregados.
> Incluye pruebas para N=0, N=4, N=5 y N mayor que cinco; verifica tanto el
> contenido como la ausencia de información enmascarada.

### Prompt D — Autorización del flujo por roles

> Aplica autorización backend por rol para las rutas de HospitaPulse: `staff`
> puede acceder a encuestas y registrar respuestas; `supervisor` puede consultar
> únicamente indicadores; `admin` puede consultar indicadores y gestionar
> cuentas. `admin` y `supervisor` no pueden responder encuestas. Una sesión
> ausente, inválida, asociada a cuenta inactiva o con cambio de contraseña
> pendiente debe impedir el acceso según la política definida. Añade pruebas
> negativas por rol; no confíes exclusivamente en la ocultación de elementos de
> interfaz.

### Prompt E — Flujo de interfaz y sesión del personal

> Actualiza el frontend para mostrar el login como primera pantalla a usuarios
> no autenticados y construir el menú de acuerdo con el rol autenticado. Para el
> rol `staff`, permite volver al menú tras responder sin redirección automática
> repetida a la encuesta. Muestra cierre de sesión desde el menú y después del
> envío, permitiendo mantener la sesión activa si no se elige cerrar. Si se
> cierra tras responder, preserva en la interfaz la confirmación de envío aunque
> se limpie la cookie de sesión. Mantén los indicadores y la administración
> fuera del menú de `staff`.

### Prompt F — Administración de cuentas

> Implementa la creación de cuentas y asignación del rol inicial solo para
> `admin`. La contraseña temporal debe generarse de forma segura, mostrarse una
> sola vez y almacenarse únicamente como hash. Marca la cuenta para cambio
> obligatorio de contraseña en el primer acceso. Obtén las credenciales de la
> cuenta administrativa inicial desde configuración externa segura y nunca
> incluyas secretos en el código fuente.

### Prompt G — Encuesta mensual idempotente

> Implementa la obtención o creación de la encuesta mensual con una garantía de
> idempotencia. Ante solicitudes simultáneas o repetidas para el mismo periodo,
> debe existir como máximo una encuesta. Mantén la regla en la capa de
> aplicación/dominio y apóyala con una restricción de persistencia apropiada.

### Prompt H — Caché y prueba de carga

> Implementa la caché Redis de indicadores según `docs/spec-backend.md`:
> claves por año y mes, TTL predeterminado de 60 segundos configurable,
> invalidación al guardar una respuesta y fallback a PostgreSQL si Redis falla.
> Cachea solo agregados que cumplen N ≥ 5 o resultados enmascarados sin datos.
> Añade pruebas unitarias para TTL, cache hit, invalidación, fallback y
> privacidad. Crea un escenario k6 de solo lectura con 50 usuarios virtuales
> durante 2 minutos, limitado a localhost, con umbrales iniciales de error y
> p95; documenta que debe ejecutarse antes de reportar mediciones.

## 9. Trazabilidad de requisitos

| Requisito | Componentes principales | Evidencia esperada |
|---|---|---|
| RF-01 a RF-04 | `auth`, dependencias de autorización, frontend | Pruebas de login, cookie, roles y cambio de contraseña |
| RF-05 a RF-09 | `encuestas`, frontend de encuestas | Pruebas de permisos, validación, anonimato y navegación |
| RF-10 y RF-11 | `encuestas` / indicadores | Pruebas de umbral para N=4 y N=5 y autorización |
| RF-12 | `usuarios` / gestión de personal | Pruebas de rol administrador y contraseña temporal |
| RF-13 | `encuestas` / gestión mensual | Pruebas de idempotencia por periodo |
| RF-14 | Redis y módulo `encuestas` | Pruebas de caché, privacidad, invalidación y fallback |
| RF-15 | `tests/load/indicators.js` | Ejecución k6 local y reporte de error HTTP/p95 |
| RF-16 | `asistente`, configuración backend y chatbot frontend | Pruebas de contrato, privacidad y manejo de errores del proveedor |
| RF-17 | `institucional` / sugerencias | Pruebas de anonimato, moderación y autorización |
| RF-18 | `institucional` / planes de mejora | Pruebas de roles, estados, seguimiento y referencia segura a agregados |
| RF-19 | `institucional` / reconocimientos | Pruebas de moderación, consentimiento y revocación |
| RF-20 | `institucional` / organigrama | Pruebas de permisos, ciclos y visibilidad autorizada |
| RF-21 | `institucional` / eventos | Pruebas de publicación, audiencia, cupo y registro/cancelación |
| RF-22 | `institucional` / comunicaciones | Pruebas de aprobación, audiencia y vigencia |
| RF-23 | `institucional` / auditoría | Pruebas de acceso de solo lectura y ausencia de secretos/encuestas |
| RF-24 | `dashboard`, `reportes` e indicadores | Pruebas de comparaciones seguras, supresión complementaria y estados de interfaz |

## 10. Criterio de completitud SDD

La conformidad se evalúa por requisito, no por la sola presencia del requisito
en este documento. La implementación actual de los módulos institucionales es
un MVP y no se considera lista para producción hasta completar los requisitos
pendientes, pruebas, revisión de privacidad/seguridad, migraciones y aprobación
institucional.

1. Los requisitos del alcance implementado cuentan con contratos y controles en
   las capas correspondientes.
2. Los controles de autenticación y autorización se hacen en el backend.
3. Las pruebas demuestran los criterios de aceptación implementados,
   especialmente la diferencia entre `N=4` y `N=5`. Los criterios AC-17 a
   AC-23 requieren pruebas específicas adicionales antes de marcar como
   completa la implementación MVP de los módulos. Los resultados k6 se reportan
   solo después de ejecutar realmente la prueba.
4. No se divulgan datos de muestras menores que cinco, ni directa ni
   indirectamente mediante conteos, promedios o dimensiones.
5. El frontend conserva el comportamiento de login inicial, navegación por rol y
   cierre de sesión voluntario del personal.
6. La documentación de requisitos y la implementación distinguen claramente el
   flujo local de sesión de cualquier integración futura con SSO/Keycloak.
