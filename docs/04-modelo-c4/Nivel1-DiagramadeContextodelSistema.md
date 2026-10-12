# Nivel 1 · Diagrama de contexto del sistema
**Proyecto:** Sistema de Gestión del Clima Organizacional e Institucional (Hospital Regional de Ayacucho)  
**Modelo:** C4 · Nivel 1 de 4 · Versión: 1.0  

---

## 1. Objetivo
Mostrar el sistema del Hospital Regional de Ayacucho como una sola caja: quiénes lo usan (personal asistencial, administrativo y directivos) y con qué sistemas externos o servicios se comunica. Es la vista de mayor nivel y la primera que se presenta a cualquier persona, técnica o no.

| Aspecto | Descripción |
| :--- | :--- |
| **Pregunta que responde** | ¿Qué es el sistema, quién lo usa y con qué se integra? |
| **Audiencia** | Todos: negocio, comité directivo, equipo de desarrollo, operaciones |
| **Qué no muestra** | Tecnologías, servidores, bases de datos ni módulos internos |
| **Siguiente nivel** | Nivel 2 - Diagrama de Contenedores |

---

## 2. Diagrama

![](/img/nivel1-contexto.png)
---

## 3. Personas (usuarios)

| Persona | Descripción | Qué hace en el sistema |
| :--- | :--- | :--- |
| **Personal Asistencial (Médicos, Enfermeras, Técnicos)** | Personal de salud del hospital | Responde las encuestas de clima organizacional de forma anónima y consulta reportes agregados según su área |
| **Personal Administrativo** | Empleados de gestión y soporte del hospital | Completa las encuestas institucionales y evalúa las dimensiones del clima laboral |
| **Administrador del Sistema / RRHH** | Responsable de la gestión del clima y analítica institucional | Configura las encuestas, gestiona periodos de evaluación, supervisa el cumplimiento y exporta reportes con control de supresión |

---

## 4. Sistemas

| Sistema | Tipo | Responsabilidad | Quién lo construye |
| :--- | :--- | :--- | :--- |
| **Sistema de Gestión del Clima Organizacional (HRA)** | Sistema en alcance | Permite registrar encuestas anónimas, aplicar reglas de K-anonimato y generar analítica institucional | El equipo del proyecto |
| **Motor Externo de Anonimización / Supresión** | Sistema externo | Valida umbrales de muestras mínimas ($N < 5$) para prevenir la reidentificación | Proveedor externo / Módulo especializado |
| **Directorio Activo / SSO del Hospital** | Sistema externo | Gestiona la autenticación segura y roles del personal del hospital | Área de TI del Hospital Regional de Ayacucho |
| **Servicio de Notificaciones (Correo / SMS)** | Sistema externo | Envía alertas y recordatorios institucionales para completar las encuestas | Proveedor de servicios de mensajería |

---

## 5. Relaciones

| Origen | Destino | Descripción | Protocolo |
| :--- | :--- | :--- | :--- |
| **Personal Asistencial** | Sistema de Gestión del Clima (HRA) | Responde encuestas y visualiza tableros analíticos | HTTPS |
| **Personal Administrativo** | Sistema de Gestión del Clima (HRA) | Responde encuestas institucionales | HTTPS |
| **Administrador del Sistema / RRHH** | Sistema de Gestión del Clima (HRA) | Gestiona campañas de encuestas y evalúa indicadores | HTTPS |
| **Sistema de Gestión del Clima (HRA)** | Motor Externo de Anonimización | Solicita validación de k-anonimato y supresión de datos | HTTPS/REST |
| **Sistema de Gestión del Clima (HRA)** | Directorio Activo / SSO del Hospital | Valida credenciales institucionales de acceso | OAuth2 / OIDC |
| **Sistema de Gestión del Clima (HRA)** | Servicio de Notificaciones | Envía alertas y recordatorios a los usuarios | HTTPS/REST |

---

## 6. Decisiones y supuestos

| # | Decisión o supuesto | Motivo |
| :--- | :--- | :--- |
| **1** | **Integración mediante API REST con servicios externos** | Es el estándar de interoperabilidad que permite desacoplar los motores de anonimización y autenticación sin comprometer la base de datos central. |
| **2** | **El sistema garantiza el anonimato absoluto en el almacenamiento** | Las respuestas se separan de la identidad del usuario mediante tokens y se aplica la regla estricta de supresión ($N < 5$) para cumplir con las políticas de confidencialidad del hospital. |
| **3** | **Los sistemas externos operan bajo contratos desacoplados** | Al depender de servicios de autenticación y pasarelas externas, se aplica el patrón Adapter para aislar cualquier cambio de proveedor. |

---

## Pendientes por definir

| Tema | Detalle |
| :--- | :--- |
| **Canal oficial de notificaciones** | Confirmar con el área de TI del hospital si las alertas se enviarán exclusivamente por correo institucional o si se integrarán notificaciones vía WhatsApp/Telegram. |
| **Periodicidad de sincronización con el Directorio Activo** | Definir la frecuencia con la que se actualizan los roles y áreas de los trabajadores del hospital para la segmentación de las encuestas. |