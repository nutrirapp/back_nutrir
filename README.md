# Nutrir - Sistema de Gestión de Comedores

Sistema de gestión para comedores comunitarios. El proyecto se divide en dos partes:

- **Backend**: API REST con Django + PostgreSQL
- **Frontend**: Aplicación web con Next.js + React + TypeScript

---

## Permisos necesarios

> Antes de comenzar, solicitar al encargado del proyecto:
> - **Acceso al repositorio de GitHub** (permisos para hacer push)
> - **Credenciales SSH del servidor** para aplicar cambios en producción

---

## Requisitos previos

| Herramienta | Versión |
|-------------|---------|
| Python | 3.9 (requerida) |
| PostgreSQL + pgAdmin | 13+ |
| Node.js | LTS |
| Git | cualquier versión reciente |

### Instalación de requisitos

<details>
<summary><b>Windows</b></summary>

- Python 3.9: [python.org/downloads](https://www.python.org/downloads/release/python-390/)
- PostgreSQL + pgAdmin: [postgresql.org/download/windows](https://www.postgresql.org/download/windows/)
- Node.js LTS: [nodejs.org](https://nodejs.org/)
- Git: [git-scm.com](https://git-scm.com/download/win)

</details>

<details>
<summary><b>Debian/Ubuntu</b></summary>

```bash
# Python 3.9
sudo apt update
sudo apt install python3.9 python3.9-dev python3.9-venv

# PostgreSQL
sudo apt install postgresql postgresql-contrib

# pgAdmin (opcional, para interfaz gráfica)
curl -fsS https://www.pgadmin.org/static/packages_pgadmin_org.pub | sudo gpg --dearmor -o /usr/share/keyrings/packages-pgadmin-org.gpg
sudo sh -c 'echo "deb [signed-by=/usr/share/keyrings/packages-pgadmin-org.gpg] https://ftp.postgresql.org/pub/pgadmin/pgadmin4/apt/$(lsb_release -cs) pgadmin4 main" > /etc/apt/sources.list.d/pgadmin4.list'
sudo apt update && sudo apt install pgadmin4-desktop

# Node.js LTS
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs

# Git
sudo apt install git
```

</details>

---

## Instalación y ejecución local

### Backend (Django)

#### 1. Crear la base de datos en pgAdmin

1. Abrir pgAdmin.
2. **Si ya tenés un servidor local configurado:** en el panel izquierdo ir a `Servers` → `<nombre del servidor>` → `Databases`, click derecho → **Create Database**, ingresar `nutrir` como nombre.
3. **Si no tenés servidor local creado:** click derecho en `Servers` → **Register Server**. En la pestaña **General** poner un nombre descriptivo y en **Connection** completar:

   | Campo | Valor |
   |-------|-------|
   | Host | `localhost` |
   | Port | `5432` |
   | Username | `postgres` |
   | Password | contraseña de tu instalación local |

   > Si no recordás la contraseña de PostgreSQL, podés resetearla siguiendo este video: https://www.youtube.com/watch?v=vFENJpe6eJU
   >
   > Luego volvé al paso 2.

#### 2. Clonar el repositorio

```bash
git clone <url-del-repositorio>
```

#### 3. Crear archivo `.env`

Dentro de `django_nutrir/django_nutrir/` crear un archivo `.env` con el siguiente contenido:

```env
SECRET_KEY=
DATABASE_NAME=nutrir
DATABASE_USER=postgres
DATABASE_PASS=          # Contraseña de tu base de datos local
DATABASE_PORT=5432
DJANGO_SUPERUSER_USERNAME=
DJANGO_SUPERUSER_EMAIL=
DJANGO_SUPERUSER_PASSWORD=
EMAIL_HOST=
EMAIL_PORT=
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
```

#### 4. Crear y activar entorno virtual

Desde la carpeta `django_nutrir/`:

**Windows:**
```bash
python3.9 -m venv env
.\env\Scripts\activate
```

**Debian/Ubuntu:**
```bash
python3.9 -m venv env
source ./env/bin/activate
```

#### 5. Instalar dependencias

**Windows:**
```bash
pip install wheel
pip install -r requirements.txt
```

> En Windows puede aparecer un error relacionado con **Microsoft Visual C++**. En ese caso instalar [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) y volver a ejecutar los comandos.

**Debian/Ubuntu:**
```bash
sudo apt-get install python3.9-dev
pip install wheel
pip install -r requirements.txt
```

#### 6. Ejecutar migraciones y crear superusuario

```bash
python manage.py migrate
python manage.py createsuperuser
```

> El usuario que crees aquí es el que vas a usar para ingresar al sistema.

#### 7. Cargar datos iniciales

> **Importante:** respetar el orden de los comandos.

**Windows:**
```bash
python manage.py import_provincias --path .\provincia\management\commands\provincias.csv
python manage.py import_departamento --path .\departamento\management\commands\departamentos.csv
python manage.py import_gobiernoLocal --path .\gobierno_local\management\commands\gobiernosLocales.csv
python manage.py import_localidades --path .\localidad\management\commands\localidades.csv
```

**Debian/Ubuntu:**
```bash
python manage.py import_provincias --path ./provincia/management/commands/provincias.csv
python manage.py import_departamento --path ./departamento/management/commands/departamentos.csv
python manage.py import_gobiernoLocal --path ./gobierno_local/management/commands/gobiernosLocales.csv
python manage.py import_localidades --path ./localidad/management/commands/localidades.csv
```

#### 8. Iniciar el servidor

```bash
python manage.py runserver
```

El backend estará disponible en http://127.0.0.1:8000/admin. Ingresar con el usuario creado en el paso 6.

---

### Frontend (Next.js)

#### 1. Pre-requisito

Completar los pasos del backend **hasta el paso 6 incluido** y dejar el servidor corriendo en una terminal.

#### 2. Ingresar a la carpeta del frontend

```bash
cd front_nutrir
```

#### 3. Crear archivo `.env`

En la raíz de `front_nutrir/` crear un archivo `.env`:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/
NEXT_PUBLIC_COMEDOR=
NEXT_PUBLIC_API_COMEDORES_GET_ALL=
```

#### 4. Instalar dependencias e iniciar

```bash
npm install
npm run dev
```

El frontend estará disponible en http://localhost:3000. Al ingresar serás redirigido a la pantalla de login; usar el usuario creado en el paso 6 del backend.

---

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.9 + Django 4.1 + Django REST Framework |
| Base de datos | PostgreSQL |
| Frontend | TypeScript + React 18 + Next.js 12 |
| UI | Material UI (MUI) |
| Autenticación | JWT (djangorestframework-simplejwt) |
| Comunicación | API REST |

**Referencias útiles:**
- Patrón MVT de Django: https://www.youtube.com/watch?v=cyP4Uw2b2XM
- Componentes de Material UI: https://mui.com/material-ui/all-components/
- Introducción a REST API: https://www.youtube.com/watch?v=lsMQRaeKNDk

---

## Flujo de trabajo con Git (Git Flow)

### Estructura de ramas

| Rama | Descripción |
|------|-------------|
| `main` | Código final y estable. Solo se actualiza con código revisado y aprobado. |
| `developer` | Rama de integración. De acá salen las ramas de cada tarea. |
| `<nombre-tarea>` | Rama individual por tarea. Se hace PR hacia `dev` al terminar. |

### Flujo para trabajar en una tarea

```bash
# 1. Asegurarse de tener developer actualizado
git checkout developer
git pull origin developer

# 2. Crear la rama de la tarea a partir de developer
git checkout -b nombre-tarea

# 3. Trabajar y commitear los cambios
git add <archivos>
git commit -m "feat: descripcion del cambio"

# 4. Subir la rama al repositorio remoto
git push origin nombre-tarea

# 5. Abrir un Pull Request hacia `developer` en GitHub para revisión
```

> Nunca se pushea directamente a `main` ni a `developer`. Todo cambio entra mediante Pull Request.

### Convenciones de commits

```
feat:     nueva funcionalidad
fix:      corrección de un bug
refactor: cambio de código sin modificar comportamiento
docs:     cambios en documentación
style:    cambios de formato o estilo (sin lógica)
```

---

## Deployment en servidor

> Las credenciales SSH del servidor de producción deben **solicitarse al encargado del proyecto**.

Para la guía completa de deployment con Gunicorn + Nginx + systemd ver [README_DEPLOYMENT.md](django_nutrir/README_DEPLOYMENT.md).

---

> Este instructivo es una guía recomendada. Podés configurar el entorno de la forma que prefieras siempre que se respeten los requisitos de versión.
