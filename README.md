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
