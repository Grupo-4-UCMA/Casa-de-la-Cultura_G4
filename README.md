# Casa de la Cultura

**Sistema de Gestión Bibliotecaria y Recomendación Inteligente**

Proyecto de la asignatura *Proyectos de Software* del Bachelor en Ingeniería Informática de la Universitat Carlemany. Curso 2025-2026, Grupo 4.

## Sobre el proyecto

La Casa de la Cultura es un bibliobús municipal con un fondo amplio de libros y un histórico de usuarios y valoraciones que hasta ahora no se estaba aprovechando. El encargo del cliente (Albert Calvo Ibáñez, en representación del ayuntamiento) consiste en construir un sistema que permita:

- Gestionar el catálogo a partir de los datos depurados del sistema anterior.
- Recomendar libros a los usuarios mediante un motor de asociación entre lectores ("quien leyó X también disfrutó Y").
- Visualizar el uso del fondo y los gustos de los lectores en cuadros de mando.

El sistema debe funcionar de forma local y offline en un único PC en la sede de la Casa de la Cultura, sin dependencias de internet ni licencias de pago.


## Equipo

| Nombre | Rol |
|---|---|
| Bruno Clemente Mora Hernández | Jefe de Proyecto |
| Juan Gabriel Carvajal Franco | Ingeniero de Software (Backend) |
| Adrián Meneses Ramos | Ingeniero de Software (Recomendación) |
| Jose Luis Mus Peñarroja | Ingeniero de Datos |

## Stack tecnológico

- **Lenguaje:** Python3
- **Framework:** Django
- **Base de datos:** SQLite
- **Control de versiones:** GitHub
- **Metodología:** AGILE(iterativa, con entregables al final de cada fase)

## Estructura de la aplicacion

Casa-de-la-Cultura_G4/
├── casa_cultura/      # Configuración y recursos de Django
├── app/               # Catálogo, dashboard y recomendación con IA
├── data/              # Datos procesados utilizados por la aplicación
├── manage.py
├── requirements.txt   # Dependencias del proyecto
└── README.md          # Guía de instalación y uso
