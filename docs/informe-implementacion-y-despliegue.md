# Informe técnico de implementación y despliegue — HospitaPulse

- **Fecha:** 21 de noviembre de 2026
- **Producto:** HospitaPulse — sistema de clima organizacional
- **Estado:** MVP funcional desplegado para demostración
- **Repositorio:** HospitaPulse

## 1. Resumen ejecutivo

HospitaPulse permite gestionar el acceso por roles, responder una encuesta
mensual anónima y consultar indicadores agregados protegidos por una regla de
privacidad. El sistema fue ejecutado localmente y publicado en AWS mediante
contenedores ECS.

Para una demostración temporal se incorporó Cloudflare Quick Tunnel, que entrega
un enlace HTTPS sin necesidad de comprar un dominio. La aplicación conserva una
URL pública HTTP detrás de AWS Application Load Balancer y una URL HTTPS temporal
proporcionada por Cloudflare.

El despliegue actual no es SSO. La autenticación implementada usa cuentas de
personal almacenadas en PostgreSQL, contraseñas con bcrypt y sesiones JWT en una
cookie HttpOnly. La integración con SSO/Keycloak aparece en documentos
arquitectónicos iniciales, pero sigue pendiente.

## 2. Alcance implementado

| Área | Implementación actual |
|---|---|
| Acceso | Inicio y cierre de sesión; contraseñas temporales; cambio obligatorio de contraseña. |
| Roles | `admin`, `supervisor` y `staff` (Personal). |
| Encuestas | Encuesta mensual con cinco preguntas Likert de 1 a 5. |
| Anonimato | Respuestas sin usuario, cuenta, DNI, IP ni clave correlacionable con la identidad. |
| Indicadores | Promedio general y promedio por dimensión; datos ocultos cuando hay menos de cinco envíos. |
| Personal | Creación, edición básica, activación/desactivación y restablecimiento de contraseña por administrador. |
| Módulos institucionales | MVP de sugerencias, planes de mejora, reconocimientos, organigrama, eventos, comunicaciones y auditoría. |
| Asistente | Integración con Gemini desde backend; envía solo la pregunta actual y requiere una clave válida. |
| Despliegue | Frontend, API, PostgreSQL, Redis y túnel Cloudflare en AWS ECS Fargate. |
| Persistencia | PostgreSQL montado sobre EFS cifrado. |
| Acceso temporal móvil | Cloudflare Quick Tunnel con HTTPS y URL `trycloudflare.com`. |

## 3. Arquitectura técnica

### 3.1 Patrón de aplicación

- Monolito modular con separación inspirada en Clean Architecture.
- Backend Python 3.12+, FastAPI, Pydantic v2 y SQLAlchemy.
- Frontend Next.js, compilado en modo `standalone` y ejecutado como usuario no
  root dentro de su contenedor.
- PostgreSQL como fuente transaccional.
- Redis exclusivamente para caché de indicadores agregados.
- Docker Compose para desarrollo local.

La organización del backend separa presentación, aplicación, dominio e
infraestructura dentro de módulos. Las rutas exponen DTOs HTTP, los casos de uso
coordinan reglas y los repositorios adaptan PostgreSQL o Redis.

### 3.2 Flujo público de la aplicación

```text
Navegador o celular
        |
        v
Cloudflare Quick Tunnel (HTTPS temporal)
        |
        v
Application Load Balancer de AWS
        |--- /api/v1, /docs, /      -> API FastAPI en ECS
        |--- demás rutas            -> Frontend Next.js en ECS
                                      |
                                      v
                              PostgreSQL sobre EFS
                                      |
                                      v
                              Redis para agregados
```

Cuando la aplicación se carga por HTTPS, el frontend usa rutas relativas
`/api/v1`. De esta manera evita contenido mixto y mantiene frontend, API y cookie
en el mismo origen visible para el navegador.

## 4. Infraestructura desplegada

### 4.1 AWS

La infraestructura se encuentra en `us-east-2` y utiliza:

- **ECS Fargate:** ejecución de contenedores sin administrar servidores.
- **ECR:** almacenamiento de imágenes de frontend, API y PostgreSQL.
- **Application Load Balancer:** publicación HTTP del frontend y API.
- **AWS Cloud Map:** resolución privada entre ECS para PostgreSQL y Redis.
- **EFS:** almacenamiento cifrado y persistente de PostgreSQL.
- **CloudWatch Logs:** registros de API, frontend y Cloudflare.
- **Security Group compartido:** acceso TCP interno a PostgreSQL y Redis; la base
  de datos no se publicó a Internet.

Los servicios principales son:

| Servicio | Función |
|---|---|
| `hospitahub-frontend-service` | Next.js en puerto 3000. |
| `hospitahub-api-td-service-per4kzto` | FastAPI en puerto 8000. |
| `hospitahub-postgres-td-service-ppl1pjpz` | PostgreSQL. |
| `hospitahub-redis-td-service-91oobcgc` | Redis. |
| `hospitapulse-cloudflare-tunnel` | `cloudflared` y generación de URL temporal. |

