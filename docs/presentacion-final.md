# Presentación final — HospitaPulse

- **Duración sugerida:** 10–12 minutos
- **Formato:** 12 diapositivas con guion breve para exposición.

---

## Diapositiva 1 — HospitaPulse

### Sistema de gestión del clima organizacional

- Encuestas mensuales anónimas.
- Indicadores agregados con protección de privacidad.
- Herramientas MVP para apoyar la comunicación y mejora institucional.

**Guion:** “HospitaPulse busca convertir la opinión del personal en información
agregada que apoye decisiones de mejora, sin asociar respuestas de encuesta con
cuentas individuales.”

---

## Diapositiva 2 — Problema y necesidad

- La institución necesita conocer periódicamente la percepción del personal.
- Las respuestas deben ser confidenciales y no revelar grupos pequeños.
- Los resultados deben ser claros para quienes toman decisiones.
- La solución debe poder evolucionar por módulos.

**Guion:** “El reto no es solo recopilar respuestas: también es evitar que un
reporte permita identificar a una persona o interpretar una muestra demasiado
pequeña.”

---

## Diapositiva 3 — Objetivos y alcance

- Responder una encuesta Likert mensual de cinco dimensiones.
- Consultar promedios agregados por periodo.
- Controlar acceso mediante roles `admin`, `supervisor` y `staff`.
- Proveer módulos institucionales MVP para sugerencias, planes, eventos,
  comunicaciones y reconocimientos.
- Aplicar supresión de resultados cuando hay menos de cinco respuestas.

**Guion:** “El alcance entregado es un MVP funcional. Los módulos institucionales
no deben presentarse como una plataforma de producción completa.”

---

## Diapositiva 4 — Usuarios y flujo principal

1. El administrador crea las cuentas del personal.
2. El personal inicia sesión y responde la encuesta mensual.
3. La aplicación guarda valores de respuesta sin asociarlos con la cuenta.
4. Administradores y supervisores consultan resultados agregados.
5. Si la muestra es menor que cinco, se ocultan conteo y métricas.

**Guion:** “La cuenta autoriza el envío, pero no se persiste un identificador de
usuario junto a la respuesta de encuesta.”

---

## Diapositiva 5 — Arquitectura

```text
Navegador
   |
Cloudflare Quick Tunnel (HTTPS temporal)
   |
AWS Application Load Balancer
   |----------------------|
Next.js               FastAPI
                          |
                 PostgreSQL + Redis
                    (EFS para datos)
```

- Backend: FastAPI, SQLAlchemy y PostgreSQL.
- Frontend: Next.js, desplegado en contenedor independiente.
- Redis: caché de indicadores agregados.
- AWS: servicios ECS Fargate, balanceador y almacenamiento persistente.

**Guion:** “La aplicación separa la experiencia web y la API. PostgreSQL conserva
los datos y Redis acelera la consulta de indicadores, no almacena respuestas
individuales.”

---

## Diapositiva 6 — Privacidad y autenticación

- Contraseñas con hash bcrypt.
- Sesión local con JWT en cookie HttpOnly; expiración de 10 minutos.
- Autorización de roles verificada en backend.
- Umbral mínimo de cinco respuestas antes de mostrar resultados.
- **SSO/Keycloak no está implementado.**

**Guion:** “La autenticación actual es local, no federada. SSO con Keycloak se
mantiene como evolución futura y no debe afirmarse como parte del sistema.”

---

## Diapositiva 7 — SDD y diseño

- Especificaciones de producto, backend y frontend mantenidas en Markdown.
- Arquitectura documentada con diagramas C4.
- Backend organizado como monolito modular con separación por capas.
- La implementación se contrasta con requisitos y pruebas.
- Algunos módulos institucionales aún tienen deuda arquitectónica y son MVP.

**Guion:** “SDD permitió mantener trazabilidad entre requisitos, decisiones y
criterios de aceptación. La documentación también registra límites y trabajo
pendiente.”

---

## Diapositiva 8 — Interfaz y experiencia

- Inicio de sesión como punto de entrada a las vistas protegidas.
- Navegación adaptada al rol.
- Formularios de encuesta con estados de carga, error y confirmación.
- Diseño responsive para móvil.
- La interfaz no reemplaza los controles de autorización de la API.

