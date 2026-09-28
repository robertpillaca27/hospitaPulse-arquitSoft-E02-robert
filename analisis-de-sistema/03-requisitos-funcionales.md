### Requisitos Funcionales

| ID | Requisito funcional |
| :--- | :--- |
| **RF01** | El sistema debe permitir registrar y desplegar encuestas de pulso y clima organizacional. |
| **RF02** | El sistema debe desvincular la identidad del usuario de sus respuestas mediante técnicas de anonimización. |
| **RF03** | El sistema debe suprimir la visualización de reportes cuando la muestra de un servicio sea menor a 5 respuestas ($N < 5$). |
| **RF04** | El sistema debe permitir la gestión y versionado de la estructura del organigrama hospitalario en $N$ niveles. |
| **RF05** | El sistema debe presentar tableros analíticos e indicadores clave (KPIs) de burnout y clima organizacional. |
| **RF06** | El sistema debe permitir la autenticación centralizada mediante SSO e integración con Keycloak. |
| **RF07** | El sistema debe ejecutar procesos ETL para la ingesta periódica de datos de personal desde archivos o vistas de SIGA/INFORHUS. |
| **RF08** | El sistema debe permitir guardar el borrador de avance de una encuesta no finalizada por el usuario. |

---

### Relación entre Historias de Usuario (HU) y Requisitos Funcionales

| Historia de usuario | Requisitos funcionales relacionados |
| :--- | :--- |
| **HU01: Responder encuestas de pulso** | RF01, RF08 |
| **HU02: Registro anónimo de respuestas** | RF02, RF03 |
| **HU03: Consultar tableros de servicio** | RF03, RF05 |
| **HU04: Gestionar organigrama hospitalario** | RF04, RF07 |
| **HU05: Exportar reportes analíticos** | RF05 |
| **HU06: Integración SSO** | RF06 |