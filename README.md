## Sistema de Gestión del Clima Organizacional e Institucional del Hospital Regional
 ## nombre
 Robert Pillaca Choquehuanca
## Descripción
Plataforma de analítica y gestión institucional orientada a medir, procesar y mitigar el desgaste emocional o burnout y el clima organizacional en el hospital regional. El módulo de encuestas aplica anonimización y supresión de agregados con N < 5; el sistema requiere validación institucional antes de procesar datos reales. La integración con SIGA, INFORHUS y autenticación Keycloak se mantiene como evolución futura.
 ## Caso de estudio
Sistemas de evaluación de clima organizacional y tableros analíticos institucionales del sector salud como referencia funcional.
 ## Curso
 Arquitectura de Software

 ## Inicio rápido: integración frontend/backend

 El repositorio incluye una API FastAPI y un frontend Next.js con autenticación,
 encuestas e indicadores, asistente Gemini y pantallas MVP para los módulos
 institucionales de sugerencias, planes, reconocimientos, organigrama, eventos,
 comunicaciones y auditoría. FastAPI expone `GET /api/v1/health`; los contratos
 disponibles se documentan en `docs/spec-backend.md`.

 ### Backend

 ```bash
 python3 -m venv .venv
 source .venv/bin/activate
 python -m pip install -r requirements.txt
 cp .env.example .env
 uvicorn app.main:app --app-dir src --reload
 ```

 La API estará en `http://localhost:8000` y OpenAPI en
 `http://localhost:8000/openapi.json`. CORS local permite por defecto
 `http://localhost:3000` y `http://127.0.0.1:3000`; cambiar los orígenes mediante
 `CORS_ALLOWED_ORIGINS` separados por comas.

 ### Frontend

 ```bash
 cd frontend
 npm install
 cp .env.example .env.local
 npm run dev
 ```

 Next.js estará en `http://localhost:3000` y consultará
 `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`. La pantalla mostrará
 si el endpoint de salud respondió o si hubo un error de conexión.

 ### Acceso desde otro dispositivo de la red local

 Si abres el frontend desde otro equipo o teléfono, `localhost` apunta a ese
 dispositivo y no a la computadora donde se ejecuta HospitaPulse. Configura
 `frontend/.env.local` con la IP LAN de la computadora, por ejemplo:

 ```env
 NEXT_PUBLIC_API_BASE_URL=http://192.168.100.22:8000
 ```

 Incluye el origen exacto del navegador en `CORS_ALLOWED_ORIGINS` del `.env` raíz:

 ```env
 CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://192.168.100.22:3000
 ```

 Reinicia los dos servidores, haciendo que escuchen en interfaces de red:

 ```bash
 # Terminal backend (raíz del repositorio)
 source .venv/bin/activate
 uvicorn app.main:app --app-dir src --reload --host 0.0.0.0 --port 8000

 # Terminal frontend (raíz del repositorio)
 npm --prefix frontend run dev -- --hostname 0.0.0.0
 ```

 El puerto 8000 debe ser accesible desde la red local. Usa solo una red de
 confianza; no expongas el servidor de desarrollo directamente a Internet.

  ### Despliegue local con Docker Compose

  ```bash
  docker compose up -d --build api frontend db redis
  docker compose ps
  ```

  El despliegue local publica el frontend en `http://127.0.0.1:3000` y la API en
  `http://127.0.0.1:8000`. El frontend se construye con Next.js en modo
  `standalone` y se ejecuta como usuario no root. Compose conecta PostgreSQL y Redis
  mediante los nombres internos `db` y `redis`; no debe usar `localhost` para esos
  servicios dentro de la red de contenedores.

 ### Encuestas y PostgreSQL

 El menú **Encuestas** solicita inicio de sesión con una cuenta de rol
 `staff` (**Personal**) para abrir y responder la encuesta mensual activa.
 Las cuentas `admin` y `supervisor` no pueden responder encuestas; usan sus
 menús de gestión e indicadores. Una cuenta de personal activa puede responder; una
 contraseña temporal debe cambiarse antes de continuar. La identidad de la sesión
 solo autoriza el acceso y nunca se asocia a la respuesta guardada. El backend crea una
 encuesta de pulso con preguntas Likert (1–5) cuando inicia el mes o cuando se
 solicita la encuesta actual, y la restricción única por periodo evita duplicados.
 PostgreSQL local se inicia con Docker Compose. Copia `.env.example` a `.env`,
 asigna una contraseña local en `POSTGRES_PASSWORD` y actualiza `DATABASE_URL`
 con el mismo usuario y contraseña:

 ```env
 POSTGRES_DB=hospitapulse
 POSTGRES_USER=hospitapulse
 POSTGRES_PASSWORD=tu-clave-local
 DATABASE_URL=postgresql+psycopg://hospitapulse:tu-clave-local@localhost:5432/hospitapulse
 ```

 Inicia PostgreSQL y Redis (ambos puertos quedan enlazados solo a localhost):

 ```bash
 docker compose up -d db redis
 docker compose ps
 ```

 Redis se usa exclusivamente como caché de indicadores agregados. Su TTL local
 predeterminado es 60 segundos (`REDIS_INDICATORS_TTL_SECONDS`); al registrar una
 respuesta se invalida la clave del periodo. Si Redis no está disponible, el
 backend registra una advertencia y obtiene los indicadores directamente de
 PostgreSQL. El caché no almacena respuestas individuales ni identidades.

 Con `.env` configurado, inicia/reinicia el backend. Al iniciar, crea las tablas
 de los modelos cargados por la API que falten y asegura la encuesta del mes.
 El repositorio incluye una migración inicial de Alembic. Para aplicarla
 explícitamente en un entorno local, ejecuta `alembic upgrade head` desde la
 raíz con las dependencias instaladas. La aplicación todavía usa `create_all`
 al arrancar; las migraciones controladas en despliegues AWS siguen pendientes.
 Si no se configura la
 base de datos, el chequeo de salud seguirá disponible y la página Encuestas
 indicará cómo habilitar PostgreSQL. Los datos se conservan en el volumen
 `hospitapulse-postgres-data`; para detener la base sin borrar los datos usa
 `docker compose stop db`.
 Las respuestas guardan únicamente los valores Likert y la encuesta; no guardan
 usuario, DNI ni servicio. El endpoint `GET /api/v1/encuestas/indicadores?anio=2026&mes=11`
 devuelve los promedios por dimensión y el promedio general solo cuando hay al
 menos cinco respuestas en el periodo; por debajo de ese umbral enmascara todos
 los valores y no revela el conteo. El dashboard permite elegir entre los últimos
 doce periodos. Como el sistema no identifica participantes, el conteo representa
 envíos recibidos y no personas únicas verificadas.

