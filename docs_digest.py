"""Hechos condensados de https://code.claude.com/docs/ para generar y validar preguntas."""

DOCS_DIGEST = """
DOCUMENTACIÓN OFICIAL Claude Code (https://code.claude.com/docs/)
No confundir con Google Cloud Code.

INSTALACIÓN Y ARRANQUE
- macOS/Linux/WSL: curl -fsSL https://claude.ai/install.sh | bash
- Windows PowerShell: irm https://claude.ai/install.ps1 | iex
- Windows CMD: install.cmd (no usar && en PowerShell)
- brew install --cask claude-code (no auto-update; brew upgrade)
- winget install Anthropic.ClaudeCode
- Verificar: claude --version
- Arranque: cd proyecto && claude
- Git for Windows recomendado en Windows nativo para la tool Bash

AUTH
- Primera vez: login en navegador. ANTHROPIC_API_KEY salta el login y pide aprobar la key.
- /login para cambiar cuenta. /logout cierra sesión.
- Cuentas: Pro/Max/Team/Enterprise (claude.ai), Console (API), Bedrock/Vertex/Foundry, gateway SSO.
- Equipos: cada persona con su cuenta; no compartir API keys.

COMANDOS
- claude | claude "tarea" | claude -p "query" | claude -c (continuar) | claude -r (resume)
- En sesión: /help /clear /exit /init /context /compact /memory /permissions
- Shift+Tab cicla modos: default (pide aprobación), acceptEdits, plan (propone sin editar). Algunos tienen auto.

CLAUDE.md Y MEMORIA
- CLAUDE.md o .claude/CLAUDE.md: instrucciones persistentes al inicio (contexto, NO enforcement).
- ~/.claude/CLAUDE.md: preferencias personales.
- CLAUDE.local.md: personal del proyecto; gitignore.
- /init genera o mejora CLAUDE.md.
- Auto memory: Claude anota aprendizajes; no sustituye deny/hooks.
- /context muestra qué memory files cargaron.
- Instrucciones vagas o contradictorias se siguen peor. Conciso y específico.
- Procedimientos multi-paso -> skills, no un CLAUDE.md enorme.
- claudeMdExcludes salta CLAUDE.md de otros equipos en monorepos.

CONTEXTO Y BEST PRACTICES
- La ventana de contexto se llena; el rendimiento baja. No pegar todo el repo.
- Explorar/planear (plan mode) antes de codear.
- Dar verificación: tests, build, linter, screenshot vs diseño.
- Git conversacional: commit, branch, PRs; el humano revisa el diff.
- Permisos: default pregunta antes de editar.

PERMISOS, HOOKS, MCP
- permissions.allow/deny/ask en .claude/settings.json los aplica el CLI, no el modelo.
- CLAUDE.md no bloquea tools. Para bloquear: deny o PreToolUse hook.
- Hook PreToolUse exit 2 bloquea la tool incluso con allow.
- settings.json se comparte; settings.local.json es personal (gitignore).
- MCP: conectar Jira, Drive, Slack, APIs propias.
- Skills: flujos repetibles (/review-pr). Subagents: subtareas en paralelo.
- Secretos: no commitear .env; rotar si se filtró.
"""
