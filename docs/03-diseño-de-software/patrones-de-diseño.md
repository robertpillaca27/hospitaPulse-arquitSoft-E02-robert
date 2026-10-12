# Patrones de Diseño - Módulo Encuestas

* **Estilo arquitectónico:** Monolito modular.
* **Enfoque interno:** Clean Architecture.
* **Stack:** Python, FastAPI, SQLAlchemy.

## 1. Patrones Aplicados

| Patrón | Dónde se usa | Problema que resuelve | Se implementa con | Archivos en el código |
| :--- | :--- | :--- | :--- | :--- |
| **Adapter** | Supresión / Validación externa | Cada servicio externo de anonimización tiene su propia API o SDK. | API REST del motor externo | `supresion_port.py`, `fastapi_algoritmo_supresion_adapter.py` |
| **Repository** | Capa de Dominio ➔ Base de datos | El negocio no debe acoplarse ni conocer detalles de SQL u ORMs específicos. | PostgreSQL (SQLAlchemy) | `encuesta_repository.py`, `postgres_encuesta_repository.py` |
| **Decorator** | Capa de Datos / Consultas frecuentes | Consultar datos pesados o repetitivos más rápido sin modificar la lógica del repositorio base. | Redis (Caché en memoria) | `cached_encuesta_repository.py` |

---

## 2. ¿Cómo funciona cada patrón?

* **Adapter (Adaptador):** 
  * *En pocas palabras:* **Traduce.** El sistema de negocio invoca una interfaz genérica (ej. `evaluarMuestraMinima(total)`), y el adaptador se encarga de transformarla a la estructura que espera el sistema externo o algoritmo de anonimización.
* **Repository (Repositorio):** 
  * *En pocas palabras:* **Abstrae los datos.** El núcleo de dominio indica qué necesita guardar o buscar, mientras que el repositorio traduce esa intención en consultas SQL concretas mediante SQLAlchemy hacia PostgreSQL.
* **Decorator (Decorador):** 
  * *En pocas palabras:* **Intercepta y optimiza.** Consulta primero en la caché (como Redis); si el recurso no se encuentra allí, ejecuta la consulta real en PostgreSQL y almacena el resultado en la caché.

---

## 3. Beneficios Clave

* **Desacoplamiento:** Cambiar de proveedor externo, algoritmo de anonimización o motor de base de datos **solo afecta a la capa de infraestructura** (específicamente al adaptador o repositorio correspondiente).
* **Escalabilidad y Rendimiento:** La caché con Redis se puede activar o retirar de forma transparente **sin tocar ni alterar las reglas de negocio**.

---

## 4. Patrones Previstos para Siguientes Iteraciones

| Patrón | Dónde se aplicaría | Cuándo implementarlo |
| :--- | :--- | :--- |
| **Observer** | Módulo de Dominio ➔ Notificaciones | Al requerir la emisión de eventos asíncronos ante respuestas críticas. |
| **Factory** | Creación de entidades complejas | Si la lógica de construcción de encuestas y respuestas se vuelve compleja. |
| **Facade** | Comunicación entre módulos | Cuando los módulos crezcan y necesiten una única puerta de entrada simplificada para interactuar entre ellos. |