### Migraciones, respaldos y pruebas

La migración inicial está en `migrations/versions/`. Los scripts
`scripts/db-backup.sh` y `scripts/db-restore.sh` permiten crear y restaurar
respaldos locales en formato PostgreSQL custom:

```bash
sh scripts/db-backup.sh
CONFIRM_RESTORE=yes sh scripts/db-restore.sh backups/archivo.dump
```

La restauración reemplaza objetos/datos existentes; úsala solo contra el
entorno correcto y después de verificar el archivo. Estos scripts no programan
respaldos ni configuran copias en AWS.

Las pruebas de backend y frontend, el chequeo de tipos y un flujo E2E de
Playwright están configurados en GitHub Actions. Para ejecutar las pruebas
backend localmente ejecuta `pip install -r requirements-dev.txt` y luego
`pytest -q`. En frontend:

```bash
cd frontend
npm ci
npm run typecheck
npm run build
npm test
npx playwright install chromium
npm run test:e2e
```

El E2E necesita los servicios locales disponibles. La configuración de CI/CD
para AWS está desactivada por defecto y requiere configurar explícitamente el
rol OIDC y la variable `ENABLE_AWS_DEPLOY`; el workflow de despliegue no se ha
ejecutado desde este cambio. La última prueba local de carga usó 50 VUs por 2
minutos, obtuvo 0 % de errores HTTP y p95 de 182.64 ms; consulta
[`docs/evidence/k6-indicators-output.txt`](docs/evidence/k6-indicators-output.txt).

### Acceso temporal por Cloudflare

La demostración desplegada en AWS puede compartirse mediante un Cloudflare Quick
Tunnel HTTPS. El túnel se ejecuta como un servicio ECS separado y reenvía tráfico
al Application Load Balancer, que dirige `/api/v1` al backend y el resto de rutas
al frontend. Esta configuración no requiere comprar un dominio.

La dirección activa cambia al reiniciar o sustituir la tarea de `cloudflared`;
antes de compartirla debe consultarse el log del grupo
`/ecs/hospitapulse-cloudflare`. La URL termina en `trycloudflare.com` y es
apropiada solo para una demostración temporal. Para producción debe configurarse
un dominio institucional, un túnel autenticado, HTTPS estable, secretos
administrados, monitoreo y respaldo.

La infraestructura AWS actual usa ECS Fargate, ECR, Application Load Balancer,
Cloud Map y EFS cifrado para PostgreSQL. EFS reemplaza el almacenamiento efímero
de la tarea; los datos se verificaron después de reiniciar PostgreSQL y la API.
La cookie de sesión sigue siendo una cookie HttpOnly con JWT firmado localmente.
**SSO/Keycloak no está implementado** en esta versión.

