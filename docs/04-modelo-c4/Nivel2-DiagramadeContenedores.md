# Nivel 2 · Diagrama de contenedores
**Proyecto:** Sistema de Gestión del Clima Organizacional e Institucional (Hospital Regional de Ayacucho)  
**Modelo:** C4 · Nivel 2 de 4 · Versión: 1.0  

---

## 1. Objetivo
Abrir la caja «Sistema de Gestión del Clima Organizacional» del nivel 1 y mostrar los contenedores que la forman: las aplicaciones y almacenes de datos que se ejecutan por separado, la tecnología de cada uno y cómo se comunican.

| Aspecto | Descripción |
| :--- | :--- |
| **Pregunta que responde** | ¿De qué piezas ejecutables se compone el sistema y con qué tecnología? |
| **Audiencia** | Arquitectos, desarrolladores, operaciones |
| **Qué es un contenedor** | Algo que se ejecuta o almacena datos de forma independiente: una aplicación web, una API, una base de datos (no es lo mismo que un contenedor Docker) |
| **Nivel anterior** | Nivel1-Diagrama-de-Contexto-del-Sistema.md |
| **Siguiente nivel** | Nivel3-Diagrama-de-Componentes.md |

---

## 2. Diagrama

![](/img/nivel2-contenedores.png)

---

## 3. Contenedores

| Contenedor | Tecnología | Responsabilidad | Datos que maneja |
| :--- | :--- | :--- | :--- |
| **Aplicación web** | SPA · React / Next.js | Interfaz para responder encuestas de forma anónima, visualización de tableros de clima y panel de administración institucional. Se ejecuta en el navegador. | Ninguno persistente; solo el estado de la pantalla y el token de sesión. |
| **API del Sistema (Backend)** | Python + FastAPI | Expone la API REST, aplica las reglas de negocio, valida el K-anonimato y la regla de supresión ($N < 5$). Es un monolito modular: un solo proceso con módulos internos. | Ninguno propio; utiliza la base de datos y la caché en memoria. |
| **Base de datos** | PostgreSQL | Almacena de forma permanente la información institucional, encuestas, respuestas anonimizadas y catálogos de áreas. | Usuarios, áreas, encuestas, preguntas y respuestas cifradas/anonimizadas. |
| **Caché** | Redis | Guarda en memoria los indicadores y configuraciones más consultadas para responder con mayor agilidad. | Copia temporal de configuraciones y métricas agregadas. |

---

## 4. Relaciones

| Origen | Destino | Descripción | Protocolo |
| :--- | :--- | :--- | :--- |
| **Personal Asistencial, Administrativo, Admin** | Aplicación web | Usan la aplicación desde el navegador | HTTPS |
| **Aplicación web** | API del Sistema (Backend) | Llama a la API REST para operaciones y registro | HTTPS/JSON |
| **API del Sistema (Backend)** | Base de datos | Lee y escribe información transaccional | SQL sobre TCP |
| **API del Sistema (Backend)** | Caché | Lee y escribe datos temporales en memoria | TCP |
| **API del Sistema (Backend)** | Motor Externo de Anonimización | Solicita validación de k-anonimato y supresión | HTTPS/REST |
| **API del Sistema (Backend)** | Directorio Activo / SSO del Hospital | Valida credenciales corporativas | OAuth2 / OIDC |
| **API del Sistema (Backend)** | Servicio de Notificaciones | Envía alertas institucionales | HTTPS/REST |

---

## 5. Decisiones arquitectónicas reflejadas

| Decisión | Alternativa descartada | Motivo |
| :--- | :--- | :--- |
| **Un único contenedor de backend (monolito modular)** | Microservicios | Equipo académico/técnico de tamaño acotado; los módulos internos permiten separar servicios en el futuro si la escala del hospital lo requiere. |
| **Frontend separado del backend (SPA + API REST)** | Páginas generadas en el servidor | El frontend y el backend evolucionan y se despliegan de forma independiente, optimizando la experiencia en dispositivos corporativos. |
| **PostgreSQL como base de datos relacional** | Base de datos NoSQL | Las encuestas institucionales, reportes y trazabilidad de cumplimiento exigen consistencia estricta y transaccionalidad. |
| **Redis como caché de soporte** | Consultar siempre la base de datos | Los indicadores agregados de clima laboral consultados frecuentemente se benefician de una caché de baja latencia. |
| **Solo la API se comunica con sistemas externos** | Llamar a servicios externos desde el navegador | Las credenciales sensibles y tokens de integración con el directorio activo y motor de anonimización permanecen seguros en el servidor. |

---

## 6. Seguridad entre contenedores

| Comunicación | Medida |
| :--- | :--- |
| **Navegador → Aplicación web y API** | Tráfico cifrado de extremo a extremo con HTTPS |
| **Aplicación web → API** | Autenticación basada en tokens seguros (JWT / OAuth2) en cada petición |
| **API → Base de datos y caché** | Acceso restringido exclusivamente desde la red interna; credenciales gestionadas mediante variables de entorno |
| **API → Sistemas externos** | Claves y credenciales de cada proveedor guardadas de forma segura solo en el servidor |