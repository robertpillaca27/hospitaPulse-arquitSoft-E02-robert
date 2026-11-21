# Especificación SDD — Frontend de HospitaPulse

## 1. Propósito y alcance

Definir la experiencia de inicio de sesión, navegación por rol, respuesta de
encuestas, consulta de indicadores y gestión visual de sesión.

- **Tecnología:** Next.js.
- **Backend API:** FastAPI, accesible mediante la URL de API configurada para el
  entorno.
- El frontend aplica navegación y presentación por rol, pero no sustituye la
  autorización obligatoria del backend.

## Validación automatizada disponible

Vitest cubre las pruebas unitarias del frontend y TypeScript se valida con
`npm run typecheck`. Playwright está configurado para Chromium en viewport
móvil; comprueba la pantalla de login y el endpoint de salud, el acceso
administrativo a indicadores y el flujo de personal (cambio de contraseña
temporal y envío de encuesta) cuando se proporcionan credenciales E2E. La
suite se ejecutó localmente contra servicios aislados y sus tres casos pasaron.
El resultado JUnit está guardado en `docs/evidence/playwright-junit.xml`.
GitHub Actions está configurado para ejecutar estas pruebas junto con el build;
la ejecución del workflow debe verificarse en GitHub.

### Estado de implementación del menú

Están conectados Resumen, indicadores mensuales, encuestas, Personal y el
asistente Gemini. También están disponibles pantallas MVP para sugerencias,
planes, reconocimientos, organigrama, eventos, comunicaciones y consulta de
auditoría. La navegación se agrupa por área y adapta su presentación a móvil.
Las vistas institucionales cubren operaciones básicas; filtros avanzados,
calendarios, notificaciones, exportación, datos de producción y todos los
criterios de aceptación descritos en esta especificación aún requieren
validación o desarrollo adicional.

## 2. Requisitos funcionales

### FE-RF-01 — Login como punto de entrada

Cuando no existe una sesión válida, mostrar el formulario de inicio de sesión
antes del menú y de las pantallas protegidas.

### FE-RF-02 — Menú diferenciado por rol

- `staff`: mostrar navegación general y acceso a Encuestas; ocultar indicadores
  administrativos y gestión de cuentas.
- `supervisor`: mostrar acceso a indicadores; ocultar encuesta y administración.
- `admin`: mostrar indicadores y gestión de personal; ocultar respuesta de
  encuestas.

La ocultación es una regla de interfaz; el backend conserva la autoridad final.

### FE-RF-03 — Sesión y cookie

Enviar credenciales al endpoint de login y usar la cookie HttpOnly establecida
por la API en las solicitudes protegidas. El token no se debe guardar ni leer
desde JavaScript. Consultar la sesión actual para determinar identidad, rol y
estado de cambio obligatorio de contraseña.

En desarrollo, frontend y backend deben usar el mismo origen de red (`localhost`
o `127.0.0.1`) para evitar que la cookie se configure o consulte desde un host
distinto. `NEXT_PUBLIC_API_BASE_URL` debe incluir el puerto del backend y el
cliente debe construir el prefijo `/api/v1` una sola vez.

### FE-RF-04 — Cambio de contraseña requerido

Si la sesión indica `debe_cambiar_password`, llevar a la pantalla de cambio
obligatorio y no habilitar la navegación normal hasta que la API confirme el
cambio.

### FE-RF-05 — Flujo de Encuestas

El personal autenticado puede abrir la encuesta actual y enviar respuestas
Likert de 1 a 5. Tras el envío, mostrar confirmación y permitir volver al menú.
No redirigir automáticamente a Encuestas al navegar de vuelta al resumen.

### FE-RF-06 — Cierre de sesión voluntario

Mostrar a `staff`, `admin` y `supervisor` una opción de cierre de sesión en la
barra superior del menú principal. El personal también puede cerrar sesión
después de responder. Al cerrar, invocar logout y limpiar el estado local de
sesión, pero conservar la confirmación de envío de una respuesta ya registrada
en la interfaz.

### FE-RF-07 — Indicadores

Presentar a `admin` y `supervisor` los indicadores generales y por dimensión
devueltos por la API. Si el backend marca el resultado enmascarado, no mostrar
conteo ni promedios; presentar un mensaje que indique que el grupo no alcanza el
mínimo de privacidad. El frontend no debe intentar recalcular ni inferir los
datos suprimidos.