El guion de la presentación final está en
[`docs/presentacion-final.md`](docs/presentacion-final.md).
El plan de escalabilidad, límites de costo y operación está en
[`docs/escalabilidad-y-operacion.md`](docs/escalabilidad-y-operacion.md).

 El asistente de preguntas abiertas usa Gemini desde el backend. Para habilitarlo,
 crea una clave en Google AI Studio y agrega `GEMINI_API_KEY` a `.env`. De forma
 opcional, selecciona el modelo con `GEMINI_MODEL` (por defecto
 `gemini-3.5-flash-lite`). Reinicia el backend después del cambio. La clave no debe
 incluirse en el frontend, el repositorio ni los logs.
 El texto de cada pregunta se transmite a Gemini; el asistente no recibe historial
 de conversación, cuentas, respuestas de encuestas ni indicadores. Las solicitudes
 están limitadas a 12 por minuto por cliente en cada proceso del backend. Esta
 limitación local no sustituye un control compartido de cuotas para despliegues
 con varias instancias. El uso de la API puede generar cargos según el modelo y
 volumen de uso. Revisa los límites, precios, condiciones y políticas de datos
 del proveedor antes de configurarlo; no uses preguntas con información
 institucional sensible.

 ### Pruebas de carga locales

 Las pruebas usan k6 para consultar repetidamente los indicadores con una cuenta
 autorizada. El script es de solo lectura y rechaza destinos distintos de
 `localhost` o `127.0.0.1`; no lo ejecutes contra producción. En macOS puedes
 instalar k6 con `brew install k6`. Define credenciales de una cuenta local de
 administrador o supervisor en el entorno:

 ```bash
 read -r -p "Usuario local autorizado: " LOAD_TEST_USERNAME
 read -r -s -p "Contraseña: " LOAD_TEST_PASSWORD
 printf '\n'
 export LOAD_TEST_USERNAME LOAD_TEST_PASSWORD
 k6 run tests/load/indicators.js
 unset LOAD_TEST_PASSWORD
 ```

 El perfil predeterminado ejecuta 50 usuarios virtuales durante 2 minutos y
 verifica menos de 1 % de errores HTTP y latencia p95 inferior a 500 ms. El año
 y mes por defecto son los actuales; se pueden seleccionar con
 `LOAD_TEST_YEAR` y `LOAD_TEST_MONTH`. Los umbrales son criterios iniciales de
 prueba, no una garantía de capacidad de producción.

 ### Personal y autorizaciones

 Al abrir la aplicación se solicita iniciar sesión antes de mostrar el menú.
 Después del acceso, el rol `staff` ve las opciones generales, Encuestas y los
 módulos de participación disponibles; `admin` y `supervisor` ven los
 indicadores y opciones autorizadas para cada rol. Las cuentas
 temporales deben cambiar su contraseña antes de continuar.

 El menú **Personal** requiere una sesión de administrador. Configura
 `JWT_SECRET` (al menos 32 caracteres), `ADMIN_USERNAME` y `ADMIN_PASSWORD`
 (12–72 bytes UTF-8) en el `.env` local antes de reiniciar el backend. Al
 arrancar, se crea el administrador inicial si aún no existe. Entra en
 `http://localhost:3000/personal` con esas credenciales.

 El administrador puede crear cuentas (la contraseña temporal se muestra una
 sola vez), cambiar roles y activar/desactivar accesos. Las cuentas nuevas
 deben cambiar su contraseña al ingresar. Roles disponibles: `admin`
 (gestiona accesos y consulta indicadores), `supervisor` (consulta indicadores
 agregados) y `staff` (responde encuestas). Consultar indicadores requiere una
 sesión de administrador o supervisor. El backend aplica los permisos; ocultar o modificar
 controles del frontend no concede acceso. No es posible quitar o desactivar
 el último administrador activo. Para despliegues HTTPS, configura
 `SESSION_COOKIE_SECURE=true`; no uses las credenciales locales de desarrollo
 en producción.

 Las sesiones expiran absolutamente a los 10 minutos desde el inicio de sesión,
 incluso si hay actividad. En **Usuarios y roles**, el administrador puede
 restablecer la contraseña de otra cuenta: la contraseña temporal se muestra una
 sola vez y la persona debe cambiarla al ingresar. «Desactivar» retira el acceso
 sin borrar la cuenta ni sus registros. Los formularios ofrecen «¿Olvidaste tu
 contraseña?»; como el correo saliente no está configurado, la recuperación
 requiere contactar al administrador.

 El detalle consolidado de arquitectura, despliegue, pruebas, autenticación real,
 limitaciones y pendientes se encuentra en
 [docs/informe-implementacion-y-despliegue.md](docs/informe-implementacion-y-despliegue.md).

  ### Módulos institucionales MVP

  Las pantallas institucionales se encuentran en `/modulos/sugerencias`,
  `/modulos/planes-mejora`, `/modulos/reconocimientos`, `/modulos/organigrama`,
  `/modulos/eventos`, `/modulos/comunicaciones` y `/modulos/auditoria`. Sus
  endpoints están agrupados bajo `/api/v1/institucional`; los permisos se
  verifican en el backend. El envío del buzón no almacena la cuenta, sesión ni
  IP junto al contenido. Los registros de asistencia a eventos son distintos e
  independientes de las respuestas de encuestas.

  Estas pantallas son una primera versión funcional, no una certificación de
  privacidad/seguridad ni una aprobación para producción. La auditoría aún no
  registra todos los eventos de autenticación; también faltan controles de
  retención, migraciones versionadas, notificaciones y algunas capacidades
  avanzadas. Revisa `docs/spec.md`, `docs/spec-backend.md` y
  `docs/spec-frontend.md` para los límites y criterios pendientes.