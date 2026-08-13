import random
from copy import deepcopy

QUESTION_BANK = {
    "Principiante": [
        {
            "prompt": "Según las docs, ¿qué hace Claude Code al ejecutar `claude` por primera vez en un proyecto?",
            "options": [
                {"id": "a", "text": "Abre login en el navegador; si existe ANTHROPIC_API_KEY, pide aprobar esa clave en lugar del login."},
                {"id": "b", "text": "Exige pegar la API key dentro de un archivo del repositorio."},
                {"id": "c", "text": "Ejecuta gcloud auth login porque Claude Code depende de GCP."},
                {"id": "d", "text": "Arranca sin autenticación y usa un modelo local."},
            ],
            "correct": "a",
        },
        {
            "prompt": "¿Dónde debe vivir un CLAUDE.md de equipo y para qué sirve?",
            "options": [
                {"id": "a", "text": "En ./CLAUDE.md o ./.claude/CLAUDE.md: instrucciones persistentes (build, convenciones) que se leen al inicio de cada sesión."},
                {"id": "b", "text": "Solo en /etc/hosts para bloquear comandos Bash."},
                {"id": "c", "text": "Es el manifiesto de despliegue a Cloud Run."},
                {"id": "d", "text": "Reemplaza settings.json y deniega herramientas con enforcement duro."},
            ],
            "correct": "a",
        },
        {
            "prompt": "¿Qué diferencia hay entre CLAUDE.md y CLAUDE.local.md?",
            "options": [
                {"id": "a", "text": "CLAUDE.md se comparte con el equipo; CLAUDE.local.md es personal y debe ir en .gitignore."},
                {"id": "b", "text": "CLAUDE.local.md es el único que Claude lee; CLAUDE.md se ignora."},
                {"id": "c", "text": "Son idénticos y ambos deben commitearse siempre."},
                {"id": "d", "text": "CLAUDE.local.md bloquea MCP; CLAUDE.md no."},
            ],
            "correct": "a",
        },
        {
            "prompt": "En un equipo, ¿cuál es la práctica de autenticación recomendada?",
            "options": [
                {"id": "a", "text": "Claude for Teams/Enterprise: cada persona entra con su cuenta Claude.ai; no compartir API keys."},
                {"id": "b", "text": "Una sola API key en un canal de Slack para todo el squad."},
                {"id": "c", "text": "Usar el login personal de cada dev dentro de CI."},
                {"id": "d", "text": "Desactivar login para no frenar el onboarding."},
            ],
            "correct": "a",
        },
        {
            "prompt": "¿Qué hace `/init` en una sesión de Claude Code?",
            "options": [
                {"id": "a", "text": "Analiza el repo y genera o sugiere un CLAUDE.md inicial (comandos de build/test y convenciones)."},
                {"id": "b", "text": "Borra node_modules y reinstala dependencias."},
                {"id": "c", "text": "Publica el proyecto a producción."},
                {"id": "d", "text": "Crea un cluster de Kubernetes."},
            ],
            "correct": "a",
        },
        {
            "prompt": "Claude Code corre en varias superficies. ¿Cuál afirmación es correcta?",
            "options": [
                {"id": "a", "text": "CLI, extensión VS Code/Cursor, Desktop y web comparten el mismo motor: CLAUDE.md, settings y MCP aplican en todas."},
                {"id": "b", "text": "Solo existe la extensión de VS Code; la CLI está deprecada."},
                {"id": "c", "text": "La web y la CLI usan archivos de configuración distintos e incompatibles."},
                {"id": "d", "text": "Desktop no puede leer CLAUDE.md del proyecto."},
            ],
            "correct": "a",
        },
        {
            "prompt": "¿Cómo arrancas Claude Code en un repo local según el quickstart?",
            "options": [
                {"id": "a", "text": "`cd tu-proyecto` y luego `claude`."},
                {"id": "b", "text": "`az login` y abrir Cloud Code de Google."},
                {"id": "c", "text": "`npm start` sin instalar el CLI."},
                {"id": "d", "text": "Solo se puede usar en claude.ai, nunca en terminal."},
            ],
            "correct": "a",
        },
        {
            "prompt": "¿Qué debes poner en CLAUDE.md para que sea efectivo?",
            "options": [
                {"id": "a", "text": "Instrucciones específicas y concisas: comandos de build/test, layout del repo y reglas “siempre haz X”."},
                {"id": "b", "text": "Todo el código fuente del proyecto para que no tenga que leer archivos."},
                {"id": "c", "text": "Solo emojis y un “sé un 10x engineer”."},
                {"id": "d", "text": "La API key de Anthropic para no autenticarse."},
            ],
            "correct": "a",
        },
    ],
    "Intermedio": [
        {
            "prompt": "Las best practices dicen que la ventana de contexto se llena rápido. ¿Qué haces primero si Claude “olvida” instrucciones?",
            "options": [
                {"id": "a", "text": "Curar contexto: CLAUDE.md corto, @archivos relevantes, respetar .gitignore y compactar la sesión."},
                {"id": "b", "text": "Pegar todo el repositorio en el chat para “darle más memoria”."},
                {"id": "c", "text": "Subir la temperatura del modelo."},
                {"id": "d", "text": "Vaciar .gitignore para incluir dist y node_modules."},
            ],
            "correct": "a",
        },
        {
            "prompt": "¿Cuál es el flujo recomendado antes de implementar un feature?",
            "options": [
                {"id": "a", "text": "Plan mode (p. ej. Shift+Tab): explorar y planear sin editar; luego implementar con un contrato claro."},
                {"id": "b", "text": "Pedir que edite archivos de inmediato sin leer el código."},
                {"id": "c", "text": "Aceptar el primer diff completo sin plan."},
                {"id": "d", "text": "Desactivar la revisión de diffs para ir más rápido."},
            ],
            "correct": "a",
        },
        {
            "prompt": "Según best practices, ¿qué debe tener Claude para verificar su propio trabajo?",
            "options": [
                {"id": "a", "text": "Un check ejecutable: tests, build, linter o screenshot comparado con el diseño."},
                {"id": "b", "text": "Solo la frase “confía en que se ve bien”."},
                {"id": "c", "text": "Cambiar el stack del proyecto en cada tarea."},
                {"id": "d", "text": "Omitir tests para ahorrar tokens."},
            ],
            "correct": "a",
        },
        {
            "prompt": "Claude Code y git: ¿qué puede hacer de forma nativa y qué debes hacer tú?",
            "options": [
                {"id": "a", "text": "Puede stage, commit, ramas y abrir PRs; tú revisas el diff antes de merge."},
                {"id": "b", "text": "No puede tocar git; hay que copiar archivos a mano."},
                {"id": "c", "text": "Debe hacer force push a main sin revisión."},
                {"id": "d", "text": "Reemplaza git por un VCS propio de Anthropic."},
            ],
            "correct": "a",
        },
        {
            "prompt": "¿Para qué sirve `/context` durante una sesión?",
            "options": [
                {"id": "a", "text": "Ver qué hay en la ventana de contexto (p. ej. memory files) y si CLAUDE.md cargó."},
                {"id": "b", "text": "Borrar el historial de git."},
                {"id": "c", "text": "Desplegar a producción."},
                {"id": "d", "text": "Generar un Dockerfile vacío."},
            ],
            "correct": "a",
        },
        {
            "prompt": "Si Claude comete el mismo error de estilo dos veces, ¿qué recomienda la documentación?",
            "options": [
                {"id": "a", "text": "Añadir la regla a CLAUDE.md (o a .claude/rules/) para no repetirla cada sesión."},
                {"id": "b", "text": "Subir max_tokens y esperar que lo recuerde."},
                {"id": "c", "text": "Desactivar auto memory."},
                {"id": "d", "text": "Borrar el repo y empezar de cero."},
            ],
            "correct": "a",
        },
        {
            "prompt": "¿Qué es auto memory en Claude Code?",
            "options": [
                {"id": "a", "text": "Notas que Claude escribe solo (comandos de build, preferencias) y carga al inicio; no sustituye un deny de permisos."},
                {"id": "b", "text": "Un caché de Docker para builds más rápidos."},
                {"id": "c", "text": "La API key guardada en el repo."},
                {"id": "d", "text": "Un modo que salta todos los prompts de permiso."},
            ],
            "correct": "a",
        },
        {
            "prompt": "Para UI, ¿qué reduce alucinaciones de componentes según las docs?",
            "options": [
                {"id": "a", "text": "Referenciar el design system real y, si aplica, comparar un screenshot del resultado con el diseño."},
                {"id": "b", "text": "Pedir un stack distinto al del proyecto."},
                {"id": "c", "text": "Ignorar el CSS existente y generar todo inline."},
                {"id": "d", "text": "Omitir accesibilidad para ir más rápido."},
            ],
            "correct": "a",
        },
    ],
    "Avanzado": [
        {
            "prompt": "¿Qué diferencia hay entre CLAUDE.md y permissions.allow/deny en .claude/settings.json?",
            "options": [
                {"id": "a", "text": "CLAUDE.md guía al modelo (no es enforcement); allow/deny y hooks los aplica el cliente aunque Claude intente otra cosa."},
                {"id": "b", "text": "Un “no uses Bash” en CLAUDE.md bloquea igual que un deny en settings.json."},
                {"id": "c", "text": "Los permisos solo existen en producción, nunca en local."},
                {"id": "d", "text": "settings.json solo guarda el color del tema."},
            ],
            "correct": "a",
        },
        {
            "prompt": "Un PreToolUse hook que sale con código 2, ¿qué efecto tiene?",
            "options": [
                {"id": "a", "text": "Bloquea la tool call de forma determinista, incluso si hay una regla allow."},
                {"id": "b", "text": "Solo imprime un warning y deja pasar el comando."},
                {"id": "c", "text": "Reinicia la sesión de Claude."},
                {"id": "d", "text": "Convierte el hook en un skill."},
            ],
            "correct": "a",
        },
        {
            "prompt": "¿Qué es MCP en Claude Code?",
            "options": [
                {"id": "a", "text": "Model Context Protocol: conectar fuentes/herramientas externas (Jira, Drive, Slack, APIs propias) al agente."},
                {"id": "b", "text": "El compilador interno de Claude."},
                {"id": "c", "text": "El emulador de Cloud Run de Google."},
                {"id": "d", "text": "Un linter que sustituye ESLint."},
            ],
            "correct": "a",
        },
        {
            "prompt": "Si Claude propone un diff con un secreto o un .env, ¿qué haces?",
            "options": [
                {"id": "a", "text": "No commitearlo, rotarlo si se filtró, usar secret manager; CLAUDE.local.md y settings.local.json van en gitignore."},
                {"id": "b", "text": "Commitearlo y “ya lo quitamos después”."},
                {"id": "c", "text": "Codificarlo en Base64 y dejarlo en el repo."},
                {"id": "d", "text": "Desactivar cualquier revisión de secretos."},
            ],
            "correct": "a",
        },
        {
            "prompt": "¿Cuándo usar un skill en lugar de meter un procedimiento largo en CLAUDE.md?",
            "options": [
                {"id": "a", "text": "Cuando es un flujo repetible de varios pasos (p. ej. /review-pr o /deploy-staging) que el equipo quiere invocar."},
                {"id": "b", "text": "Nunca: todo debe ir en CLAUDE.md aunque tenga 20 páginas."},
                {"id": "c", "text": "Solo para guardar API keys."},
                {"id": "d", "text": "Los skills reemplazan git."},
            ],
            "correct": "a",
        },
        {
            "prompt": "¿Para qué sirven los subagents en Claude Code?",
            "options": [
                {"id": "a", "text": "Delegar subtareas en paralelo con contexto propio; un agente líder coordina y fusiona resultados."},
                {"id": "b", "text": "Sustituyen al humano en code review de producción sin supervisión."},
                {"id": "c", "text": "Son aliases de git worktree."},
                {"id": "d", "text": "Solo funcionan en Cloud Run."},
            ],
            "correct": "a",
        },
        {
            "prompt": "En un monorepo, otras carpetas cargan su CLAUDE.md al leer archivos ahí. ¿Cómo evitas ruido de otros equipos?",
            "options": [
                {"id": "a", "text": "claudeMdExcludes en settings (a menudo settings.local.json) para saltar esos CLAUDE.md."},
                {"id": "b", "text": "Borrar todos los CLAUDE.md del monorepo."},
                {"id": "c", "text": "Poner la API key en cada paquete."},
                {"id": "d", "text": "Desactivar .gitignore."},
            ],
            "correct": "a",
        },
        {
            "prompt": "¿Qué archivo de proyecto guarda permisos y hooks compartidos con el equipo?",
            "options": [
                {"id": "a", "text": ".claude/settings.json (versionado). Lo personal va en settings.local.json, gitignored."},
                {"id": "b", "text": "package-lock.json."},
                {"id": "c", "text": "Dockerfile.prod."},
                {"id": "d", "text": "Solo ~/.bashrc."},
            ],
            "correct": "a",
        },
    ],
}


def _shuffle_options(item: dict) -> dict:
    cloned = deepcopy(item)
    options = cloned["options"][:]
    random.shuffle(options)
    cloned["options"] = options
    return cloned


def sample_fallback_quiz() -> list[dict]:
    quiz = []
    index = 1
    for level in ("Principiante", "Intermedio", "Avanzado"):
        picked = random.sample(QUESTION_BANK[level], k=4)
        for item in picked:
            q = _shuffle_options(item)
            q["id"] = f"q{index}"
            q["level"] = level
            quiz.append(q)
            index += 1
    return quiz