### FE-RF-08 — Gestión visual de personal

Mostrar la interfaz de gestión solamente a `admin`. Al crear una cuenta, mostrar
la contraseña temporal recibida de la API una sola vez y advertir que debe
guardarse en ese momento. Permitir restablecer la contraseña de otras cuentas y
mostrar la credencial temporal una sola vez, indicando que debe cambiarse al
ingresar. No permitir restablecer la contraseña de la propia sesión. La acción
de retiro debe decir «Desactivar» y explicar que conserva registros.

El administrador también debe disponer de una carga `.xlsx` que importe cuentas
de forma masiva. La interfaz debe mostrar el total procesado, creados, omitidos,
usuario y contraseña temporal de cada alta; las credenciales temporales se
presentan una sola vez. Debe aceptar las columnas Nombre, DNI, Teléfono,
Usuario, Email y Rol, documentar la derivación del usuario desde DNI y no
persistir ni mostrar el archivo como documento de personal.

### FE-RF-09 — Contexto de trabajo y fecha local

Mostrar el único espacio de trabajo configurado, Hospital Regional de Ayacucho,
sin presentar un selector de sedes mientras no existan alternativas disponibles.
El perfil del menú debe reflejar el nombre y rol de la sesión autenticada. La
fecha y hora del menú y la fecha del resumen deben actualizarse automáticamente
con la zona horaria `America/Lima`.

### FE-RF-10 — Acceso a información de privacidad

El aviso de privacidad del menú debe enlazar a la explicación de privacidad del
resumen. Ambos textos deben reflejar la regla vigente de muestra mínima N ≥ 5.

### FE-RF-11 — Asistente de preguntas abiertas

Mostrar un asistente de IA en las páginas de la aplicación que pueda responder
preguntas abiertas. Enviar al backend únicamente el texto de la pregunta actual,
sin el historial del chat ni contexto de usuarios, respuestas o indicadores.
El backend llama al proveedor configurado; el frontend nunca recibe ni almacena
su clave. El backend usa Gemini, con modelo configurable mediante `GEMINI_MODEL`;
el modelo predeterminado es `gemini-3.5-flash-lite`. Informar que el texto se
procesa con Gemini y que no se deben incluir datos personales ni respuestas de
encuestas. Mostrar explícitamente los errores de configuración, modelo no
disponible, cuota o proveedor.

### FE-RF-12 — Navegación institucional profesional

Organizar el menú en grupos con jerarquía clara: **Principal** (Dashboard,
Analítica institucional, Encuestas), **Participación y cultura** (Buzón de
sugerencias, Reconocimientos, Actividades y eventos, Comunicaciones),
**Gestión** (Planes de mejora, Organigrama institucional) y
**Administración** (Usuarios y roles, Seguridad y auditoría). Mostrar cada
opción según el rol y disponibilidad; la API aplica la autorización definitiva.
Indicar claramente la ruta activa, permitir navegación por teclado, mantener
etiquetas visibles junto a iconos, adaptar el menú a móvil y ofrecer estados
consistentes de carga, error y contenido vacío. No usar insignias o conteos que
revelen datos protegidos.

### FE-RF-13 — Buzón de sugerencias

Ofrecer un formulario sencillo con categoría, título opcional y detalle.
Advertir que el mensaje es anónimo, no permite seguimiento individual y no debe
incluir datos personales, clínicos o que identifiquen a participantes. Mostrar
una confirmación genérica. `admin` y `supervisor` disponen de una bandeja de
moderación con filtros y estados, sin información del remitente.

### FE-RF-14 — Planes de mejora

Mostrar a `admin` y `supervisor` una vista de planes con objetivo, dimensión
agregada, responsable institucional, tareas, fechas, estado y progreso. Permitir
crear, actualizar y cerrar planes según permisos. El personal puede consultar
solo planes publicados. No mostrar enlaces a datos de grupos con N < 5.

### FE-RF-15 — Reconocimientos

Permitir nominaciones positivas voluntarias con destinatario, categoría y
motivo. Mostrar el estado de moderación. No presentar una nominación al resto
de la institución hasta su aprobación y el consentimiento de la persona
reconocida; ofrecer una acción para retirar consentimiento.

### FE-RF-16 — Organigrama institucional

