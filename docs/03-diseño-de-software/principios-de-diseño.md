# Principios de diseño (SOLID) - Módulo Encuestas

* **Estilo arquitectónico:** Monolito modular.
* **Enfoque interno:** Clean Architecture (presentación, aplicación, dominio, infraestructura).
* **Stack:** Python, FastAPI, SQLAlchemy.

## 1. Objetivo
Documentar cómo se aplican los principios SOLID en el backend del Hospital Regional de Ayacucho (Sistema de Gestión del Clima Organizacional), organizado con Clean Architecture, para que cada módulo se programe de forma uniforme y las reglas de negocio no dependan de la tecnología.

---

## 2. SOLID en el Módulo Encuestas

![SOLID en el módulo Encuestas](/img/solid-modulo-encuestas.png)

| Principio | Dónde se aplica (capa) | Cómo se cumple en el Módulo | Archivos |
| :--- | :--- | :--- | :--- |
| **S · Responsabilidad única** | Todas las capas | Cada clase tiene una sola tarea: el controlador recibe la petición HTTP, el caso de uso coordina el registro, la entidad aplica las reglas de la encuesta y el repositorio guarda en PostgreSQL. | `encuestas_controller.py`, `registrar_respuesta.use_case.py`, `encuesta_pulse.py`, `postgres_encuesta_repository.py` |
| **O · Abierto/cerrado** | Infraestructura | Para agregar un nuevo algoritmo o motor de anonimización externo se crea un nuevo adaptador; el caso de uso de registro no se modifica. | `fastapi_algoritmo_supresion_adapter.py`, `nuevo_motor_anonimizacion_adapter.py` |
| **L · Sustitución de Liskov** | Infraestructura | Los adaptadores de supresión devuelven el mismo contrato `{ aprobado, requiereSupresion }`; el caso de uso funciona igual con cualquiera de ellos. | `fastapi_algoritmo_supresion_adapter.py`, `custom_supresion_adapter.py` |
| **I · Segregación de interfaces** | Dominio | Cada interfaz tiene solo lo que Encuestas necesita: `SupresionPort` solo evalúa la muestra mínima, `EncuestaRepository` solo guarda y busca encuestas. | `supresion_port.py`, `encuesta_repository.py` |
| **D · Inversión de dependencias** | Aplicación | El caso de uso recibe interfaces por el constructor y no conoce FastAPI, SQLAlchemy ni servicios externos; las implementaciones se conectan en la raíz de composición. | `registrar_respuesta.use_case.py`, `encuestas_module.py` |

---

## 3. Qué pasaría sin SOLID en el Módulo Encuestas

| Situación real | Sin SOLID | Con SOLID |
| :--- | :--- | :--- |
| **Se cambia el algoritmo o regla de supresión ($N < 5$)** | Hay que modificar el caso de uso y la lógica central | Solo se crea un nuevo adaptador en infraestructura |
| **Se cambia el ORM o la base de datos (ej. de SQLAlchemy a Tortoise)** | Se modifica todo el código del módulo Encuestas | Solo se reemplaza el repositorio de infraestructura |
| **Se quiere realizar pruebas unitarias del caso de uso** | Se necesita PostgreSQL y servicios externos reales | Se prueba de forma aislada con stubs o mocks de las interfaces |
| **Cambia una regla de confidencialidad o estado de la encuesta** | Hay que buscarla esparcida en controladores y scripts | Está centralizada únicamente en la entidad `EncuestaPulse` |

---

## 4. Relación con Clean Architecture y los patrones

| Principio | Lo cumple en el proyecto |
| :--- | :--- |
| **Responsabilidad única** | La estricta separación en capas de Clean Architecture |
| **Abierto/cerrado y Liskov** | El patrón Adapter (para el motor de anonimización / supresión) |
| **Segregación de interfaces** | Los puertos y contratos puros definidos en el Dominio (`SupresionPort`, `EncuestaRepository`) |
| **Inversión de dependencias** | El patrón Repository y la regla de dependencia: las capas externas apuntan hacia el dominio |