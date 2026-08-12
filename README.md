# Evaluador Claude Code

Aplicación web en **FastAPI** para evaluar habilidades de desarrolladores Fullstack en **Claude Code** (Anthropic) y asistencia de IA. Genera un diagnóstico con **Azure AI Foundry (GPT-4o)** y descarga un **informe PDF**.

Repositorio: [github.com/ManuelFGalindo/evaluador-cloud-code](https://github.com/ManuelFGalindo/evaluador-cloud-code)

## Flujo

1. Registro del desarrollador (nombre y rol)
2. Cuestionario técnico en 4 módulos
3. Diagnóstico con Azure AI Foundry
4. Generación y descarga del informe PDF

## Módulos de evaluación

- **Setup, instalación y autenticación** — CLI de Claude Code, `ANTHROPIC_API_KEY` / login
- **Gestión de contexto** — `CLAUDE.md`, `.claudeignore`, inclusión de archivos, consumo de tokens
- **Desarrollo Fullstack asistido por IA** — backend, frontend y generación de tests
- **Despliegue local, debugging y seguridad** — permisos Allow/Deny, hooks, detección de secretos

El informe incluye puntaje (%), nivel (Principiante / Intermedio / Avanzado), resumen ejecutivo, brechas de capacitación y una ruta semanal sugerida.

## Estructura

```
evaluador-cloud-code/
├── main.py
├── requirements.txt
├── .env.example
├── static/css/style.css
└── templates/
    ├── index.html
    ├── test.html
    └── report_template.html
```

## Requisitos

- Python 3.12 (en Render se fija con `.python-version`; no uses 3.14)
- Credenciales de Azure AI Foundry (opcional: si no están configuradas, se usa un diagnóstico local)

## Instalación

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

En Linux o macOS:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edita `.env` con tus credenciales:

```env
AZURE_AI_FOUNDRY_ENDPOINT="https://tu-recurso.services.ai.azure.com/models"
AZURE_AI_FOUNDRY_KEY="tu-key"
AZURE_AI_FOUNDRY_MODEL="gpt-4o"
```

## Ejecución

```powershell
uvicorn main:app --reload
```

Abre [http://127.0.0.1:8000](http://127.0.0.1:8000).

## WeasyPrint

La generación de PDF usa WeasyPrint. En **Windows** puede requerir GTK3. En **Linux** (por ejemplo Render) instala las librerías nativas:

```txt
libpango-1.0-0
libpangocairo-1.0-0
libgdk-pixbuf2.0-0
libffi-dev
shared-mime-info
```

## Despliegue en Render

Render elige Python 3.14 por defecto y **pydantic 2.7.4 no compila en 3.14**. Este repo fija **Python 3.12.8**.

1. Conecta este repositorio en [Render](https://render.com)
2. Crea un **Web Service** con runtime Python
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. En Environment agrega:
   - `PYTHON_VERSION` = `3.12.8`
   - `AZURE_AI_FOUNDRY_ENDPOINT`
   - `AZURE_AI_FOUNDRY_KEY`
   - `AZURE_AI_FOUNDRY_MODEL` = `gpt-4o`
6. Redeploy el servicio

WeasyPrint usa el `Aptfile` de la raíz para instalar Pango/Cairo.

No subas el archivo `.env`. Usa `.env.example` como plantilla.
