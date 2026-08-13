import json
import os
import re
import tempfile
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from openai import OpenAI
from starlette.background import BackgroundTask
from starlette.middleware.sessions import SessionMiddleware
from weasyprint import HTML

from docs_digest import DOCS_DIGEST
from question_bank import randomize_option_letters, sample_fallback_quiz

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
AZURE_ENDPOINT = os.getenv("AZURE_AI_FOUNDRY_ENDPOINT", "")
AZURE_KEY = os.getenv("AZURE_AI_FOUNDRY_KEY", "")
AZURE_MODEL = os.getenv("AZURE_AI_FOUNDRY_MODEL", "gpt-5.1")
SESSION_SECRET = os.getenv("SESSION_SECRET", "evaluador-claude-code-cambia-esto")

LEVEL_ORDER = ("Principiante", "Intermedio", "Avanzado")
QUESTIONS_PER_LEVEL = 8
QUIZ_SIZE = QUESTIONS_PER_LEVEL * len(LEVEL_ORDER)
LEVEL_META = {
    "Principiante": {
        "title": "Instalación, login y memoria del proyecto",
        "blurb": "Quickstart, autenticación y CLAUDE.md.",
        "css": "level-1",
        "badge": "badge-1",
    },
    "Intermedio": {
        "title": "Contexto, plan mode y verificación",
        "blurb": "Best practices: explorar, planear y comprobar el trabajo.",
        "css": "level-2",
        "badge": "badge-2",
    },
    "Avanzado": {
        "title": "Permisos, hooks, MCP y seguridad",
        "blurb": "settings.json, hooks, MCP, skills y secretos.",
        "css": "level-3",
        "badge": "badge-3",
    },
}

QUIZ_PROMPT = f"""
Eres un examinador de Claude Code (Anthropic). Usa SOLO estos hechos oficiales.
No inventes URLs ni confundas Claude Code con Google Cloud Code.

{DOCS_DIGEST}

Genera un examen NUEVO de {QUIZ_SIZE} preguntas de opción múltiple (4 opciones, 1 correcta).
{QUESTIONS_PER_LEVEL} Principiante, {QUESTIONS_PER_LEVEL} Intermedio, {QUESTIONS_PER_LEVEL} Avanzado.
Escenarios reales, no triviales. Dimensionado para resolverlo en 45 minutos.
La letra correcta DEBE variar: no pongas todas en "a". Mezcla a, b, c y d.

Responde SOLO JSON:
{{
  "questions": [
    {{
      "id": "q1",
      "level": "Principiante",
      "prompt": "pregunta",
      "options": [{{"id": "a", "text": "..."}}, {{"id": "b", "text": "..."}}, {{"id": "c", "text": "..."}}, {{"id": "d", "text": "..."}}],
      "correct": "c"
    }}
  ]
}}
ids q1..q{QUIZ_SIZE}. correct = id de la opción correcta. Español.
"""

REPORT_PROMPT = """
Eres un Evaluador Senior de Claude Code según https://code.claude.com/docs/
Te pasan el puntaje OBJETIVO ya calculado. NO lo cambies: copia score, level y level_scores tal cual.

Escribe el diagnóstico cualitativo (resumen, fortalezas, brechas, plan) alineado a esos números.
Si el score es alto, no digas que el desempeño es superficial. Si es bajo, no inventes que dominó todo.

Responde SOLO JSON:
{
  "score": 0,
  "level": "Principiante",
  "level_scores": {"Principiante": 0, "Intermedio": 0, "Avanzado": 0},
  "summary": "2-4 oraciones",
  "strengths": ["..."],
  "gaps": ["..."],
  "training_plan": [{"topic": "...", "desc": "... enlace code.claude.com/docs ..."}]
}
Español, profesional. Capacitación: 3 a 5 ítems con SOLO tema y detalle.
NO indiques semanas, días, horas ni duración. El detalle debe decir qué estudiar y el enlace, no cuándo.
"""


def normalize_azure_endpoint(url: str) -> str:
    cleaned = (url or "").strip().rstrip("/")
    if cleaned.endswith("/chat/completions"):
        cleaned = cleaned[: -len("/chat/completions")].rstrip("/")
    parsed = urlparse(cleaned)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}/openai/v1"
    return cleaned


app = FastAPI(title="Evaluador Claude Code")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def get_azure_client() -> Optional[OpenAI]:
    if not AZURE_ENDPOINT or not AZURE_KEY or "tu-key" in AZURE_KEY:
        return None
    return OpenAI(
        base_url=normalize_azure_endpoint(AZURE_ENDPOINT),
        api_key=AZURE_KEY,
    )


