flowchart TD
%% =========================
%% CAPA DE PRESENTACIÓN
%% =========================
subgraph PRESENTACION["CAPA DE PRESENTACIÓN"]
ClienteWeb["Aplicación Web Responsive (React / Next.js)"]
ClienteMobile["Terminales de Enfermería & Tablets"]
end

%% =========================
%% CAPA DE LÓGICA DE NEGOCIO
%% =========================
subgraph NEGOCIO["CAPA DE LÓGICA DE NEGOCIO"]
Gateway["API Gateway & Reverse Proxy (NGINX)"]
AuthModule["Módulo de Identidad & Roles (RBAC)"]
SurveyEngine["Motor de Encuestas & Pulse Surveys"]
Anonymizer["Algoritmo de Anonimización & Supresión (N < 5)"]
OrgManager["Gestor de Organigrama & Plazas CAP/PAP"]
ReportEngine["Motor de Reportes & Analítica"]
end

%% =========================
%% CAPA DE DATOS
%% =========================
subgraph DATOS["CAPA DE DATOS"]
BDTransaccional[(Base de Datos OLTP - PostgreSQL)]
Datamart[(Datamart OLAP - Clima & Burnout)]
end

%% =========================
%% CAPA DE SISTEMAS EXTERNOS
%% =========================
subgraph EXTERNOS["CAPA DE SISTEMAS EXTERNOS"]
Keycloak["Servidor SSO / IAM (Keycloak)"]
Legacy["Sistemas Legacy (SIGA / INFORHUS)"]
Direccion["Portal Institucional (DIRESA / MINSA)"]
end

%% =========================
%% FLUJOS Y CONEXIONES
%% =========================
PRESENTACION -->|"HTTPS / REST API"| Gateway
Gateway --> AuthModule
Gateway --> SurveyEngine
Gateway --> OrgManager
Gateway --> ReportEngine

SurveyEngine --> Anonymizer
Anonymizer --> BDTransaccional
OrgManager --> BDTransaccional
ReportEngine --> Datamart

BDTransaccional -->|"Sincronización ETL / Batch"| Datamart
AuthModule -->|"OAuth2 / OIDC Token"| Keycloak
OrgManager -->|"Sincronización Lectura (CAP/PAP)"| Legacy
Datamart -->|"Exportación de Reportes"| Direccion

%% =========================
%% DISTRIBUCIÓN HORIZONTAL
%% =========================
ClienteWeb ~~~ ClienteMobile
AuthModule ~~~ SurveyEngine
SurveyEngine ~~~ Anonymizer
Anonymizer ~~~ OrgManager
OrgManager ~~~ ReportEngine
BDTransaccional ~~~ Datamart
Keycloak ~~~ Legacy
Legacy ~~~ Direccion

%% =========================
%% ESTILOS
%% =========================
style PRESENTACION fill:#222,stroke:#fff,stroke-width:2px,color:#fff
style NEGOCIO fill:#222,stroke:#fff,stroke-width:2px,color:#fff
style DATOS fill:#222,stroke:#fff,stroke-width:2px,color:#fff
style EXTERNOS fill:#222,stroke:#fff,stroke-width:2px,color:#fff

style ClienteWeb fill:#222,stroke:#fff,color:#fff
style ClienteMobile fill:#222,stroke:#fff,color:#fff

style Gateway fill:#222,stroke:#fff,color:#fff
style AuthModule fill:#222,stroke:#fff,color:#fff
style SurveyEngine fill:#222,stroke:#fff,color:#fff
style Anonymizer fill:#222,stroke:#fff,color:#fff
style OrgManager fill:#222,stroke:#fff,color:#fff
style ReportEngine fill:#222,stroke:#fff,color:#fff

style BDTransaccional fill:#222,stroke:#fff,color:#fff
style Datamart fill:#222,stroke:#fff,color:#fff

style Keycloak fill:#222,stroke:#fff,color:#fff
style Legacy fill:#222,stroke:#fff,color:#fff
style Direccion fill:#222,stroke:#fff,color:#fff