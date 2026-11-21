# Plan de escalabilidad y operación

**Estado:** propuesta; no aplicada en AWS.
**Restricción aprobada:** presupuesto adicional de AWS = USD 0; no comprar un
dominio. La demostración conserva Cloudflare Quick Tunnel.

## 1. Estado actual verificado

- Frontend Next.js, API FastAPI, PostgreSQL, Redis y Cloudflare Tunnel corren
  como servicios separados en ECS Fargate.
- PostgreSQL usa almacenamiento EFS persistente. Esto evita depender del disco
  efímero de una tarea, pero no ofrece por sí solo alta disponibilidad ni
  escalado administrado de PostgreSQL.
- Redis almacena indicadores agregados con TTL e invalidación al responder.
- Hay una migración inicial Alembic; la API aún usa `create_all` al iniciar y
  el workflow de ECS no aplica migraciones.
- Las pruebas k6 locales con 50 VUs durante 2 minutos registraron 57,173
  solicitudes, 0 % de errores y p95 de 182.64 ms. No equivalen a una prueba de
  capacidad en AWS.
- No se ha habilitado autoscaling ni se han verificado métricas CloudWatch,
  límites de conexiones de PostgreSQL o costos del entorno.

## 2. Escalado inicial sugerido para ECS

Aplicar solo después de comprobar el presupuesto y observar métricas reales:

| Servicio | Mínimo | Máximo inicial | Señal propuesta | Acción |
|---|---:|---:|---|---|
| API | 1 tarea | 3 tareas | CPU objetivo 60 %; memoria de alarma 70 % | ECS Service Auto Scaling con scale-out más rápido que scale-in. |
| Frontend | 1 tarea | 3 tareas | CPU objetivo 60 %; memoria de alarma 70 % | ECS Service Auto Scaling; verificar límites de tareas y ALB. |
| Redis | 1 instancia actual | Sin cambio inicial | Memoria, conexiones, latencia y evictions | Mantener caché degradable; evaluar ElastiCache solo con necesidad demostrada. |

Estos valores son un punto de partida, no una configuración aprobada. Antes de
aplicarlos hay que confirmar vCPU/memoria por tarea, métricas CloudWatch,
capacidad del ALB y precio estimado. Mantener el mínimo en una tarea evita
duplicar inmediatamente el costo fijo, pero no garantiza alta disponibilidad.
El límite de tres tareas debe revisarse con evidencia de carga.

Las sesiones usan JWT en cookie y el estado de indicadores es compartido por
Redis/PostgreSQL; aun así, se deben comprobar permisos, cookies, límites de
conexión y comportamiento durante despliegues con varias tareas. No activar
sticky sessions como sustituto de estado compartido.

## 3. Base de datos y conexiones

### Próximo paso de bajo riesgo

1. Registrar el `max_connections` real de PostgreSQL y el número de procesos API.
2. Presupuestar conexiones por tarea. La configuración actual del pool permite
   hasta 50 conexiones por proceso (`pool_size=30` y `max_overflow=20`); con
   tres tareas podría alcanzar 150 conexiones.
3. Antes de habilitar tres tareas, fijar un pool por proceso compatible con el
   límite de PostgreSQL. Como hipótesis de prueba, evaluar `pool_size=10` y
   `max_overflow=5` por proceso, midiendo latencia y espera; no aplicarlo sin
   contrastarlo con el límite real del servidor.
4. Mantener las consultas de indicadores agregadas y cacheadas; no cachear
   respuestas individuales.

### Evolución recomendada para producción

- Migrar PostgreSQL desde una tarea con EFS hacia Amazon RDS for PostgreSQL en
  subredes privadas; valorar Multi-AZ según el nivel de disponibilidad y el
  presupuesto aprobados.
- Habilitar backups automáticos/PITR con una retención aprobada y realizar un
  ejercicio de restauración documentado.
- Usar lecturas réplica únicamente si métricas demuestran que las lecturas
  saturan la instancia primaria y la consistencia eventual es aceptable.
- Gestionar conexiones, credenciales y rotación fuera de la definición ECS.
- Ejecutar migraciones Alembic como paso controlado antes de desplegar la nueva
  versión de la API; usar cambios compatibles hacia adelante/atrás.

RDS Multi-AZ, réplicas, ElastiCache y mayores tareas generan costos adicionales.
Con el límite aprobado de USD 0, este documento no crea ni modifica esos
recursos.

## 4. Prueba de carga y criterios de aceptación

La ejecución local registrada está en
[`evidence/k6-indicators-output.txt`](./evidence/k6-indicators-output.txt) y su
resumen sin credenciales en
[`evidence/k6-indicators-summary.json`](./evidence/k6-indicators-summary.json).

Para una evaluación posterior en AWS:

1. Solicitar autorización expresa, ventana de prueba y presupuesto.
2. Usar un entorno aislado con datos sintéticos, no datos de pacientes ni del
   personal real.
3. Acordar límites de VUs/duración; el script actual rechaza intencionalmente
   destinos no locales.
4. Registrar región, tipo y tamaño de tareas, métricas CloudWatch, conexiones
   de BD, tasa de errores y p95/p99.
5. Escalar gradualmente y detenerse si se supera el presupuesto, la tasa de
   error acordada o la capacidad de PostgreSQL.

No quitar la protección loopback del script k6 para apuntarlo directamente a
producción.

## 5. Dominio, DNS y CDN

No hay un dominio propio disponible y no se autoriza comprar uno. Quick Tunnel
permite una demostración HTTPS sin costo de dominio, pero su URL es temporal y
no satisface DNS permanente ni CDN institucional. Si más adelante se dispone de
un dominio autorizado, configurar DNS en Cloudflare, un túnel nombrado con
credenciales gestionadas y reglas TLS; verificar costos/condiciones antes de
habilitarlo.

## 6. Publicación y despliegue

- La rama y PR propuestos publican el código para revisión y disparan CI/E2E.
- El workflow de despliegue AWS se activa solo en `main` y requiere
  `ENABLE_AWS_DEPLOY=true` más el rol OIDC. No se activará en este PR.
- Mantener las credenciales de las definiciones ECS fuera de Git; los archivos
  locales `td-api.json` y `td-frontend.json` están ignorados por Git.
- No hacer merge ni activar el deploy hasta revisar los resultados del PR,
  configurar secretos/variables AWS y aprobar presupuesto.

## 7. Decisiones pendientes para operar en AWS

- Presupuesto mensual autorizado para tareas adicionales, RDS/HA, Redis
  administrado, backups y tráfico.
- Máximo de tareas y ventana de operación.
- RPO/RTO y retención de respaldos aprobados por la institución.
- Dominio DNS ya adquirido o decisión de continuar solo con el túnel temporal.
- Autorización explícita de despliegue y de una prueba de carga en AWS.
