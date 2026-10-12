# Nivel 4 · Diagrama de código
**Proyecto:** Sistema de Gestión del Clima Organizacional e Institucional (Hospital Regional de Ayacucho)  
**Módulos detallados:** Encuestas y Supresión / K-Anonimato  
**Modelo:** C4 · Nivel 4 de 4 · Notación: UML · Versión: 1.0  

---

## 1. Objetivo
Mostrar cómo está organizado el código de un componente del nivel 3: sus clases, interfaces y la forma en que colaboran. Se detalla el flujo de **Registrar Respuesta Anónima**, que involucra a los módulos de Encuestas, Supresión y la integración con el motor de anonimización.

| Aspecto | Descripción |
| :--- | :--- |
| **Pregunta que responde** | ¿Qué clases existen dentro de un módulo y cómo se relacionan? |
| **Audiencia** | Desarrolladores |
| **Notación** | UML (diagrama de clases y diagrama de secuencia). El modelo C4 recomienda UML para este nivel |
| **Por qué estos módulos** | El nivel 4 se dibuja para los componentes más críticos. Encuestas y Supresión concentran las reglas de confidencialidad y la protección de identidad institucional |
| **Nivel anterior** | Nivel3-Diagrama-de-Componentes.md |

---

## 2. Diagrama de clases

* **Archivo editable:** `img/fuentes/nivel4-clases.svg`

### 2.1 Capas de Clean Architecture

| Capa | Contiene | Regla |
| :--- | :--- | :--- |
| **Presentación** | Controladores | Traduce HTTP a llamadas del caso de uso y viceversa |
| **Aplicación** | Casos de uso | Coordina los pasos del proceso; no conoce la tecnología |
| **Dominio** | Entidades, objetos de valor, interfaces | Contiene las reglas del negocio; no importa nada de las otras capas |
| **Infraestructura** | Repositorios y adaptadores | Implementa las interfaces del dominio con una tecnología concreta |

> *Regla de dependencia:* las flechas del código apuntan hacia el dominio. Las clases de infraestructura implementan interfaces del dominio (triángulo hueco); el dominio nunca conoce a la infraestructura.

---

### 2.2 Clases del módulo Encuestas

| Clase | Tipo | Capa | Responsabilidad |
| :--- | :--- | :--- | :--- |
| **EncuestasController** | Controlador | Presentación | Recibe `POST /api/v1/encuestas/respuesta` y responde al cliente |
| **RegistrarRespuestaUseCase** | Caso de uso | Aplicación | Valida el registro, evalúa el k-anonimato y guarda la respuesta |
| **EncuestaPulse** | Entidad | Dominio | Valida las reglas de la encuesta y controla sus estados |
| **RespuestaItem** | Objeto de valor | Dominio | Ítem evaluado, escala y valor de la respuesta |
| **EstadoEncuesta** | Enumeración | Dominio | ACTIVA, REGISTRADA, SUPRIMIDA |
| **EncuestaRepository** | Interfaz | Dominio | Contrato para guardar y buscar encuestas en la base de datos |

---

### 2.3 Clases del módulo Supresión / K-Anonimato

| Clase | Tipo | Capa | Responsabilidad |
| :--- | :--- | :--- | :--- |
| **EvaluarAnonimatoUseCase** | Caso de uso (API pública) | Aplicación | Único punto por el que otros módulos solicitan validación de muestra |
| **SupresionPort** | Interfaz | Dominio | Contrato para evaluar el umbral mínimo ($N < 5$) |
| **ResultadoAnonimatoDTO** | DTO | Dominio | Indica si la muestra está aprobada o requiere supresión |
| **FastApiAlgoritmoSupresionAdapter** | Adaptador | Infraestructura | Implementa `SupresionPort` conectándose al motor externo de anonimización |

---

### 2.4 Notación UML utilizada

| Símbolo | Significado | Ejemplo |
| :--- | :--- | :--- |
| **Línea continua con flecha abierta** | Asociación: la clase tiene una referencia a la otra | `RegistrarRespuestaUseCase` $\to$ `EncuestaRepository` |
| **Línea discontinua con flecha abierta** | Dependencia: la usa o la crea | `RegistrarRespuestaUseCase` $\dashrightarrow$ `EncuestaPulse` (*crea*) |
| **Línea discontinua con triángulo hueco** | Realización: implementa una interfaz | `PostgresEncuestaRepository` $\triangleright$ `EncuestaRepository` |
| **Rombo relleno** | Composición: la parte no existe sin el todo | `EncuestaPulse` $\blacklozenge$ `RespuestaItem` |
| **Nombre en cursiva con `«interface»`** | Interfaz | `SupresionPort` |
| **`+` / `-`** | Atributo o método público y privado | `+ ejecutar(cmd)` |

---

## 3. Diagrama de secuencia: registrar respuesta anónima

* **Archivo editable:** `img/fuentes/nivel4-secuencia.svg`

| Paso | Origen → Destino | Acción |
| :--- | :--- | :--- |
| **1** | Cliente web → EncuestasController | Envía `POST /api/v1/encuestas/respuesta` con el ID, servicio y respuestas |
| **2** | EncuestasController → RegistrarRespuestaUseCase | Ejecuta el caso de uso con el comando recibido |
| **3–4** | RegistrarRespuestaUseCase → EncuestaPulse | Crea la instancia de la encuesta y valida las reglas internas |
| **5** | RegistrarRespuestaUseCase → EvaluarAnonimatoUseCase | Solicita la evaluación de la muestra actual al módulo de Supresión |
| **6–7** | FastApiAlgoritmoSupresionAdapter → Motor Externo | Envía la solicitud de validación de k-anonimato por HTTPS |
| **8** | RegistrarRespuestaUseCase → EncuestaRepository | Si el anonimato está aprobado ($N \ge 5$), marca la encuesta como registrada |
| **9** | RegistrarRespuestaUseCase → PostgresEncuestaRepository | Guarda la respuesta anonimizada en PostgreSQL |
| **10** | EncuestasController → Cliente web | Responde `201 Created` con el ID de la encuesta registrada |
| **11–12** | Alternativa | Si la muestra es insuficiente ($N < 5$), la respuesta no se guarda y se responde `422 Unprocessable Entity` |

---

## 4. Patrones y principios que se ven en este nivel

| Elemento del diagrama | Patrón o principio |
| :--- | :--- |
| **FastApiAlgoritmoSupresionAdapter** | Patrón Adapter |
| **EncuestaRepository y PostgresEncuestaRepository** | Patrón Repository |
| **El caso de uso recibe interfaces, no clases concretas** | Principio de Inversión de Dependencias (SOLID) |
| **Una clase por responsabilidad (controlador, caso de uso, entidad, repositorio)** | Principio de Responsabilidad Única (SOLID) |
| **Encuestas usa a Supresión solo mediante su API pública** | Regla del monolito modular |