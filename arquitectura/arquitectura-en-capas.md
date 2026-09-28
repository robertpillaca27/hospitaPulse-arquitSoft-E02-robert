```mermaid
flowchart TD
%% =========================
%% PRESENTACIÓN
%% =========================
subgraph PRESENTACION["PRESENTACIÓN"]
    P1["Web / API / Interfaz Mobile"]
end

%% =========================
%% LÓGICA DE NEGOCIO
%% =========================
subgraph NEGOCIO["LÓGICA DE NEGOCIO"]
    N1["Gestión de Roles<br/>Motor de Encuestas<br/>Motor de Pulse Surveys<br>Algoritmo de Anonimización<br/>lgoritmo de Supresión<br/>Gestor de Organigrama<br/>Gestor de Plazas (CAP/PAP)<br/>Motor de Reportes<br/>Motor de Analítica"]
end

%% =========================
%% DATOS
%% =========================
subgraph DATOS["DATOS"]
    D1["Base de Datos OLTP<br/>Datamart OLAP"]
end

%% =========================
%% SISTEMAS EXTERNOS
%% =========================
subgraph EXTERNOS["SISTEMAS EXTERNOS"]
    E1["Keycloak SSO<br/>Sistemas Legacy<br/>Portal"]
end

%% =========================
%% FLUJO PRINCIPAL
%% =========================
PRESENTACION --> NEGOCIO
NEGOCIO --> DATOS
DATOS --> EXTERNOS

%% =========================
%% ESTILOS (TEMA OSCURO / BORDES BLANCOS)
%% =========================
style PRESENTACION fill:#1e1e1e,stroke:#ffffff,stroke-width:2px,color:#ffffff
style NEGOCIO fill:#1e1e1e,stroke:#ffffff,stroke-width:2px,color:#ffffff
style DATOS fill:#1e1e1e,stroke:#ffffff,stroke-width:2px,color:#ffffff
style EXTERNOS fill:#1e1e1e,stroke:#ffffff,stroke-width:2px,color:#ffffff

style P1 fill:#1e1e1e,stroke:none,color:#ffffff
style N1 fill:#1e1e1e,stroke:none,color:#ffffff
style D1 fill:#1e1e1e,stroke:none,color:#ffffff
style E1 fill:#1e1e1e,stroke:none,color:#ffffff