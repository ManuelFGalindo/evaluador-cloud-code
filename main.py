import json
import os
import re
import tempfile
from pathlib import Path
from typing import Optional

from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.background import BackgroundTask
from weasyprint import HTML

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
AZURE_ENDPOINT = os.getenv("AZURE_AI_FOUNDRY_ENDPOINT", "")
AZURE_KEY = os.getenv("AZURE_AI_FOUNDRY_KEY", "")
AZURE_MODEL = os.getenv("AZURE_AI_FOUNDRY_MODEL", "gpt-4o")

CORRECT_ANSWERS = {
    "q1": "env-secret",
    "q2": "claude-login",
    "q4": "ignore-noise",
    "q5": "curate-context",
    "q6": "spec-first",
    "q7": "design-system",
    "q9": "tool-permissions",
    "q10": "rotate-remove",
}

SYSTEM_PROMPT = """
Eres un Evaluador Senior de Claude Code (Anthropic) y asistencia de IA en desarrollo Fullstack.
No confundas Claude Code con Google Cloud Code.
Analiza las respuestas del desarrollador y responde ÚNICAMENTE un JSON válido, sin markdown, con esta forma:

{
  "score": 0,
  "level": "Principiante",
  "summary": "Resumen ejecutivo en 2-4 oraciones",
  "strengths": ["fortaleza 1", "fortaleza 2"],
  "gaps": ["brecha 1", "brecha 2"],
  "training_plan": [
    {"week": "Semana 1", "topic": "Tema", "desc": "Detalle accionable"}
  ]
}

Reglas:
- score es un entero 0-100.
- level debe ser exactamente: Principiante, Intermedio o Avanzado.
- Usa Principiante si score < 50, Intermedio si 50-79, Avanzado si >= 80.
- training_plan debe tener 4 semanas, una por módulo: autenticación Claude Code, contexto (CLAUDE.md / .claudeignore / tokens), fullstack+tests, permisos/hooks/secretos.
- Escribe todo en español, tono profesional y concreto.
"""

app = FastAPI(title="Evaluador Claude Code")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def get_azure_client() -> Optional[ChatCompletionsClient]:
    if not AZURE_ENDPOINT or not AZURE_KEY or "tu-key" in AZURE_KEY:
        return None
    return ChatCompletionsClient(
        endpoint=AZURE_ENDPOINT,
        credential=AzureKeyCredential(AZURE_KEY),
    )


def local_score(answers: dict) -> dict:
    points = 0.0
    total = 10.0
    for key, expected in CORRECT_ANSWERS.items():
        points += 1 if answers.get(key) == expected else 0
    for key in ("q3", "q8"):
        points += int(answers.get(key, "1")) / 5
    score = round((points / total) * 100)
    if score >= 80:
        level = "Avanzado"
    elif score >= 50:
        level = "Intermedio"
    else:
        level = "Principiante"
    return {
        "score": score,
        "level": level,
        "summary": (
            f"El desarrollador obtuvo {score}% y un nivel {level}. "
            "El diagnóstico local se usó porque Azure AI Foundry no estaba disponible. "
            "Revisa autenticación, contexto, generación de tests y secretos."
        ),
        "strengths": ["Completó la evaluación de los 4 módulos de Claude Code."],
        "gaps": [
            "Autenticación con ANTHROPIC_API_KEY o login de Claude Code",
            "Curado de contexto, CLAUDE.md y .claudeignore",
            "Generación de tests con Claude Code",
            "Permisos Allow/Deny, hooks y rotación de secretos",
        ],
        "training_plan": [
            {
                "week": "Semana 1",
                "topic": "Setup y autenticación",
                "desc": "Instalar la CLI de Claude Code y practicar login o ANTHROPIC_API_KEY en un secret manager.",
            },
            {
                "week": "Semana 2",
                "topic": "Gestión de contexto",
                "desc": "Diseñar CLAUDE.md y .claudeignore, y medir consumo de tokens al incluir archivos.",
            },
            {
                "week": "Semana 3",
                "topic": "Fullstack asistido",
                "desc": "Generar un endpoint + UI + tests a partir de un contrato claro, revisando cada diff.",
            },
            {
                "week": "Semana 4",
                "topic": "Permisos y seguridad",
                "desc": "Configurar Allow/Deny y hooks, y un flujo de detección/rotación de secretos.",
            },
        ],
    }


def parse_model_json(raw: str) -> dict:
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    return json.loads(text)


def diagnose_with_azure(dev_name: str, dev_role: str, answers: dict) -> dict:
    client = get_azure_client()
    if client is None:
        return local_score(answers)

    response = client.complete(
        messages=[
            SystemMessage(content=SYSTEM_PROMPT),
            UserMessage(
                content=(
                    f"Desarrollador: {dev_name}\n"
                    f"Rol: {dev_role}\n"
                    f"Respuestas: {json.dumps(answers, ensure_ascii=False)}"
                )
            ),
        ],
        model=AZURE_MODEL,
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    return parse_model_json(response.choices[0].message.content)


def cleanup_file(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/start-eval", response_class=HTMLResponse)
async def start_eval(
    request: Request,
    dev_name: str = Form(...),
    dev_role: str = Form(...),
):
    return templates.TemplateResponse(
        "test.html",
        {"request": request, "dev_name": dev_name, "dev_role": dev_role},
    )


@app.post("/generate-report")
async def generate_report(
    dev_name: str = Form(...),
    dev_role: str = Form(...),
    answers: str = Form(...),
):
    parsed_answers = json.loads(answers)
    try:
        report = diagnose_with_azure(dev_name, dev_role, parsed_answers)
    except Exception:
        report = local_score(parsed_answers)

    html = templates.get_template("report_template.html").render(
        developer={"name": dev_name, "role": dev_role},
        report=report,
    )

    fd, pdf_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    HTML(string=html, base_url=str(BASE_DIR)).write_pdf(pdf_path)

    filename = f"Reporte_ClaudeCode_{dev_name.replace(' ', '_')}.pdf"
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=filename,
        background=BackgroundTask(cleanup_file, pdf_path),
    )