Mostrar una vista jerárquica navegable y adaptable a móvil por unidad, área y
servicio. Permitir búsqueda por estructura y cargo. Solo `admin` puede mantener
los nodos; ocultar datos personales de contacto no autorizados y no asociar
personas a respuestas o resultados de encuesta.

### FE-RF-17 — Actividades y eventos

Ofrecer agenda de próximos eventos con filtros por fecha y categoría, detalle de
ubicación/horario/audiencia y estados de cupo. Permitir confirmar o cancelar
asistencia a usuarios autenticados cuando el evento lo habilite. `admin` y
`supervisor` pueden gestionar eventos según permisos.

### FE-RF-18 — Comunicaciones institucionales

Mostrar anuncios vigentes por audiencia, prioridad y fecha. Para `admin`,
ofrecer redacción, vista previa, programación, publicación, edición y archivo;
`supervisor` puede preparar borradores sujetos a aprobación. Mostrar autor
institucional y vigencia. Si un anuncio requiere confirmación de lectura,
presentar su estado sin revelar información innecesaria.

### FE-RF-19 — Seguridad y auditoría

Mostrar a `admin` una pantalla de consulta de eventos con filtros por fecha,
tipo, actor, resultado y recurso. El detalle debe excluir secretos, respuestas
individuales y texto confidencial. El MVP permite filtrar fecha, acción,
resultado y actor; no ofrece exportación. La interfaz será de solo lectura y
limitará exportaciones a permisos explícitos.

### FE-RF-20 — Evolución del dashboard y analítica

Conservar los indicadores existentes por periodo y dimensión. Incorporar
tendencias, comparaciones y exportaciones solo cuando el backend confirme que
los filtros cumplen N ≥ 5 y controles contra inferencias entre grupos o
periodos. Para vistas con supresión, mostrar un mensaje comprensible sin
conteos, valores parciales ni gráficas residuales.

### FE-RF-21 — Expiración de sesión y recuperación de contraseña

Cerrar la sesión visible y volver al acceso al cumplirse 10 minutos desde el
login, aunque exista actividad. Ofrecer «¿Olvidaste tu contraseña?» en los
formularios de acceso principales; mostrar que la recuperación por correo no
está disponible y dirigir a contactar al administrador. La experiencia no debe
afirmar que se envió un correo.

### Estado y límites del MVP institucional

- **Sugerencias:** envío y moderación disponibles; no hay búsqueda ni filtros
  en la bandeja y el autor no puede consultar seguimiento individual.
- **Planes:** creación, consulta, progreso y estado disponibles; no se incluyen
  tareas con fechas individuales ni asociación a un resultado analítico.
- **Reconocimientos:** nominación, moderación y aceptación/retiro de
  consentimiento disponibles; el nominador no tiene una bandeja de seguimiento.
- **Organigrama:** estructura jerárquica y búsqueda por unidad/cargo disponibles;
  no se ha agregado información de contacto de personas.
- **Eventos:** creación, publicación, edición básica, cancelación y RSVP con
  control de cupo disponibles; faltan filtros por categoría y una vista de
  calendario.
- **Comunicaciones:** borrador, audiencia, vigencia, publicación y archivo
  disponibles; faltan vista previa, autor visible en la UI, confirmaciones de
  lectura y un flujo de programación dedicado.
- **Auditoría:** consulta de solo lectura y filtros disponibles; no registra
  todos los eventos de autenticación ni ofrece exportación.

Estos límites no anulan los requisitos de evolución enumerados en FE-RF-13 a
FE-RF-20. El MVP no debe presentarse como una implementación integral ni como
aprobación para procesar información institucional real.

### FE-RNF-01 — Calidad visual y accesibilidad

Las pantallas nuevas deben usar el sistema visual común del producto, jerarquía
tipográfica consistente, espaciado uniforme, contraste legible, foco visible,
etiquetas accesibles y diseños adaptables a móvil/escritorio. Cada flujo debe
tener estados de carga, éxito, error, vacío y confirmación de acciones
destructivas; no debe simular datos de producción.

## 3. Integración de API esperada

`NEXT_PUBLIC_API_BASE_URL` debe contener solo el origen del backend, sin
`/api/v1`. Por ejemplo: `http://127.0.0.1:8000`. Cada módulo HTTP debe agregar
explícitamente el prefijo completo de API a sus paths; por ejemplo:
`/api/v1/health`, `/api/v1/auth/me`, `/api/v1/encuestas/actual`,
`/api/v1/encuestas/indicadores` y `/api/v1/asistente/chat`.

