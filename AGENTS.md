# AGENTS.md

## Architecture

- Flask backend lives at the repo root: `app.py` imports `main.app`; `main.py` contains all routes. Default port 5000.
- Next.js 16 UI lives in `frontend/` (port 3000). **`frontend/` is a separate embedded git repo tracked as a gitlink** (no `.gitmodules`). Commit UI changes inside `frontend/`; a root commit only records the new gitlink SHA.
- Read `frontend/AGENTS.md` before editing the UI: it warns that Next.js 16 APIs/conventions differ from training data and points to `frontend/node_modules/next/dist/docs/`.
- `models.py` maps frontend model keys to Ollama tags and per-model `think` / `tools` flags. Those models must already exist in the local Ollama instance.
- Tools are plugins: decorate a function with `@tool(...)` in `tools/*.py`, then add the module import to `tools/__init__.py`. Unimported modules never register. `main.py` imports `TOOLS_REGISTRY` from `tools/tool_registery.py`.
- Backend calls Ollama through the `ollama` Python client, so a running Ollama server is required.

## Commands

- Backend (must run from repo root; `data/memory.md` is opened via relative paths):
  `.venv\Scripts\activate.bat` then `python app.py`, or run `run.bat` to start backend + frontend together.
- Backend smoke test: `.venv\Scripts\python.exe -c "import main"` (also prints nothing on success).
- Frontend: `npm run dev`, `npm run lint`, `npm run build`, with `workdir="frontend"`.
- On this machine PowerShell blocks `npm.ps1` / `npx.ps1`; use `npm.cmd` and `npx.cmd` instead.
- No test suite exists. There is no root dependency manifest: `requirement.txt` is empty and Python deps are already installed in `.venv` (Python 3.14).

## Verification baseline

- `npm.cmd run lint` currently fails with 7 errors / 2 warnings and `npx.cmd tsc --noEmit` fails on `api.ts` implicit `any`. These are pre-existing; do not report them as regressions and do not claim the frontend is green.
- `npm.cmd run build` type-checks, so expect it to hit the same existing TypeScript errors.

## API contract (`main.py`)

- `POST /chat_stream` with `{model, message: [...], think?: bool}` returns SSE `data:` JSON events: `start`, `thinking`, `token`, `tool_call`, `tool_running`, `tool_result`, `tool_error`, `error`, `done`. The parser in `frontend/app/page.tsx` depends on these names and payload fields; change both sides together.
- `POST /chat` is the non-streaming variant; `GET /models` returns the `MODELS` registry.
- Frontend calls `http://localhost:5000` / `http://127.0.0.1:5000` directly (no Next proxy); Flask CORS is enabled.
- Tool-call loop is capped by `MAX_TOOL_ITERATIONS = 20` in `main.py`.

## Gotchas

- Registry entries include an extra non-schema `"call"` key and are passed to Ollama as-is.
- `execute_python_code` runs `exec()` in the backend process. Treat it as arbitrary code execution; never expose this server publicly.
- `data/memory.md` is live user memory written by the model. Do not overwrite or recreate it during development.