### 4.2 Persistencia

Inicialmente, PostgreSQL se ejecutaba sin volumen persistente, por lo que los
datos podían desaparecer al sustituirse la tarea. Se corrigió mediante un
sistema de archivos EFS cifrado montado en `/var/lib/postgresql/data`.

La corrección se validó reiniciando PostgreSQL y la API. Después de ambos
reinicios, la aplicación mantuvo usuarios, encuesta e indicadores. La encuesta
de noviembre conserva 28 envíos anónimos.

### 4.3 Cloudflare Quick Tunnel

Enlace temporal validado durante la implementación:

`https://psychiatry-devel-residents-liz.trycloudflare.com`

El enlace:

- utiliza HTTPS;
- funciona desde un celular;
- no requiere instalar software al usuario;
- no requiere comprar un dominio;
- puede cambiar al reiniciar o recrear el servicio `cloudflared`;
- no es apropiado para una URL institucional permanente.

Si la tarea Cloudflare se reinicia, debe extraerse la nueva URL del grupo de logs
`/ecs/hospitapulse-cloudflare`.

## 5. Autenticación: implementación real

### 5.1 Flujo actual

1. El usuario introduce nombre de usuario y contraseña.
2. FastAPI busca la cuenta activa en PostgreSQL.
3. La contraseña se valida con bcrypt.
4. El backend firma un JWT local.
5. El navegador recibe el JWT en una cookie `HttpOnly`.
6. Cada solicitud protegida incluye la cookie con `credentials: include`.
7. El backend carga la identidad, comprueba su estado y aplica el rol.
8. La sesión expira absolutamente a los 10 minutos.

El JWT no se guarda en `localStorage` y JavaScript no puede leer la cookie. La
sesión se invalida funcionalmente al eliminar la cookie mediante logout.

### 5.2 Comparación con SSO

| Aspecto | Implementado | SSO/Keycloak |
|---|---:|---:|
| Credenciales propias de HospitaPulse | Sí | No es obligatorio |
| JWT emitido por el backend | Sí | No; normalmente emite un IdP |
| Cookie HttpOnly | Sí | Puede usarse |
| Redirección OIDC/OAuth2 | No | Sí |
| Proveedor de identidad corporativo | No | Sí |
| Federación o inicio de sesión único | No | Sí |
| Gestión central de sesiones | No | Sí |

**Conclusión:** SSO/Keycloak no fue implementado. La documentación original lo
consideraba una decisión arquitectónica o una posible evolución; esta iteración
incorporó autenticación local por roles. Para habilitar SSO deberán elegirse
proveedor, protocolo, secretos, mapeo de roles y política de cuentas.

## 6. Encuestas y privacidad

La respuesta anónima guarda:

- identificador interno del envío;
- encuesta;
- fecha del envío;
- pregunta;
- valor Likert.

No guarda el identificador de usuario ni una clave que permita asociar el envío
con una cuenta. La sesión identifica únicamente si el rol `staff` está
autorizado para enviar. La regla N >= 5 se aplica en el backend antes de
construir la respuesta divulgable.

Para un periodo con menos de cinco respuestas se ocultan:

- total;
- promedio general;
- dimensiones;
- cualquier gráfico derivado.

Redis no almacena respuestas individuales. Al registrar una respuesta se invalida
la caché del periodo; si Redis falla, el backend consulta PostgreSQL.

## 7. Resultado validado

En noviembre de 2026, el endpoint público autenticado devolvió:

| Métrica | Valor |
|---|---:|
| Respuestas | 28 |
| Promedio general | 2.64/5 |
| Apoyo | 2.82 |
| Bienestar | 2.71 |
| Carga laboral | 2.61 |
| Comunicación | 2.54 |
| Reconocimiento | 2.50 |

Los resultados se encuentran por encima del umbral mínimo y la API confirmó
`enmascarado: false`. Para periodos sin encuesta o sin muestra suficiente se
mantiene la respuesta protegida.

## 8. Pruebas y evidencia

Se validó en una sesión anterior:

- build de Next.js 15.5.29;
- compilación TypeScript;
- generación de rutas estáticas y dinámicas;
- estado `200` de frontend público;
- estado `200` de `/api/v1/health`;
- apertura de Swagger UI;
- login de administrador en el despliegue;
- consulta autorizada de indicadores;
- carga de la interfaz desde navegador mediante HTTPS;
- uso del mismo origen HTTPS para frontend y API;
- persistencia de los indicadores tras reinicios de tareas ECS.

Se añadieron posteriormente:

- Workflows GitHub Actions para pruebas backend/frontend, build de imágenes y
  pruebas E2E con Playwright.
- Pruebas Playwright para health/login, indicadores protegidos y envío de
  encuesta con una cuenta de personal creada para la prueba.
- Migración inicial Alembic y scripts manuales de respaldo/restauración local.