def parse_model_json(raw: str) -> dict:
    text = (raw or "").strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    return json.loads(text)


def extract_responses_text(response) -> str:
    text = getattr(response, "output_text", None)
    if text:
        return text
    chunks = []
    for item in getattr(response, "output", None) or []:
        for content in getattr(item, "content", None) or []:
            piece = getattr(content, "text", None)
            if piece:
                chunks.append(piece)
    if chunks:
        return "\n".join(chunks)
    return str(response)


def azure_json(system_prompt: str, user_content: str) -> dict:
    client = get_azure_client()
    if client is None:
        raise RuntimeError("Azure no configurado")
    try:
        response = client.chat.completions.create(
            model=AZURE_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            temperature=0.8,
        )
        raw = response.choices[0].message.content or ""
    except Exception:
        response = client.responses.create(
            model=AZURE_MODEL,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )
        raw = extract_responses_text(response)
    return parse_model_json(raw)


def validate_quiz(payload: dict) -> list[dict]:
    questions = payload.get("questions") or []
    cleaned = []
    for item in questions:
        options = item.get("options") or []
        if len(options) != 4:
            continue
        correct = str(item.get("correct", "")).strip()
        option_ids = {str(opt.get("id")) for opt in options}
        if correct not in option_ids:
            continue
        prompt = str(item.get("prompt", "")).strip()
        if not prompt:
            continue
        fallback_level = LEVEL_ORDER[min(len(cleaned) // QUESTIONS_PER_LEVEL, len(LEVEL_ORDER) - 1)]
        cleaned.append(
            {
                "id": f"q{len(cleaned) + 1}",
                "level": item.get("level") if item.get("level") in LEVEL_ORDER else fallback_level,
                "prompt": prompt,
                "options": [
                    {"id": str(opt.get("id")), "text": str(opt.get("text", "")).strip()}
                    for opt in options
                ],
                "correct": correct,
            }
        )
    if not cleaned:
        raise ValueError(f"Se esperaban preguntas válidas (objetivo {QUIZ_SIZE})")
    return cleaned


def fill_quiz_from_bank(partial: list[dict]) -> list[dict]:
    """Completa hasta 8 preguntas por nivel con el banco oficial."""
    by_level = {level: [] for level in LEVEL_ORDER}
    seen = set()
    for item in partial:
        level = item.get("level")
        prompt = item.get("prompt", "")
        if level not in LEVEL_ORDER or prompt in seen:
            continue
        if len(by_level[level]) >= QUESTIONS_PER_LEVEL:
            continue
        seen.add(prompt)
        by_level[level].append(item)

    for item in sample_fallback_quiz(QUESTIONS_PER_LEVEL):
        level = item["level"]
        if item["prompt"] in seen:
            continue
        if len(by_level[level]) >= QUESTIONS_PER_LEVEL:
            continue
        seen.add(item["prompt"])
        by_level[level].append(item)

    merged = []
    for level in LEVEL_ORDER:
        merged.extend(by_level[level][:QUESTIONS_PER_LEVEL])
    for index, item in enumerate(merged, start=1):
        item["id"] = f"q{index}"
    return merged


def build_quiz() -> list[dict]:
    quiz: list[dict] = []
    try:
        data = azure_json(
            QUIZ_PROMPT,
            "Genera un set distinto. Varía escenarios (Windows vs macOS, monorepo, CI, UI, secretos, hooks).",
        )
        quiz = validate_quiz(data)
    except Exception:
        quiz = []
    quiz = fill_quiz_from_bank(quiz)
    return [randomize_option_letters(item) for item in quiz]


def group_questions(quiz: list[dict]) -> list[dict]:
    sections = []
    for level in LEVEL_ORDER:
        meta = LEVEL_META[level]
        sections.append(
            {
                "level": level,
                "title": meta["title"],
                "blurb": meta["blurb"],
                "css": meta["css"],
                "badge": meta["badge"],
                "questions": [q for q in quiz if q["level"] == level],
            }
        )
    return sections


def score_quiz(quiz: list[dict], answers: dict) -> dict:
    by_level = {level: {"hits": 0, "total": 0} for level in LEVEL_ORDER}
    details = []
    for item in quiz:
        chosen = answers.get(item["id"], "")
        ok = chosen == item["correct"]
        by_level[item["level"]]["total"] += 1
        if ok:
            by_level[item["level"]]["hits"] += 1
        chosen_text = next((opt["text"] for opt in item["options"] if opt["id"] == chosen), chosen)
        correct_text = next((opt["text"] for opt in item["options"] if opt["id"] == item["correct"]), "")
        details.append(
            {
                "id": item["id"],
                "level": item["level"],
                "prompt": item["prompt"],
                "chosen": chosen_text,
                "correct": correct_text,
                "is_correct": ok,
            }
        )
    level_scores = {}
    for level, stats in by_level.items():
        total = stats["total"] or 1
        level_scores[level] = round((stats["hits"] / total) * 100)
    hits = sum(1 for row in details if row["is_correct"])
    score = round((hits / max(len(quiz), 1)) * 100)
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
        "details": details,
    }


def local_narrative(scored: dict) -> dict:
    return {
        "score": scored["score"],
        "level": scored["level"],
        "level_scores": scored["level_scores"],
        "summary": (
            f"Puntaje objetivo {scored['score']}% ({scored['level']}). "
            f"Principiante {scored['level_scores']['Principiante']}%, "
            f"Intermedio {scored['level_scores']['Intermedio']}%, "
            f"Avanzado {scored['level_scores']['Avanzado']}%."
        ),
        "strengths": ["Completó una evaluación dinámica de Claude Code por niveles."],
        "gaps": [
            "Reforzar fundamentos (CLI, login, CLAUDE.md).",
            "Plan mode, contexto y verificación con tests.",
            "Permisos, hooks, MCP y secretos.",
        ],
        "training_plan": [
            {
                "topic": "Setup y CLAUDE.md",
                "desc": "https://code.claude.com/docs/en/quickstart y https://code.claude.com/docs/en/memory",
            },
            {
                "topic": "Plan mode y verificación",
                "desc": "https://code.claude.com/docs/en/best-practices",
            },
            {
                "topic": "Permisos, hooks y MCP",
                "desc": "https://code.claude.com/docs/en/permissions y https://code.claude.com/docs/en/mcp",
            },
        ],
    }


def diagnose_with_azure(dev_name: str, dev_role: str, scored: dict) -> dict:
    user_content = (
        f"Desarrollador: {dev_name}\nRol: {dev_role}\n"
        f"Puntaje objetivo (NO cambiar): {json.dumps({k: scored[k] for k in ('score', 'level', 'level_scores')}, ensure_ascii=False)}\n"
        f"Detalle de ítems: {json.dumps(scored['details'], ensure_ascii=False)}"
    )
    report = azure_json(REPORT_PROMPT, user_content)
    report["score"] = scored["score"]
    report["level"] = scored["level"]
    report["level_scores"] = scored["level_scores"]
    report["training_plan"] = normalize_training_plan(report.get("training_plan"))
    if not report["training_plan"]:
        report["training_plan"] = local_narrative(scored)["training_plan"]
    return report


def normalize_training_plan(plan) -> list[dict]:
    rows = []
    for item in plan or []:
        if not isinstance(item, dict):
            continue
        topic = str(item.get("topic") or item.get("tema") or "").strip()
        desc = str(item.get("desc") or item.get("detalle") or item.get("detail") or "").strip()
        if topic and desc:
            rows.append({"topic": topic, "desc": desc})
    return rows


def quiz_signer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(SESSION_SECRET, salt="quiz-v1")


def dump_quiz(quiz: list[dict]) -> str:
    return quiz_signer().dumps(quiz)


def load_quiz(token: str) -> list[dict]:
    try:
        return quiz_signer().loads(token, max_age=8 * 3600)
    except SignatureExpired as exc:
        raise HTTPException(status_code=400, detail="El examen venció (8 h). Inicia una sesión nueva.") from exc
    except BadSignature as exc:
        raise HTTPException(status_code=400, detail="El examen no es válido. Inicia una sesión nueva.") from exc


def cleanup_file(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


@app.get("/", response_class=HTMLResponse)
@app.head("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


@app.post("/start-eval", response_class=HTMLResponse)
async def start_eval(
    request: Request,
    dev_name: str = Form(...),
    dev_role: str = Form(...),
):
    quiz = build_quiz()
    return templates.TemplateResponse(
        "test.html",
        {
            "request": request,
            "dev_name": dev_name,
            "dev_role": dev_role,
            "sections": group_questions(quiz),
            "quiz_token": dump_quiz(quiz),
        },
    )


@app.post("/generate-report")
async def generate_report(
    request: Request,
    dev_name: str = Form(...),
    dev_role: str = Form(...),
    answers: str = Form(...),
    quiz_token: str = Form(...),
):
    quiz = load_quiz(quiz_token)
    parsed_answers = json.loads(answers)
    scored = score_quiz(quiz, parsed_answers)
    try:
        report = diagnose_with_azure(dev_name, dev_role, scored)
    except Exception:
        report = local_narrative(scored)
    report["answers"] = scored["details"]

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
