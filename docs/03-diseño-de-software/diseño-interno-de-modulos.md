# Diseño interno de módulos

> **Proyecto:** Sistema de Gestión del Clima Organizacional e Institucional — Hospital Regional de Ayacucho · **Backend:** Python + FastAPI · **Módulo de referencia:** encuestas  
> **Enfoque arquitectónico:** Clean Architecture dentro de cada módulo del monolito modular  
> **Nivel C4:** 4 – Código · **Versión:** 1.0

---

## 1. Propósito

Este documento describe **cómo se organiza el código dentro de un módulo** del backend. Tiene tres objetivos:

- que todos los módulos se construyan con la misma estructura;
- que las reglas de negocio queden aisladas de la tecnología;
- que cualquier integrante del equipo sepa dónde va cada archivo y de qué puede depender.


## 2. Estructura de carpetas

```text
src/
└── app/
    └── modulos/
        └── encuestas/
            ├── dominio/
            │   ├── encuesta-pulse.py           Entidad EncuestaPulse y sus reglas
            │   ├── respuesta-anonima.py        Objeto de valor RespuestaAnonima
            │   ├── estado-encuesta.py          Enumeración EstadoEncuesta
            │   ├── encuesta-repository.py      Interfaz (puerto) de persistencia
            │   ├── supresion-port.py           Interfaz (puerto) de anonimización (N < 5)
            │   └── resultado-anonimato.py      DTO de respuesta de supresión
            ├── aplicacion/
            │   ├── registrar-respuesta.use-case.py  Caso de uso RegistrarRespuestaAnonima
            │   └── registrar-respuesta.command.py   Datos de entrada del caso de uso
            ├── infraestructura/
            │   ├── postgres-encuesta-repository.py  Implementación con PostgreSQL (SQLAlchemy)
            │   └── fastapi-algoritmo-supresion.py   Implementación del algoritmo de supresión (N < 5)
            ├── presentacion/
            │   ├── encuestas.controller.py     Traduce HTTP ⇄ caso de uso
            │   └── encuestas.routes.py         Rutas /api/v1/encuestas
            ├── encuestas.module.py             Raíz de composición del módulo
            └── index.py                        API pública del módulo
```

| Archivo | Capa | Responsabilidad | Importa de |
| :--- | :--- | :--- | :--- |
| `encuesta-pulse.py` | Dominio | Crear evaluaciones válidas, evaluar dimensiones, cambiar de estado | Solo dominio |
| `respuesta-anonima.py` | Dominio | Representar una respuesta desvinculada del usuario y sus valores | Nada |
| `estado-encuesta.py` | Dominio | Definir los estados posibles de la encuesta | Nada |
| `encuesta-repository.py` | Dominio | Declarar qué operaciones de persistencia necesita el módulo | `encuesta-pulse.py` |
| `supresion-port.py` | Dominio | Declarar qué necesita el módulo para evaluar privacidad ($N < 5$) | `resultado-anonimato.py` |
| `resultado-anonimato.py` | Dominio | Estructura del resultado tras evaluar la muestra mínima | Nada |
| `registrar-respuesta.use-case.py` | Aplicación | Coordinar los pasos del registro de respuesta anónima | Dominio |
| `registrar-respuesta.command.py` | Aplicación | Datos de entrada validados del caso de uso | Nada |
| `postgres-encuesta-repository.py` | Infraestructura | Guardar y leer respuestas en PostgreSQL (OLTP) | Dominio + SQLAlchemy / driver de BD |
| `fastapi-algoritmo-supresion.py` | Infraestructura | Traducir el cálculo de supresión a la lógica de FastAPI ($N < 5$) | Dominio + reglas analíticas |
| `encuestas.controller.py` | Presentación | Leer la petición HTTP, invocar el caso de uso y responder | Aplicación |
| `encuestas.routes.py` | Presentación | Registrar las rutas en FastAPI | Presentación |
| `encuestas.module.py` | Composición | Crear las instancias concretas e inyectarlas | Todas las capas |
| `index.py` | Composición | Exponer solo lo que otros módulos pueden usar | `encuestas.module.py` |

### 3. Capas del módulo y regla de dependencia

> **Regla de dependencia:** El código solo puede importar hacia el dominio. El dominio no conoce FastAPI, PostgreSQL ni Keycloak.

![Diagrama de paquetes del módulo Encuestas](/img/paquetes-modulo-encuestas.png)