**Guion:** “La experiencia permite responder desde móvil y explica la regla de
privacidad. La seguridad se conserva en el backend aunque la interfaz oculte
acciones.”

---

## Diapositiva 9 — Pruebas y resultados

- Backend: migración inicial aplicada y 23 pruebas pasaron con PostgreSQL
  aislado.
- Frontend: 3 pruebas Vitest, chequeo TypeScript y build pasaron.
- Playwright: los 3 casos E2E pasaron contra una API y frontend aislados,
  incluido el envío de la encuesta.
- k6: 50 VUs por 2 minutos, 57,173 solicitudes, 0 % de errores HTTP y p95 de
  **183 ms**, por debajo del objetivo de **500 ms**.

**Guion:** “La prueba local cumplió los umbrales iniciales de errores y latencia.
Es una señal favorable en este entorno, no una certificación de capacidad en
producción.”

---

## Diapositiva 10 — Despliegue actual y límites

- Demostración desplegada en AWS ECS Fargate.
- PostgreSQL persistente sobre EFS y Redis para caché.
- Cloudflare Quick Tunnel provee un enlace HTTPS temporal.
- No hay dominio propio permanente ni autoscaling validado.
- Los workflows están configurados, pero todavía deben ejecutarse en GitHub.

**Guion:** “El túnel permite compartir la demo sin comprar un dominio, pero su
URL puede cambiar. El entorno es demostrativo y no está aprobado para datos
institucionales reales.”

---

## Diapositiva 11 — Próximos pasos

1. Publicar los cambios revisados en GitHub y verificar CI/E2E en GitHub Actions.
2. Evaluar rendimiento también en la infraestructura objetivo, sin confundirlo
   con la prueba local aprobada.
3. Automatizar respaldos y probar restauración en un entorno controlado.
4. Definir autoscaling y estrategia de base de datos según presupuesto.
5. Usar dominio permanente solo si se autoriza su costo.
6. Evaluar SSO/OIDC y controles institucionales antes de producción.

La propuesta de escalabilidad y sus condiciones están en
[docs/escalabilidad-y-operacion.md](./escalabilidad-y-operacion.md); no se
aplicó ningún cambio de infraestructura AWS.

**Guion:** “Las mejoras de infraestructura dependen de presupuesto y aprobación.
No se deben desplegar cambios que aumenten costos sin definir primero límites y
criterios.”

---

## Diapositiva 12 — Cierre

### HospitaPulse convierte opiniones en señales de mejora, protegiendo la
privacidad como requisito del sistema.

**Mensaje final:** “El MVP demuestra el flujo de encuesta y análisis agregado.
La siguiente etapa es cerrar validación operativa, rendimiento y controles de
producción.”

---

## Preguntas que podrían hacerte

**¿Está implementado SSO?**

No. El sistema usa cuentas locales, bcrypt y sesión JWT en cookie HttpOnly.
Keycloak/OIDC queda pendiente.

**¿Cómo se protege el anonimato?**

Las respuestas no guardan el ID de la cuenta y los indicadores se suprimen si
hay menos de cinco respuestas. La política operativa y la revisión institucional
siguen siendo necesarias antes de usar datos reales.

**¿El sistema escala automáticamente?**

No está demostrado todavía. Los servicios están separados, pero faltan pruebas
de autoscaling y una estrategia de alta disponibilidad para PostgreSQL.

**¿Qué mostró k6?**

Se registraron 57,173 solicitudes con 0 % de errores HTTP y p95 de 183 ms
durante la prueba local. El resultado no sustituye una prueba en infraestructura
productiva.

**¿Por qué no hay dominio propio?**

La demo usa un Quick Tunnel temporal para evitar comprar un dominio. Para una
dirección permanente se necesita un dominio y configuración DNS autorizados.

## Documentos de respaldo

- [Especificación maestra](./spec.md)
- [Especificación backend](./spec-backend.md)
- [Especificación frontend](./spec-frontend.md)
- [Informe técnico](./informe-implementacion-y-despliegue.md)
- [Resultado E2E JUnit](./evidence/playwright-junit.xml)
- [Resultados k6](./evidence/k6-indicators-output.txt)
- [Plan de escalabilidad y operación](./escalabilidad-y-operacion.md)
