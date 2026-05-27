# javimendoza.com

Personal landing page. Flask + Jinja2 + CSS plano.

## Desarrollo local

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Abre <http://localhost:5000>.

## Variables de entorno

Copia `.env.example` a `.env` y rellena los valores. Para desarrollo los contadores funcionan con placeholders aunque las claves estén vacías.

## Deploy

Coolify construye la imagen desde el `Dockerfile` y la sirve en `https://javimendoza.com` con HTTPS automático vía Let's Encrypt. Auto-deploy en cada push a `main`.

## Tracker de visitas y clicks

Esta app expone un mini-tracker propio que centraliza las stats de las 3 webs (`javimendoza.com`, `app.javimendoza.com`, `links.javimendoza.com`).

### Endpoints

- `GET /api/track?site=<dominio>&path=<ruta>` — devuelve un pixel 1x1. Lo llaman las otras webs para registrar visita.
- `GET /r/<slug>` — incrementa el contador del slug y redirige a la URL definida en `redirects.json`.
- `GET /stats` — dashboard privado (HTTP basic auth con `STATS_PASSWORD`, usuario cualquiera).

### Integración en las otras webs

En `app.javimendoza.com` y `links.javimendoza.com`, añadir al final del `<body>`:

```html
<img src="https://javimendoza.com/api/track?site=app.javimendoza.com&path=/" alt="" width="1" height="1" style="position:absolute;left:-9999px">
```

Cambiar `site` y `path` según el dominio y página.

En `links.javimendoza.com`, sustituir los `href` directos por `https://javimendoza.com/r/<slug>` y añadir el slug en `redirects.json`.

### Persistencia en Coolify

El SQLite vive en `/app/data/tracker.db`. **En Coolify hay que añadir un Persistent Storage** apuntando a `/app/data` para que sobreviva a redeploys.

Variables de entorno necesarias: `STATS_PASSWORD` (para el dashboard).
