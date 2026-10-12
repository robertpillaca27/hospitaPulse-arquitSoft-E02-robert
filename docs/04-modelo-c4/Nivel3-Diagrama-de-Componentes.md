# Nivel 3 · Diagrama de componentes
**Proyecto:** Sistema de Gestión del Clima Organizacional e Institucional (Hospital Regional de Ayacucho)  
**Contenedor detallado:** API del Sistema (Backend Modular)  
**Modelo:** C4 · Nivel 3 de 4 · Versión: 1.0  

---

## 1. Objetivo
Abrir el contenedor de la API del nivel 2 y mostrar sus componentes: los módulos del monolito modular, la responsabilidad de cada uno, cómo se relacionan entre sí y con la base de datos, la caché y los sistemas externos.

| Aspecto | Descripción |
| :--- | :--- |
| **Pregunta que responde** | ¿Cómo se divide el backend por dentro y qué hace cada parte? |
| **Audiencia** | Arquitectos y desarrolladores |
| **Qué es un componente** | Un grupo de funcionalidades con una responsabilidad clara, accesible mediante una interfaz. En este proyecto, cada módulo del monolito es un componente |
| **Nivel anterior** | Nivel2-Diagrama-de-Contenedores.md |
| **Siguiente nivel** | Nivel4-Diagrama-de-Codigo.md |

---

## 2. Diagrama

* **Archivo editable:** `img/fuentes/nivel3-componentes.drawio`

---

## 3. Componentes

| Componente | Responsabilidad | Funcionalidades principales | Carpeta en el código |
| :--- | :--- | :--- | :--- |
| **API REST** | Punto de entrada HTTP del contenedor | Rutas `/api/v1`, autenticación OAuth2/JWT, validación de entradas, manejo global de errores | `src/api/` |
| **Usuarios / Personal** | Identidad y acceso institucional | Gestión de personal asistencial, administrativo y roles corporativos | `src/modules/usuarios/` |
| **Áreas / Servicios** | Gestión organizacional | Estructura jerárquica y áreas del hospital (necesaria para el cálculo de muestras) | `src/modules/areas/` |
| **Encuestas** | Gestión principal del clima | Creación de campañas, registro de respuestas anónimas y control de estado | `src/modules/encuestas/` |
| **Supresion / K-Anonimato** | Validación de confidencialidad | Aplica la regla estricta de supresión ($N < 5$) para prevenir la reidentificación | `src/modules/supresion/` |
| **Reportes / Analítica** | Indicadores institucionales | Generación de tableros agregados por servicio y dimensiones del clima | `src/modules/reportes/` |
| **Notificaciones** | Comunicación institucional | Envío de alertas y recordatorios a los trabajadores | `src/modules/notificaciones/` |

---

## 4. Relaciones entre componentes

| Origen | Destino | Descripción | Tipo de comunicación |
| :--- | :--- | :--- | :--- |
| **Aplicación web** | API REST | Llama a la API mediante peticiones HTTP | HTTPS/JSON |
| **API REST** | Módulos de negocio | Invoca los casos de uso correspondientes | Llamada en memoria |
| **Encuestas** | Usuarios / Personal | Valida la pertenencia del usuario al hospital | Llamada en memoria (API pública del módulo) |
| **Encuestas** | Áreas / Servicios | Asocia cada respuesta al servicio correspondiente | Llamada en memoria |
| **Encuestas** | Supresion / K-Anonimato | Valida si la muestra cumple el umbral mínimo antes de registrar | Llamada en memoria |
| **Reportes** | Supresion / K-Anonimato | Aplica filtros de supresión antes de mostrar métricas | Llamada en memoria |
| **Encuestas** | Notificaciones | Publica el evento de registro o alertas de campaña | Evento en memoria |

---

## 5. Relaciones con contenedores y sistemas externos

| Componente | Destino | Descripción | Protocolo | Patrón aplicado |
| :--- | :--- | :--- | :--- | :--- |
| **Todos los módulos** | Base de datos (PostgreSQL) | Cada módulo lee y escribe solo sus propias tablas | SQL | Repository |
| **Reportes / Encuestas** | Caché (Redis) | Guarda y lee indicadores agregados en memoria | TCP | Decorator |
| **Supresion / K-Anonimato** | Motor Externo de Anonimización | Valida reglas de supresión complejas | HTTPS/REST | Adapter |
| **Usuarios / Personal** | Directorio Activo / SSO | Valida credenciales corporativas | OAuth2 / OIDC | Adapter |
| **Notificaciones** | Servicio de Notificaciones | Envía correos y alertas institucionales | HTTPS/REST | Adapter |

---

## 6. Reglas del monolito modular

| # | Regla | Motivo |
| :--- | :--- | :--- |
| **1** | **Todos los componentes se despliegan juntos** | Es un monolito: un solo proceso y un solo contenedor ejecutable en FastAPI. |
| **2** | **Un módulo usa a otro solo a través de su API pública (`index.py`)** | Evita acoplamientos estrechos y que un cambio interno rompa a los demás módulos. |
| **3** | **Un módulo no lee ni escribe directamente las tablas de otro** | Mantiene la independencia estricta de los datos y la privacidad por esquema. |
| **4** | **Cada sistema externo se integra en un único módulo** | La integración con terceros queda centralizada y es fácil de reemplazar mediante adaptadores. |
| **5** | **Cada módulo se organiza por dentro con Clean Architecture** | Las reglas de negocio permanecen aisladas y no dependen de la tecnología (ver nivel 4). |