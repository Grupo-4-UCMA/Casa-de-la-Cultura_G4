# Guía de flujo de trabajo en GitHub

Esta guía explica cómo trabajar en el repositorio del proyecto **Casa de la Cultura**. Está pensada para que cualquier miembro del equipo pueda seguirla, tenga o no experiencia previa con Git y GitHub.

> Si te encuentras con algo que no entiendes o un error que no sale aquí, pregunta en el grupo antes de improvisar. Es más fácil resolverlo entre todos que arreglar después un destrozo en el repo.

---

## 1. Antes de empezar (solo la primera vez)

### 1.1 Instalar Git

- **Windows:** descarga e instala desde [git-scm.com](https://git-scm.com/download/win). Acepta las opciones por defecto.
- **macOS:** abre la Terminal y escribe `git --version`. Si no lo tienes, te ofrecerá instalarlo.
- **Linux:** `sudo apt install git` (Ubuntu/Debian) o el equivalente de tu distribución.

Comprueba que está instalado:

```bash
git --version
```

Debe mostrarte algo como `git version 2.x.x`.

### 1.2 Configurar tu identidad

Esto es importante: **el email tiene que ser el mismo que usas en GitHub**, si no, tus commits no aparecerán como tuyos.

```bash
git config --global user.name "Tu Nombre"
git config --global user.email "tu_email@ejemplo.com"
```

### 1.3 Clonar el repositorio

Decide en qué carpeta de tu ordenador quieres tener el proyecto. Por ejemplo:

```bash
cd ~/Proyectos
git clone https://github.com/Grupo-4-UCMA/Casa-de-la-Cultura_G4.git
cd Casa-de-la-Cultura_G4
```

A partir de aquí, ya tienes el proyecto en tu equipo.

---

## 2. El flujo de cada tarea

Cada vez que vayas a trabajar en algo, sigue estos pasos:

1. **Asegúrate de estar en `main` y al día.**
2. **Crea una rama nueva** para tu tarea.
3. **Trabaja:** edita archivos, haz commits.
4. **Sube tu rama** a GitHub.
5. **Abre un Pull Request (PR)** desde la web de GitHub.
6. **Espera revisión y aprobación** de un compañero.
7. **Mergea el PR** y borra la rama.

Importante: **nunca hagas `git push` directo a `main`**. La rama está protegida y te lo va a rechazar. Todo cambio pasa por una rama propia y un PR.

---

## 3. Comandos que vas a usar el 95% del tiempo

### Empezar una tarea nueva

```bash
git checkout main
git pull
git checkout -b funcionalidad/lo-que-vas-a-hacer
```

Tipos de prefijo según lo que hagas:

- `funcionalidad/...` — funcionalidades nuevas.
- `correccion/...` — corrección de errores.
- `documentacion/...` — cambios en documentación.
- `refactorizacion/...` — reorganizar código sin cambiar comportamiento.

Sin tildes, sin espacios, en minúsculas, separa palabras con guiones.

### Guardar tus cambios

```bash
git status               # Ver qué archivos has cambiado
git add <archivo>        # Marcar un archivo concreto para commit
git add .                # Marcar TODOS los cambios para commit
git commit -m "Mensaje claro y en imperativo"
```

Mensajes de commit: **en español, en imperativo, descriptivos.** Ejemplos:

- ✅ `Añadir script de carga de libros`
- ✅ `Corregir error al leer user_info.csv`
- ❌ `cambios` (no dice nada)
- ❌ `He arreglado el bug` (no es imperativo)

### Subir tu rama a GitHub

La primera vez:

```bash
git push -u origin funcionalidad/lo-que-vas-a-hacer
```

Después, basta con:

```bash
git push
```

### Volver a `main` cuando termines

Cuando tu PR ya esté mergeado:

```bash
git checkout main
git pull
git branch -d funcionalidad/lo-que-vas-a-hacer   # Borra la rama local
```

---

## 4. Cómo abrir un Pull Request (PR)

Después de hacer `git push -u origin tu-rama`, GitHub te muestra una URL en la terminal. Pínchala (o abre el repo en GitHub y verás un banner amarillo proponiéndote crear el PR).

En la pantalla de "Open a pull request":

1. **Título:** corto y descriptivo. Por ejemplo: *"Añadir script de limpieza de books.csv"*.
2. **Descripción:** explica brevemente:
   - **Qué cambia:** los cambios principales.
   - **Por qué:** el motivo.
   - **Notas:** cualquier cosa que el revisor deba tener en cuenta.
3. **Reviewers (panel derecho):** asigna a 1 o 2 compañeros para que lo revisen.
4. **Assignees:** ponte a ti mismo.
5. Botón **"Create pull request"**.

Después de crearlo, **avisa por WhatsApp** a los revisores para que lo vean (la notificación de GitHub a veces se pierde).

---

## 5. Cómo revisar el PR de un compañero

Cuando alguien te ponga como revisor, recibirás una notificación. Para revisar:

1. Entra al PR desde GitHub.
2. Pestaña **"Files changed"**: ahí ves todos los cambios línea a línea.
3. Lee con atención. Si ves algo:
   - **Para comentar una línea:** pasa el ratón por encima del número de línea, sale un `+`, púlsalo y escribe tu comentario.
   - **Para comentar el PR en general:** pestaña "Conversation", escribes abajo.
4. Cuando termines de revisar, botón verde **"Review changes"** (arriba a la derecha en "Files changed"):
   - **Comment:** dejas comentarios pero ni apruebas ni rechazas.
   - **Approve:** lo apruebas, listo para mergear.
   - **Request changes:** pides cambios. El autor tendrá que arreglarlo antes de poder mergear.

Una sola aprobación es suficiente para que el PR pueda mergearse. **Sé constructivo y específico** en los comentarios: en vez de *"esto está mal"*, mejor *"creo que aquí habría que validar que el ISBN no sea nulo, si no, el script peta con los registros incompletos del CSV"*.

---

## 6. Errores comunes y cómo solucionarlos

### "Tengo cambios sin commitear y necesito cambiar de rama"

```bash
git stash            # Guarda los cambios temporalmente
git checkout otra-rama
# ...haces lo que tengas que hacer...
git checkout tu-rama
git stash pop        # Recupera los cambios
```

### "Mi rama está desactualizada respecto a main"

Mientras trabajabas, alguien mergeó cambios a `main` y tu rama ha quedado atrás. Para actualizarla:

```bash
git checkout main
git pull
git checkout tu-rama
git merge main
```

Si hay conflictos, Git te lo dirá. Abre los archivos marcados, busca las marcas `<<<<<<<` y `=======` y `>>>>>>>`, decide qué versión dejar, guarda, y haz `git add` + `git commit`.

### "Se me ha olvidado y he hecho cambios directamente en main"

Si **aún no has commiteado**:

```bash
git stash
git checkout -b tu-rama-nueva
git stash pop
```

Y sigues normal desde ahí. Si **ya has commiteado en main local** (no pasa nada porque el push estará bloqueado), háblalo en el grupo, hay solución pero conviene hacerla con cuidado.

### "Git me pide credenciales y mi contraseña no funciona"

GitHub ya no acepta contraseñas para Git. Tienes dos opciones:

- **GitHub CLI:** instala `gh` y ejecuta `gh auth login`. Es lo más cómodo.
- **Personal Access Token (PAT):** crea uno desde GitHub (Settings → Developer settings → Personal access tokens), y úsalo como contraseña cuando Git la pida.

### "He pusheado algo que no debía"

No entres en pánico, no borres nada, **escribe en el grupo**. Casi todo en Git tiene arreglo, pero mejor parar y hablarlo antes de empeorarlo intentando arreglarlo solo.

---

## 7. Resumen rápido

```bash
# Empezar tarea
git checkout main
git pull
git checkout -b funcionalidad/mi-tarea

# Trabajar y guardar
git add .
git commit -m "Hacer X"

# Subir y crear PR
git push -u origin funcionalidad/mi-tarea
# (luego ir a GitHub y crear el PR)

# Cuando esté mergeado
git checkout main
git pull
git branch -d funcionalidad/mi-tarea
```

---

*Si encuentras algún error en esta guía o crees que falta algo, abre un PR para corregirla. La documentación también es código.*