Esta separación evita componer accidentalmente `/api/v1/api/v1/...` y permite
que el mismo origen sea usado por autenticación, encuestas, indicadores,
asistente y módulos institucionales. El cliente debe leer la configuración desde
`frontend/.env.local` o `.env.example`, nunca desde credenciales o secretos
versionados.

El despliegue en contenedores debe construir Next.js en modo `standalone`,
ejecutar el servidor como usuario no root y exponer el puerto 3000. Para
configuraciones antiguas que todavía incluyan `/api/v1` en
`NEXT_PUBLIC_API_BASE_URL`, el cliente debe normalizar el valor para evitar
duplicar el prefijo. Las variables públicas se incorporan en el build; ECS y
otros orquestadores deben pasar el origen alcanzable por el navegador como
argumento `NEXT_PUBLIC_API_BASE_URL` al construir la imagen.

El frontend debe integrarse, como mínimo, con estos contratos:

- `POST /auth/login`: autenticación y creación de cookie.
- `GET /auth/me`: sesión e identidad actuales.
- `POST /auth/logout`: cierre de sesión.
- `PATCH /auth/password`: cambio de contraseña.
- `GET /encuestas/actual`: encuesta mensual del usuario `staff`.
- `POST /encuestas/{encuesta_id}/respuestas`: envío anónimo.
- `GET /encuestas/indicadores?anio={anio}&mes={mes}`: indicadores de
  `admin`/`supervisor`.
- `POST /asistente/chat`: responde preguntas abiertas; se envía únicamente la
  pregunta actual.
- `/institucional/sugerencias`, `/institucional/planes-mejora`,
  `/institucional/reconocimientos`, `/institucional/organigrama`,
  `/institucional/eventos`, `/institucional/comunicaciones` y
  `/institucional/auditoria`: lectura y operaciones MVP según los permisos
  descritos en `spec-backend.md`.

Las peticiones que dependan de cookie deben configurarse para incluir
credenciales según el cliente HTTP usado y las políticas de origen/CORS.

## 4. Estados de interfaz

1. **Sin sesión:** formulario de login.
2. **Autenticando:** indicar progreso y evitar envíos duplicados.
3. **Sesión activa con cambio pendiente:** pantalla de cambio de contraseña.
4. **Sesión activa normal:** menú limitado por rol.
5. **Encuesta cargando/disponible/enviando:** mostrar estado y errores de API sin
   perder respuestas capturadas de forma accidental.
6. **Respuesta enviada:** mostrar confirmación y acción de volver al menú.
7. **Respuesta enviada y sesión cerrada:** mostrar confirmación persistente junto
   al formulario de login.
8. **Indicadores enmascarados:** mostrar aviso de muestra insuficiente sin
   valores ni visualizaciones que permitan inferirlos.

## 5. Criterios de aceptación del frontend