Los workflows nuevos no se han ejecutado en GitHub; el E2E sí se ejecutó
localmente contra servicios aislados. La aplicación de migraciones en AWS y la
restauración de un respaldo allí siguen pendientes. El job de despliegue AWS
permanece desactivado hasta configurar `ENABLE_AWS_DEPLOY` y el rol OIDC con
permisos mínimos.

Validación local adicional del 21 de noviembre de 2026:

- Backend: migración inicial Alembic aplicada y 23 pruebas pasaron con
  PostgreSQL aislado.
- Frontend: 3 pruebas Vitest pasaron, `tsc --noEmit` y `next build` pasaron.
- Playwright: los 3 casos E2E pasaron contra API y frontend aislados, incluido
  el cambio de contraseña temporal y envío de encuesta; el resultado JUnit se
  guardó en `docs/evidence/playwright-junit.xml`.
- k6: 50 VUs durante 2 minutos; 57,173 solicitudes, 0 % de errores HTTP y p95
  de 182.64 ms. Cumplió el objetivo local de p95 menor a 500 ms.
- Docker Compose: la configuración fue validada. El despliegue AWS sigue sin
  ejecutarse; los resultados locales no certifican capacidad de producción.

Los permisos de administración/indicadores dependen del backend. Ocultar enlaces
en el frontend no concede ni elimina permisos.

## 9. Documentación relacionada

| Documento | Uso para el informe |
|---|---|
| `README.md` | Preparación local, Docker Compose, roles, PostgreSQL, Redis y acceso temporal. |
| `docs/spec.md` | Especificación maestra, alcance, autenticación, roles y despliegue. |
| `docs/spec-backend.md` | Contratos FastAPI, privacidad, persistencia, EFS y criterios backend. |
| `docs/spec-frontend.md` | UX, sesiones, cookie, API por mismo origen y validación Cloudflare. |
| `docs/presentacion-final.md` | Guion de exposición y respuestas para la defensa. |
| `docs/escalabilidad-y-operacion.md` | Propuesta de escalado y operación AWS; no aplicada. |
| `docs/01-analisis-de-sistema/` | Actores, historias, requisitos, atributos, restricciones y decisiones. |
| `docs/02-arquitectura-software/` | Arquitectura inicial, capas y estructura backend/frontend. |
| `docs/03-diseño-de-software/` | Principios, patrones y diseño interno. |
| `docs/04-modelo-c4/` | Contexto, contenedores, componentes y código. |

Los documentos de análisis pueden mencionar Keycloak, OLAP o capacidades futuras.
Para describir lo realmente disponible deben prevalecer las especificaciones
actualizadas y este informe.

## 10. Riesgos y pendientes

1. Cloudflare Quick Tunnel genera una URL temporal y cambia al reiniciar.
2. La URL HTTP del balanceador no está protegida con TLS institucional.
3. EFS aporta persistencia, pero todavía no define una política aprobada de
   respaldo y restauración.
4. Existe una migración inicial Alembic, pero la aplicación aún usa `create_all`
   al iniciar y el workflow de ECS no aplica migraciones.
5. SSO/Keycloak no está integrado.
6. Los secretos de las definiciones ECS deben migrarse a AWS Secrets Manager o
   Parameter Store.
7. El despliegue temporal debe usar `Secure` para la cookie HTTPS en una
   configuración final con dominio estable.
8. Falta monitoreo institucional completo, alertas, trazabilidad, retención,
   límites de cuota y plan de respuesta a incidentes.
9. La auditoría no registra todos los eventos de autenticación.
10. Los datos disponibles son de demostración; el uso con personal real exige
    aprobación, aviso de privacidad y retención documentada.

## 11. Recomendaciones

Para convertir el despliegue en un entorno institucional:

1. registrar un dominio, por ejemplo `hospitapulse.pe`;
2. emitir certificado TLS y forzarlo en el balanceador;
3. convertir Cloudflare en túnel autenticado o usar DNS/CDN estable;
4. mover secretos a AWS Secrets Manager;
5. activar `SESSION_COOKIE_SECURE=true`;
6. aplicar migraciones Alembic de forma controlada durante el despliegue;
7. programar copias y probar restauración de EFS/PostgreSQL;
8. definir SSO por OIDC con Keycloak o el proveedor institucional;
9. configurar alertas, métricas, retención de logs y auditoría de acceso;
10. realizar pruebas de seguridad y privacidad antes de cargar datos reales.

## 12. Operación para demostración

Para abrir la aplicación desde un teléfono:

1. conectar el dispositivo a Internet;
2. abrir la URL HTTPS actual de Cloudflare;
3. iniciar sesión con una cuenta creada;
4. usar una cuenta `staff` para responder la encuesta;
5. usar `admin` o `supervisor` para consultar indicadores.

Una persona sin cuenta puede abrir la pantalla inicial, pero no puede responder
la encuesta ni consultar indicadores. No se deben incluir contraseñas ni
credenciales en este informe, capturas públicas, frontend o repositorio.
