# Semáforo Eléctrico

Aplicación para consultar el precio de la electricidad en España en tiempo real
mediante un **semáforo de colores**, además de una **API REST** y capacidad de
instalarse como **app en tu móvil Android (PWA)**.

- 🟢 **Verde**: menos de 0,10 €/kWh (barato)
- 🟡 **Amarillo**: entre 0,10 y 0,20 €/kWh (normal)
- 🔴 **Rojo**: 0,20 €/kWh o más (caro)

---

## ✨ Novedades de esta versión

- **PWA instalable**: abre la web en Chrome del móvil y pulsa "Añadir a pantalla
  de inicio". Se comporta como una app nativa (icono, pantalla completa, offline básico).
- **Configuración por entorno** (`.env`) en lugar de valores fijos en el código.
- **Base de datos flexible**: SQLite para desarrollo rápido o PostgreSQL en producción.
- **Listo para la nube**: `Procfile`, `render.yaml`, `build.sh` y `gunicorn`.
- **Corregido el capturador de precios de OMIE**: ahora interpreta correctamente
  los precios **cuarto-horarios** (96 valores/día = 24 horas reales).
- Dependencias actualizadas y ajustes de seguridad para producción.

---

## 🚀 Puesta en marcha (desarrollo local)

### 1. Requisitos
- Python 3.12+
- (Opcional) Docker, si quieres usar PostgreSQL en local

### 2. Crear entorno virtual e instalar dependencias

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # Windows PowerShell
# source .venv/bin/activate         # Linux/macOS
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

Copia la plantilla y ajusta si es necesario:

```powershell
Copy-Item .env.example .env
```

Por defecto el `.env` de ejemplo local usa **SQLite** (`USE_SQLITE=True`), por lo
que **no necesitas base de datos** para empezar.

> Para usar **PostgreSQL** con Docker: pon `USE_SQLITE=False` y ejecuta
> `docker compose up -d` (levanta un PostgreSQL en `localhost:5432`).

### 4. Preparar la base de datos

```powershell
python manage.py migrate
```

### 5. Crear un usuario (para entrar en la web)

```powershell
python manage.py createsuperuser
```

### 6. Capturar los precios del día

```powershell
python manage.py fetch_prices
```

### 7. Arrancar el servidor

```powershell
python manage.py runserver
```

Abre **http://127.0.0.1:8000/** en el navegador.

---

## 📱 Instalar la app en tu móvil Android (PWA)

La PWA necesita que el backend sea accesible desde el móvil. Tienes dos opciones:

### Opción A — Despliegue en la nube (recomendado)