| ID | Dado | Cuando | Entonces |
|---|---|---|---|
| FE-AC-01 | Usuario sin sesión | Abre la aplicación | Ve login antes del menú. |
| FE-AC-02 | Usuario `staff` autenticado | Abre el menú | Ve Encuestas y no ve indicadores ni gestión de cuentas. |
| FE-AC-03 | Usuario `supervisor` autenticado | Abre el menú | Ve indicadores y no ve encuesta ni administración. |
| FE-AC-04 | Usuario `admin` autenticado | Abre el menú | Ve indicadores y gestión; no ve la opción de responder encuesta. |
| FE-AC-05 | `staff` envía una respuesta válida | La API confirma el envío | Ve confirmación y puede volver al menú sin redirección automática. |
| FE-AC-06 | Usuario `staff`, `admin` o `supervisor` autenticado en el menú | Selecciona “Cerrar sesión” en la barra superior | Se llama al endpoint logout y se muestra el formulario de acceso. |
| FE-AC-07 | `staff` termina de responder | Elige mantener sesión | Continúa autenticado y puede navegar. |
| FE-AC-08 | `staff` termina de responder | Elige cerrar sesión | Se limpia la sesión y la confirmación de envío permanece visible. |
| FE-AC-09 | API devuelve indicadores enmascarados | Se renderiza la vista | No se muestran conteos, promedios ni gráficas derivadas. |
| FE-AC-10 | Sesión indica cambio requerido | Se carga la app | Se exige cambiar contraseña antes de mostrar funciones normales. |
| FE-AC-11 | API rechaza una operación protegida | Se procesa la respuesta | Se informa el error y no se presenta la operación como exitosa. |
| FE-AC-12 | Usuario autenticado abre el menú | Se renderiza el contexto de sesión | Ve su nombre y rol, junto al único espacio de trabajo disponible. |
| FE-AC-13 | El tiempo transcurre o cambia el día | Se actualiza el menú | La hora, fecha y día se muestran automáticamente en zona `America/Lima`. |
| FE-AC-14 | Usuario pulsa el enlace de privacidad | Se activa el enlace | La vista desplaza a la explicación de privacidad con la regla N ≥ 5. |
| FE-AC-15 | Usuario abre el asistente | Envía una pregunta abierta | Recibe una respuesta generada por el proveedor configurado; solo se transmite la pregunta actual. |
| FE-AC-16 | Usuario consulta asuntos internos o de privacidad | El asistente responde | No consulta ni revela respuestas individuales, cuentas o indicadores internos; comunica sus límites de conocimiento. |
| FE-AC-17 | El asistente no está configurado o falla el proveedor | Usuario envía una pregunta | Se muestra un error claro; no se presenta una respuesta vacía como exitosa. |
| FE-AC-18 | Usuario con un rol autenticado | Abre la navegación | Ve los grupos ordenados, su ruta activa y solo enlaces disponibles y autorizados; los enlaces funcionan con teclado y en móvil. |
| FE-AC-19 | `staff` envía una sugerencia | Se registra la propuesta | Recibe confirmación genérica y no se muestran datos de identidad o seguimiento individual. |
| FE-AC-20 | `admin` o `supervisor` modera sugerencias | Actualiza categoría o estado | La bandeja no revela ni permite inferir quién envió cada mensaje. |
| FE-AC-21 | `admin`/`supervisor` crea un plan o `staff` consulta planes | Se renderiza la vista | Se aplican permisos; resultados bajo N < 5 no se vinculan ni muestran. |
| FE-AC-22 | Una nominación aún no cuenta con consentimiento | Se consulta la lista institucional | No se publica el reconocimiento ni el nombre de la persona nominada. |
| FE-AC-23 | Usuario abre el organigrama | Busca un área o cargo | Ve la estructura autorizada sin información personal de contacto no permitida. |
| FE-AC-24 | Usuario autenticado abre la agenda | Consulta próximos eventos | Ve eventos vigentes para su audiencia y puede confirmar o cancelar asistencia cuando esté habilitado. |
| FE-AC-25 | Usuario abre comunicaciones | Consulta anuncios | Ve solo anuncios publicados y vigentes; las acciones de edición respetan rol. |
| FE-AC-26 | Usuario sin permiso intenta abrir auditoría | Accede a la ruta o enlace | No obtiene los registros; un administrador ve filtros pero no secretos ni respuestas individuales. |
| FE-AC-27 | Un filtro analítico no cumple privacidad | Se carga la visualización | Se suprime el resultado sin valores parciales ni componentes visuales que permitan inferirlo. |
| FE-AC-28 | Se muestra cualquier pantalla de módulo | Cambia tamaño o navega con teclado | El contenido conserva legibilidad, foco visible y estados de carga/error/éxito coherentes. |
| FE-AC-29 | Administrador abre Usuarios y roles | Revisa la lista de cuentas | Encuentra acciones para activar/desactivar y restablecer contraseña de otras cuentas; desactivar comunica que conserva los registros. |
| FE-AC-30 | Administrador restablece una contraseña | La API confirma la operación | Se muestra la nueva contraseña temporal solo en la respuesta actual y se informa que debe cambiarse al ingresar. |
| FE-AC-31 | Usuario abre cualquier formulario principal de acceso | Selecciona «¿Olvidaste tu contraseña?» | Llega a la página que informa el proceso asistido por administrador sin simular correo. |
| FE-AC-32 | Han transcurrido 10 minutos desde el login | El usuario sigue usando la aplicación o vuelve a la pestaña | Se limpia el estado visual de sesión y se muestra el acceso; la actividad no renueva el límite. |
| FE-AC-33 | El frontend inicia con el origen configurado | Construye una llamada a autenticación, salud o indicadores | La URL final incluye exactamente un prefijo `/api/v1`; no se genera `/api/v1/api/v1/...`. |
| FE-AC-34 | La API responde `401` al consultar sesión sin autenticar | El usuario no tiene cookie válida | La interfaz muestra el formulario de inicio de sesión y no presenta una página de error como «Not Found». |
| FE-AC-35 | Frontend en `127.0.0.1:3000` consulta el backend | La cookie de sesión no existe o expiró | El cliente usa el mismo origen `127.0.0.1:8000`, recibe `401` controlado y cambia inmediatamente el estado de Encuestas a acceso de inicio de sesión, sin permanecer cargando. |
| FE-AC-36 | La aplicación se abre por HTTPS de un túnel Cloudflare | Se autentica un usuario y se consultan módulos protegidos | Frontend y `/api/v1` usan el mismo origen HTTPS; no hay contenido mixto ni error CORS, y la cookie HttpOnly se envía con `credentials: include`. |
| FE-AC-37 | Se reinicia el servicio temporal de Cloudflare | Vuelve a obtenerse la URL del túnel | Se documenta que `trycloudflare.com` puede cambiar; los clientes reciben la nueva dirección sin presentarla como dominio permanente. |
| FE-AC-36 | Administrador sube un Excel válido | Se importa el personal | Se crean cuentas nuevas en la base desplegada, se muestra el usuario y contraseña temporal una sola vez y se informan filas creadas u omitidas. |

