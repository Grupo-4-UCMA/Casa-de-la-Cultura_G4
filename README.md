# Casa de la Cultura

**Sistema de Gestión Bibliotecaria y Recomendación Inteligente**

Proyecto de la asignatura *Proyectos de Software* del Bachelor en Ingeniería Informática de la Universitat Carlemany. Curso 2025-2026, Grupo 4.

## Sobre el proyecto

La Casa de la Cultura es un bibliobús municipal con un fondo amplio de libros y un histórico de usuarios y valoraciones que hasta ahora no se estaba aprovechando. El encargo del cliente (Albert Calvo Ibáñez, en representación del ayuntamiento) consiste en construir un sistema que permita:

- Gestionar el catálogo a partir de los datos depurados del sistema anterior.
- Recomendar libros a los usuarios mediante un motor de asociación entre lectores ("quien leyó X también disfrutó Y").
- Visualizar el uso del fondo y los gustos de los lectores en cuadros de mando.

El sistema debe funcionar de forma local y offline en un único PC en la sede de la Casa de la Cultura, sin dependencias de internet ni licencias de pago.

Más detalle en el [Project Charter](docs/entregables/Project_Charter_Grupo4.pdf) y en el PMP (cuando se entregue).

## Equipo

| Nombre | Rol |
|---|---|
| Bruno Clemente Mora Hernández | Jefe de Proyecto |
| Juan Gabriel Carvajal Franco | Ingeniero de Software (Backend) |
| Adrián Meneses Ramos | Ingeniero de Software (Recomendación) |
| Jose Luis Mus Peñarroja | Ingeniero de Datos |
| Josep Garrido Segues | Apoyo documental y revisión *(pendiente de incorporación)* |
| Miguel Simón Gil Rosas | Apoyo documental y revisión *(pendiente de incorporación)* |

## Stack tecnológico

- **Lenguaje:** Python
- **Framework:** Django
- **Base de datos:** PostgreSQL
- **Control de versiones:** Git + GitHub
- **Metodología:** Ágil (iterativa, con entregables al final de cada fase)

## Estructura del repositorio

```
.
├── README.md
├── .gitignore
└── docs/
    ├── entregables/         # Documentos finales entregados al cliente / asignatura
    │   └── justificantes/   # Justificantes de entrega de Moodle
    └── requisitos/          # Requisitos del cliente y notas relacionadas
```

A medida que avance el proyecto se irán añadiendo `src/` (código de la aplicación), `data/` (datos depurados) y otras carpetas según haga falta.

## Convenciones de trabajo

### Flujo con ramas y Pull Requests

Nadie hace push directo a `main`. Todos los cambios pasan por una rama propia y se integran a `main` mediante Pull Request, con al menos una aprobación de otro miembro del equipo.

Pasos para una tarea:

1. Sincronizar con `main`: `git pull` desde `main`.
2. Crear una rama desde `main`: `git checkout -b <tipo>/<descripcion>`.
3. Trabajar, commits, pruebas.
4. Subir la rama: `git push -u origin <tipo>/<descripcion>`.
5. Abrir un Pull Request en GitHub hacia `main`.
6. Esperar revisión y aprobación de un compañero.
7. Mergear y borrar la rama.

### Nomenclatura de ramas

- `funcionalidad/<descripcion>` — funcionalidades nuevas.
- `correccion/<descripcion>` — corrección de errores.
- `documentacion/<descripcion>` — cambios en documentación.
- `refactorizacion/<descripcion>` — reorganización de código sin cambios funcionales.

Nombres con guiones, sin tildes ni espacios. Ejemplo: `funcionalidad/limpieza-datos-libros`.

### Commits

Mensajes en español, en imperativo y descriptivos. Ejemplos:

- `Añadir script de limpieza de books.csv`
- `Corregir error de codificación al leer user_info.csv`
- `Actualizar README con convenciones de equipo`

## Cómo arrancar el proyecto en local

Pendiente. Se completará cuando esté montado el proyecto Django y la base de datos.

## Documentación del proyecto

- [Project Charter](docs/entregables/Project_Charter_Grupo4.pdf) — versión entregada el 30/04/2026.
- [Requisitos del cliente](docs/requisitos/requisitos_cliente_foro.md) — notas del foro y comunicación con el cliente.
