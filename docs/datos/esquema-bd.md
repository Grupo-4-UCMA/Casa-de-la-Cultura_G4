# Esquema de la base de datos — Casa de la Cultura

> Última actualización: 10/05/2026
> Basado en el diseño de Juan Gabriel Carvajal, incorporando las decisiones previas del equipo.

---

## Decisiones de diseño

- `isbn`, `title` y `original_publication_year` son NOT NULL — los registros sin estos campos se descartan según indicación expresa del cliente.
- `author` tiene tabla propia con relación N:M a `book` a través de `book_author` — más normalizado que un campo de texto plano.
- `sexo` eliminado de `user` — indicación expresa del cliente y principio de minimización GDPR.
- `comment` se conserva en `user` como campo de preferencias para el motor de recomendación.
- `rating` tiene CHECK entre 1 y 5.
- `genre` tiene tabla propia. El valor inicial de cada libro será NULL hasta que se implemente la clasificación automática (autorizado por el cliente).
- `copy` incluye campo `status` para gestionar la disponibilidad de cada ejemplar.
- `recommendation` almacena las recomendaciones generadas por el motor con su puntuación y el algoritmo usado.
- `book_statistics` y `genre_statistics` precalculan métricas para los dashboards y evitan consultas pesadas en tiempo real.
- `dashboard_snapshot` guarda instantáneas globales del sistema para histórico de uso.

---

## Diagrama ER

```mermaid
erDiagram
    user {
        int id_user PK
        date birth_date
        text comment
        datetime created_at
    }

    author {
        int id_author PK
        varchar name
    }

    genre {
        int id_genre PK
        varchar name
    }

    book {
        int id_book PK
        varchar isbn
        varchar original_title
        varchar title
        int original_publication_year
        varchar language_code
        text image_url
        int id_genre FK
        datetime created_at
    }

    book_author {
        int id_book FK
        int id_author FK
    }

    copy {
        int id_copy PK
        int id_book FK
        varchar status
        datetime created_at
    }

    rating {
        int id_rating PK
        int id_user FK
        int id_copy FK
        int rating
        datetime created_at
    }

    recommendation {
        int id_recommendation PK
        int id_user FK
        int id_book FK
        decimal score
        text reason
        varchar algorithm
        datetime created_at
    }

    book_statistics {
        int id_book_statistics PK
        int id_book FK
        int total_ratings
        decimal average_rating
        int recommendation_count
        datetime last_updated
    }

    genre_statistics {
        int id_genre_statistics PK
        int id_genre FK
        int total_books
        int total_ratings
        decimal average_rating
        datetime last_updated
    }

    dashboard_snapshot {
        int id_snapshot PK
        datetime snapshot_date
        int total_books
        int total_copies
        int total_users
        int total_ratings
        decimal average_rating
    }

    book }o--|| genre : "pertenece a"
    book }o--o{ author : "book_author"
    copy }o--|| book : "es ejemplar de"
    rating }o--|| user : "hace"
    rating }o--|| copy : "sobre"
    recommendation }o--|| user : "para"
    recommendation }o--|| book : "recomienda"
    book_statistics ||--|| book : "estadisticas de"
    genre_statistics ||--|| genre : "estadisticas de"
```

---

## Restricciones importantes

| Tabla | Campo | Restricción |
|-------|-------|-------------|
| book | isbn | NOT NULL |
| book | title | NOT NULL |
| book | original_publication_year | NOT NULL |
| rating | rating | CHECK entre 1 y 5 |
| book_author | id_book + id_author | PK compuesta |

---

## Índices previstos

| Tabla | Campo | Motivo |
|-------|-------|--------|
| copy | id_book | Joins frecuentes con book |
| rating | id_copy | Joins frecuentes con copy |
| rating | id_user | Filtrado por usuario |
| book | id_genre | Filtrado por género |
| book_statistics | id_book | Lookup rápido de métricas |
| genre_statistics | id_genre | Lookup rápido de métricas |