| Capa | Contiene | Responsabilidad | Puede depender de | No puede depender de |
| :--- | :--- | :--- | :--- | :--- |
| **Dominio** | Entidades, objetos de valor, enumeraciones, interfaces (puertos) | Reglas de negocio que serían ciertas con cualquier tecnología | Nada externo | Aplicación, infraestructura, presentación, FastAPI, ORM, SDK |
| **Aplicación** | Casos de uso, comandos | Orquestar el flujo: qué paso va primero y qué hacer si falla | Dominio | Infraestructura, presentación, FastAPI, ORM |
| **Infraestructura** | Repositorios concretos, adaptadores de servicios externos | Implementar las interfaces del dominio con una tecnología | Dominio, librerías externas | Aplicación, presentación |
| **Presentación** | Controladores, rutas | Traducir HTTP a llamadas del caso de uso y viceversa | Aplicación | Infraestructura, base de datos |
| **Composición** | `encuestas.module.py` | Elegir implementaciones concretas y conectarlas | Todas | — |

## 4. Diagrama de clases
![Diagrama de clases del módulo Encuestas](/img/clases-modulo-encuestas.png)
### 4.1 Notación UML utilizada

| Símbolo | Significado | Ejemplo en el diagrama |
| :--- | :--- | :--- |
| **Línea continua con flecha abierta** ($\rightarrow$) | **Asociación:** La clase guarda una referencia a la otra. | `RegistrarRespuestaUseCase` $\rightarrow$ `EncuestaRepository` |
| **Línea discontinua con flecha abierta** ($\dashrightarrow$) | **Dependencia:** La usa o la crea, pero no la guarda permanentemente. | `EncuestasController` *«crea»* `RegistrarRespuestaCommand` |
| **Línea discontinua con triángulo hueco** ($\dashrightarrow\triangleright$) | **Realización / Implementación:** Implementa un contrato o interfaz. | `PostgresEncuestaRepository` $\triangleright$ `EncuestaRepository` |
| **Rombo relleno** ($\blacklozenge$) | **Composición:** La parte no existe sin el ciclo de vida del todo. | `EncuestaPulse` $\blacklozenge$ `RespuestaAnonima` ($1..*$) |
| **Nombre en cursiva + «interface»** | **Interfaz:** Contrato abstracto sin implementación concreta. | *`«interface» EncuestaRepository`*, *`«interface» SupresionPort`* |
| **Símbolos `-` / `+`** | **Visibilidad:** `-` Atributo o método privado / `+` Atributo o método público. | `- estado`, `+ totalRespuestas()` |

## 5. Flujo de ejecución: registrar respuesta anónima
![Diagrama de secuencia de crear encuestas](/img/secuencia-crear-encuestaS.png)
| Paso | Origen → Destino | Acción | Capa |
| :---: | :--- | :--- | :--- |
| **1** | Personal del Hospital → `EncuestasController` | `POST /api/v1/encuestas` con `encuestaId`, `servicioId` y `respuestas` | Presentación |
| **2** | `EncuestasController` → `RegistrarRespuestaUseCase` | `ejecutar(cmd)` | Presentación → Aplicación |
| **3** | `RegistrarRespuestaUseCase` → `EncuestaPulse` | `crear(encuestaId, respuestas)`; se validan RN-01 a RN-03; estado `ACTIVA` | Aplicación → Dominio |
| **4** | `RegistrarRespuestaUseCase` → `EncuestaRepository` | `obtenerTotalRespuestasServicio(servicioId)` | Aplicación → Dominio (interfaz) |
| **5** | `RegistrarRespuestaUseCase` → `SupresionPort` | `evaluarMuestraMinima(total)` (RN-04: $N < 5$) | Aplicación → Dominio (interfaz) |
| **6** | `FastApiAlgoritmoSupresionAdapter` → Motor | Aplicación del K-Anonimato y supresión preventiva | Infraestructura → Externo |
| **7** | `RegistrarRespuestaUseCase` → `EncuestaPulse` | Si es seguro: `marcarRegistrada(autorizacion)` (RN-05) | Aplicación → Dominio |
| **8** | `RegistrarRespuestaUseCase` → `EncuestaRepository` | `guardarRespuesta(respuesta)` | Aplicación → Dominio (interfaz) |
| **9** | `PostgresEncuestaRepository` → PostgreSQL | `INSERT` de la respuesta anónima en la base de datos transaccional | Infraestructura → BD |
| **10** | `EncuestasController` → Cliente web | `201 Created` con `respuestaId` | Presentación |
| **11–12** | Alternativa | Si la muestra es insuficiente ($N < 5$), se aplica enmascaramiento y se avisa preventivamente | Aplicación → Presentación |