1. Sube el proyecto a GitHub.
2. Entra en [Render](https://render.com) → **New → Blueprint** y conecta el repo.
   Se usará `render.yaml` para crear el servicio web y la base de datos.
3. En el panel de Render, define las variables:
   - `DJANGO_ALLOWED_HOSTS` = `tu-app.onrender.com`
   - `DJANGO_CSRF_TRUSTED_ORIGINS` = `https://tu-app.onrender.com`
4. Cuando termine el despliegue, abre la URL en **Chrome (Android)**.
5. Menú (⋮) → **"Añadir a pantalla de inicio"** / **"Instalar aplicación"**.
6. Ya tienes el icono en tu móvil. 🎉

### 🔄 Actualización automática de precios (GRATIS)

El backend expone un endpoint protegido por token que ejecuta la captura de
precios de OMIE:

```
GET /tasks/refresh-prices/   (cabecera: X-Cron-Token: TU_TOKEN  o  ?token=TU_TOKEN)
```

Puedes llamarlo cada día desde cualquiera de estas opciones **sin coste**:

| Opción | Coste | Cómo |
|--------|-------|------|
| **GitHub Actions** (incluido) | Gratis | Workflow `.github/workflows/refresh-prices.yml` |
| **cron-job.org** | Gratis | Servicio externo que hace ping a tu URL |
| **Tu PC** (Programador de tareas) | Gratis | Solo si el PC está encendido a esa hora |
| Render *Cron Job* | De pago | No está incluido en el plan free |

**Con GitHub Actions (ya incluido en el repo):**

1. En GitHub → **Settings → Secrets and variables → Actions → New repository secret**:
   - `APP_URL` = `https://tu-app.onrender.com`
   - `CRON_SECRET_TOKEN` = el mismo token configurado en Render.
2. El workflow se ejecutará a las **13:10 UTC** cada día (y también puedes
   lanzarlo a mano desde la pestaña **Actions**).

> `CRON_SECRET_TOKEN`: en Render se genera automáticamente (`render.yaml`).
> En local se define en el `.env`. Genéralo con:
> `python -c "import secrets; print(secrets.token_urlsafe(32))"`

### Opción B — Solo en tu PC y la misma WiFi

1. Averigua la IP local de tu PC (`ipconfig` → *Dirección IPv4*, ej. `192.168.1.50`).
2. En el `.env` añade:
   ```
   DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.50
   ```
3. Arranca el servidor accesible en la red:
   ```powershell
   python manage.py runserver 0.0.0.0:8000
   ```
4. En el móvil (misma WiFi) abre `http://192.168.1.50:8000/` e instálala como PWA.

> ⚠️ En esta opción la instalación de la PWA puede no ofrecerse porque Chrome
> exige **HTTPS** para instalarla (salvo en `localhost`). Para la experiencia
> completa usa la Opción A (la nube te da HTTPS gratis).

---

## 🔌 API REST

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/electricity/api/current/` | Precio de la hora actual |
| GET | `/electricity/api/daily/` | Precios del día (`?date=YYYY-MM-DD` opcional) |
| GET | `/health/` | Estado del servicio (para despliegue) |
| GET | `/tasks/refresh-prices/` | Refresca precios (protegido por `X-Cron-Token`) |

Ejemplo de respuesta:

```json
{"date": "2026-10-12", "hour": 17, "price": "0.19740", "status": "yellow"}
```

---

## 🗂️ Estructura del proyecto

```
semaforo_electrico/
├── semaforo_electrico_project/   # Configuración Django (settings, urls, wsgi, pwa_views)
├── users/                        # Autenticación (login, registro, reset)
├── electricity_prices/           # Modelo, API y comando fetch_prices
│   └── management/commands/fetch_prices.py
├── templates/                    # Plantillas HTML (base, home, semáforo, auth)
├── static/                       # PWA: manifest.json, sw.js, icons/
├── requirements.txt              # Dependencias
├── .env.example                  # Plantilla de variables de entorno
├── build.sh / Procfile / render.yaml  # Despliegue
└── docker-compose.yml            # PostgreSQL local
```

---

## 🔐 Resumen de variables de entorno

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `DJANGO_SECRET_KEY` | Clave secreta de Django | *(única y secreta)* |
| `DJANGO_DEBUG` | Modo depuración | `True` / `False` |
| `DJANGO_ALLOWED_HOSTS` | Hosts permitidos (coma) | `miapp.onrender.com` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Orígenes CSRF (coma) | `https://miapp.onrender.com` |
| `USE_SQLITE` | Usar SQLite en vez de PostgreSQL | `True` / `False` |
| `DATABASE_URL` | Cadena de conexión PostgreSQL | `postgres://user:pass@host:5432/db` |
| `EMAIL_BACKEND` | Backend de correo | `...console.EmailBackend` |
| `CRON_SECRET_TOKEN` | Token que protege `/tasks/refresh-prices/` | *(cadena aleatoria)* |

---

## Licencia

Este proyecto está bajo una licencia de uso educativo y no comercial.

Puedes utilizar, modificar y distribuir este software para fines personales o
educativos, siempre y cuando no sea para beneficio comercial directo.

## Atribución

Si utilizas este proyecto para cualquier propósito (personal, educativo,
demostración, etc.), te pido que atribuyas el reconocimiento a su creador:

**Paco López Alarte** (spanocrypt@gmail.com)

Agradezco tu comprensión y respeto por los términos de uso.
