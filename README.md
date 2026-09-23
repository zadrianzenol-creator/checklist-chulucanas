# Checklist Electoral · Chulucanas 2026

Aplicación web moderna (dark mode 3D / glassmorphism) para la verificación de los
**locales de votación y mesas de sufragio del distrito de Chulucanas** en las
Elecciones Generales 2026.

Los datos provienen del Excel `LOCALES_Y_MESAS_DISTRITO_CHULUCANAS_OCTUBRE_2026.xlsx`
**(26 locales · 246 mesas · 73 111 electores)** y se cargan automáticamente en la
base de datos al primer arranque.

## Funcionalidades

- **Login** con diseño 3D animado (Three.js), fondo de partículas y glassmorphism.
- **Dashboard** con estadísticas en tiempo real: locales, mesas, electores, avance,
  gráficos (donut y comparativa por local).
- **Locales y Mesas**: listado con buscador y filtro urbano/rural.
- **Checklist por mesa**: cada mesa se marca **VERIFICADA / PENDIENTE / OBSERVADO**
  (con observación opcional). Avance en tiempo real del local y del distrito.
- **Usuarios** (solo admin): creación de cuentas, activar/desactivar y reset de clave.
- **Roles**: `admin` (todo) y `operador` (solo ver y marcar mesas).
- **PWA**: instalable en el celular como app y caché de la interfaz.
- Registro de actividad (logs) de los cambios de estado.

## Arquitectura

```
checklist_chulucanas/
├── app.py                 → factory de la app, login manager, seed, reglas globales
├── config.py              → config (SQLite local / Postgres en producción)
├── database.py            → instancia de SQLAlchemy
├── seed_data.json         → datos generados desde el Excel (26 locales / 246 mesas)
├── requirements.txt       → dependencias
├── Procfile / render.yaml → despliegue en Render
├── database/
│   └── build_seed.py      → script que lee el Excel y genera seed_data.json
├── models/
│   ├── user.py            → User (roles, hash de contraseña)
│   ├── local.py           → Local + Mesa (estado del checklist)
│   └── activity.py        → ActivityLog
├── routes/
│   ├── auth_routes.py     → login, logout, gestión de usuarios
│   └── main_routes.py     → dashboard, locales, detalle, API (estado, stats, ping)
├── services/
│   └── checklist_service.py → lógica de negocio (estados, stats)
├── utils/
│   └── decorators.py      → role_required / admin_required
├── templates/             → base, login, dashboard, locales, detalle, usuarios, errores
└── static/
    ├── css/app.css        → diseño dark 3D / glassmorphism
    ├── js/background.js   → escena 3D (Three.js)
    ├── js/app.js          → interacciones, modales, gráficos (Chart.js)
    └── img/, manifest.json, sw.js → PWA e iconos
```

## Instalación local

```bash
pip install -r requirements.txt
python app.py
```

Accede a `http://localhost:5050`.

> Por defecto usa SQLite en `instance/checklist.db`. Para usar PostgreSQL define la
> variable `DATABASE_URL` antes de arrancar.

### Regenerar los datos desde el Excel

```bash
python database/build_seed.py "<ruta/al/LOCALES_Y_MESAS_DISTRITO_CHULUCANAS_OCTUBRE_2026.xlsx>"
```

## Credenciales iniciales

| Usuario | Contraseña | Rol |
|---------|-----------|-----|
| admin   | admin123  | admin |

> Cambia la contraseña del admin y crea cuentas para tu equipo desde **Usuarios**.

## Despliegue en Render (plan gratis)

El archivo `render.yaml` ya está listo. Pasos:

1. **Base de datos PostgreSQL gratis (persistente)** — se recomienda [Neon](https://neon.tech)
   (o el propio free plan de Render). Crea una base y copia la cadena de conexión,
   p. ej. `postgresql://user:pass@host/dbname`.
2. Crea tu repositorio en GitHub y sube este proyecto.
3. En [Render](https://render.com) → **New → Web Service** y conecta tu repo.
   - Plan: **Free**
   - Build: `pip install -r requirements.txt`
   - Start: `gunicorn app:app --workers 2 --worker-class gthread --threads 4 --timeout 120`
4. En el servicio crea las variables de entorno:
   - `DATABASE_URL` → tu cadena de conexión de Neon/Postgres
   - `SECRET_KEY` → valor aleatorio largo
   - `ADMIN_PASSWORD` → la clave inicial del admin (opcional)
5. Al primer arranque la app conecta la BD, crea las tablas, carga los 26 locales /
   246 mesas desde `seed_data.json` y crea el usuario `admin`.

> En el plan Free, Render duerme el servicio tras 15 min sin tráfico y lo despierta
> con la siguiente visita. Los datos viven en PostgreSQL, por lo que **no se pierden**
> ante reinicios o redeploys (a diferencia de SQLite en el filesystem efímero).

## Notas

- Endpoints públicos: `/ping` (health check) y `/login`.
- El rol `operador` tiene acceso restringido a dashboard, locales, detalle y a la API
  de marcado. No puede administrar usuarios.
- El botón **En línea** del topbar indica conectividad de la página.