## 6. Prompt técnico de implementación — Frontend

> Actualiza el frontend Next.js de HospitaPulse para presentar el login como
> primera pantalla a usuarios sin sesión y construir el menú según el rol
> retornado por la API. Usa la cookie HttpOnly del backend mediante solicitudes
> con credenciales; no almacenes JWT en localStorage ni lo expongas a JavaScript.
> Para `staff`, habilita Encuestas, la navegación de regreso al menú y una opción
> de cierre de sesión disponible en la barra superior del menú y tras responder.
> Para `admin` y `supervisor`, ofrece el cierre de sesión en esa misma barra
> superior. Permite mantener la sesión activa si no se elige cerrar y conserva la
> confirmación de envío si el personal cierra sesión. Muestra indicadores según
> permisos y gestión de cuentas solo a `admin`.
> Si los indicadores llegan enmascarados por N<5, no renders conteos, promedios
> ni gráficas derivadas. Respeta los estados de carga, error y cambio obligatorio
> de contraseña. Mantén un solo espacio de trabajo (Hospital Regional de
> Ayacucho) mientras no haya otras sedes configuradas; no simules un selector.
> Muestra el nombre y rol de la sesión en el perfil y actualiza fecha/hora según
> `America/Lima`. El enlace del aviso de privacidad debe llevar a la explicación
> de la regla N ≥ 5. Incluye un asistente de preguntas abiertas con proveedor
> configurado desde el backend. Envía solo la pregunta actual; no expongas la
> clave al frontend ni compartas historial, cuentas, respuestas o indicadores.
> Advierte que el texto se procesa con Gemini y no persistas los mensajes.
### Conexión API detrás de HTTPS temporal

Cuando la aplicación se abre mediante HTTPS (por ejemplo, un túnel temporal de
Cloudflare), el frontend debe consumir `/api/v1` sobre el mismo origen. Esto
evita contenido mixto, errores CORS y dependencias del host HTTP interno usado
durante la publicación. En desarrollo HTTP se conserva
`NEXT_PUBLIC_API_BASE_URL` como origen explícito de la API.

Cloudflare Quick Tunnel se considera únicamente un mecanismo de acceso temporal:
la URL termina en `trycloudflare.com`, puede cambiar al reiniciar el contenedor y
no debe registrarse como dominio institucional. Antes de distribuir una URL,
deben verificarse la página principal, `/api/v1/health`, el formulario de acceso
y la consulta de indicadores autorizada desde navegador móvil.

El login visible continúa siendo autenticación local de HospitaPulse. El frontend
no integra una redirección OIDC ni un inicio de sesión corporativo; SSO/Keycloak
sigue pendiente aunque algunos documentos arquitectónicos originales lo
mencionen.
