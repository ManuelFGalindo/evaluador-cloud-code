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
from fastapi import FastAPI, Form, HTTPException, Request
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


def normalize_azure_endpoint(url: str) -> str:
    """El SDK agrega /chat/completions; quita ese sufijo si viene en la URL."""
    cleaned = (url or "").strip().rstrip("/")
    suffix = "/chat/completions"
    if cleaned.endswith(suffix):
        cleaned = cleaned[: -len(suffix)].rstrip("/")
    return cleaned

CORRECT_ANSWERS = {
    "q1": "cd-claude",
    "q2": "claude-login",
    "q3": "team-login",
    "q4": "claude-md",
    "q5": "curate-context",
    "q6": "plan-mode",
    "q7": "verify",
    "q8": "git-native",
    "q9": "tool-permissions",
    "q10": "hooks",
    "q11": "mcp",
    "q12": "rotate-remove",
}

LEVEL_GROUPS = {
    "Principiante": ["q1", "q2", "q3", "q4"],
    "Intermedio": ["q5", "q6", "q7", "q8"],
    "Avanzado": ["q9", "q10", "q11", "q12"],
}

SYSTEM_PROMPT = """
Eres un Evaluador Senior de Claude Code (Anthropic), según https://code.claude.com/docs/
No confundas Claude Code con Google Cloud Code.

La evaluación va por niveles:
- Principiante (q1-q4): instalar/arrancar `claude`, login, Teams, CLAUDE.md y /init.
- Intermedio (q5-q8): contexto/tokens, plan mode, verificación con tests/build/screenshot, git/PRs.
- Avanzado (q9-q12): permissions vs CLAUDE.md, hooks PreToolUse, MCP, secretos y gitignore de settings.local.json.

Analiza las respuestas y responde ÚNICAMENTE un JSON válido, sin markdown:

{
  "score": 0,
  "level": "Principiante",
  "level_scores": {"Principiante": 0, "Intermedio": 0, "Avanzado": 0},
  "summary": "Resumen ejecutivo en 2-4 oraciones",
  "strengths": ["fortaleza 1", "fortaleza 2"],
  "gaps": ["brecha 1", "brecha 2"],
  "training_plan": [
    {"week": "Semana 1", "topic": "Tema", "desc": "Detalle accionable"}
  ]
}

Reglas:
- score entero 0-100.
- level: Principiante / Intermedio / Avanzado (usa Principiante <50, Intermedio 50-79, Avanzado >=80).
- training_plan: 3 semanas, una por nivel, citando páginas de code.claude.com/docs.
- Español, tono profesional.
"""

app = FastAPI(title="Evaluador Claude Code")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def get_azure_client() -> Optional[ChatCompletionsClient]:
    if not AZURE_ENDPOINT or not AZURE_KEY or "tu-key" in AZURE_KEY:
        return None
    return ChatCompletionsClient(
        endpoint=normalize_azure_endpoint(AZURE_ENDPOINT),
        credential=AzureKeyCredential(AZURE_KEY),
    )


def score_levels(answers: dict) -> dict:
    result = {}
    for name, keys in LEVEL_GROUPS.items():
        hits = sum(1 for key in keys if answers.get(key) == CORRECT_ANSWERS[key])
        result[name] = round((hits / len(keys)) * 100)
    return result


def local_score(answers: dict) -> dict:
    level_scores = score_levels(answers)
    points = sum(1 for key, expected in CORRECT_ANSWERS.items() if answers.get(key) == expected)
    score = round((points / len(CORRECT_ANSWERS)) * 100)
    if score >= 80:
        level = "Avanzado"
    elif score >= 50:
        level = "Intermedio"
    else:
        level = "Principiante"
    return {
        "score": score,
        "level": level,
        "level_scores": level_scores,
        "summary": (
            f"El desarrollador obtuvo {score}% y un nivel {level}. "
            f"Principiante {level_scores['Principiante']}%, "
            f"Intermedio {level_scores['Intermedio']}%, "
            f"Avanzado {level_scores['Avanzado']}%."
        ),
        "strengths": ["Completó la evaluación por niveles de Claude Code."],
        "gaps": [
            "Instalación, login y CLAUDE.md (Principiante)",
            "Plan mode, contexto y verificación con tests (Intermedio)",
            "Permisos, hooks, MCP y secretos (Avanzado)",
        ],
        "training_plan": [
            {
                "week": "Semana 1 · Principiante",
                "topic": "Setup y CLAUDE.md",
                "desc": "Instalar CLI, login y /init. https://code.claude.com/docs/en/quickstart",
            },
            {
                "week": "Semana 2 · Intermedio",
                "topic": "Plan mode y verificación",
                "desc": "Contexto, plan mode y tests/screenshots. https://code.claude.com/docs/en/best-practices",
            },
            {
                "week": "Semana 3 · Avanzado",
                "topic": "Permisos, hooks y MCP",
                "desc": "settings.json, hooks y MCP. https://code.claude.com/docs/en/permissions",
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
@app.head("/")
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
    level_scores = score_levels(parsed_answers)
    try:
        report = diagnose_with_azure(dev_name, dev_role, parsed_answers)
    except Exception:
        report = local_score(parsed_answers)
    report["level_scores"] = level_scores

    html = templates.get_template("report_template.html").render(
        developer={"name": dev_name, "role": dev_role},
        report=report,
    )

    fd, pdf_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    try:
        HTML(string=html, base_url=str(BASE_DIR)).write_pdf(pdf_path)
    except Exception as exc:
        cleanup_file(pdf_path)
        raise HTTPException(status_code=500, detail=f"No se pudo generar el PDF: {exc}") from exc

    filename = f"Reporte_ClaudeCode_{dev_name.replace(' ', '_')}.pdf"
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=filename,
        background=BackgroundTask(cleanup_file, pdf_path),
    )
