# Esquema de la base de datos

Diseño del modelo de datos definitivo a partir de los archivos del sistema anterior.
Las decisiones de depuración siguen el criterio del cliente: se descartan los registros
de libros sin ISBN, sin autor o sin fecha de publicación. El campo `sexo` de usuarios
se elimina por indicación expresa del cliente. Se añade el campo `genre` en libros,
autorizado por el cliente, con valor NULL inicial.

## Diagrama entidad-relación

```mermaid
erDiagram
  BOOKS ||--o{ COPIES : "1 a N"
  COPIES ||--o{ RATINGS : "recibe"
  USERS ||--o{ RATINGS : "emite"
  BOOKS {
    integer book_id PK
    text isbn "NOT NULL"
    text title "NOT NULL"
    text original_title "NULL"
    text authors "NOT NULL"
    integer publication_year "NOT NULL"
    text language_code "NULL"
    text image_url "NULL"
    text genre "NULL - campo nuevo"
  }
  COPIES {
    integer copy_id PK
    integer book_id FK
  }
  USERS {
    integer user_id PK
    date fecha_nacimiento "NULL"
    text comentario "preferencias del usuario"
  }
  RATINGS {
    integer user_id PK_FK
    integer copy_id PK_FK
    integer rating "CHECK 1 a 5"
  }
```

## Índices previstos

- `copies(book_id)` — para hacer JOIN entre ratings y books vía copies
- `ratings(copy_id)` — la PK compuesta empieza por user_id, así que copy_id solo necesita índice propio
- `books(genre)` — para filtros en los dashboards cuando el campo esté relleno

## Decisiones pendientes

- Origen del campo `genre`: a definir con el equipo. Opciones: aportado por el cliente,
  enriquecido desde fuente externa (Open Library), o inferido automáticamente.
