from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

# Registra /app no sys.path ANTES de qualquer import de modulos internos
# (pipeline.*). Sem isso, ao invocar `python pipeline/<script>.py`, o CWD
# /app nao vai para o path, e o `from pipeline.notify_telegram import ...`
# abaixo quebra com ModuleNotFoundError (bug do agendador diario).
import requests
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pipeline.notify_telegram import send_telegram_message

load_dotenv()


def _configure_logging(verbose: bool) -> logging.Logger:
    logger = logging.getLogger("pipeline.trigger_github_sync")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.propagate = False
    return logger


def _resolve_repo(logger: logging.Logger) -> tuple[str, str]:
    repo = os.getenv("GITHUB_REPO")
    if repo:
        owner, name = repo.split("/", 1)
        return owner, name
    git_dir = ROOT_DIR / ".git"
    if git_dir.exists():
        try:
            from subprocess import run

            result = run(
                ["git", "remote", "get-url", "origin"],
                cwd=str(ROOT_DIR),
                capture_output=True,
                text=True,
            )
            url = result.stdout.strip()
            if url.endswith(".git"):
                url = url[:-4]
            if "github.com" in url:
                owner, name = url.rstrip("/").split("github.com/")[-1].split("/", 1)
                return owner, name
        except Exception as exc:
            logger.warning("Falha ao detectar repo via git: %s", exc)
    raise RuntimeError(
        "Nao foi possivel detectar o repo. Defina GITHUB_REPO='owner/name' no .env."
    )


def _trigger_workflow(logger: logging.Logger) -> dict:
    token = os.getenv("GITHUB_ACTIONS_TRIGGER_TOKEN")
    if not token:
        raise RuntimeError("Faltando GITHUB_ACTIONS_TRIGGER_TOKEN no .env da VPS.")

    owner, repo = _resolve_repo(logger)
    ref = os.getenv("GITHUB_WORKFLOW_REF", "main")
    workflow = os.getenv("GITHUB_WORKFLOW_FILE", "daily-sync.yml")
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow}/dispatches"

    logger.info("Disparando workflow %s em %s/%s (ref=%s)", workflow, owner, repo, ref)
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={"ref": ref},
        timeout=30,
    )
    if response.status_code >= 400:
        raise RuntimeError(
            f"Falha ao disparar workflow | status={response.status_code} | body={response.text[:500]}"
        )

    return {"owner": owner, "repo": repo, "workflow": workflow}


def _find_run(owner: str, repo: str, logger: logging.Logger, max_attempts: int = 60) -> dict | None:
    token = os.getenv("GITHUB_ACTIONS_TRIGGER_TOKEN")
    url = (
        f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/daily-sync.yml/runs"
        f"?event=workflow_dispatch&per_page=1"
    )
    started = time.time()
    for _ in range(max_attempts):
        response = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30,
        )
        if response.status_code == 200:
            runs = response.json().get("workflow_runs", [])
            if runs:
                return runs[0]
        time.sleep(15)
    logger.warning("Run nao encontrada apos %d s", int(time.time() - started))
    return None


def _poll_run(run: dict, logger: logging.Logger, timeout: int) -> dict:
    token = os.getenv("GITHUB_ACTIONS_TRIGGER_TOKEN")
    url = f"https://api.github.com/repos/{run['repository']['full_name']}/actions/runs/{run['id']}"
    started = time.time()
    while time.time() - started < timeout:
        response = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30,
        )
        if response.status_code == 200:
            run = response.json()
            status = run.get("status")
            if status == "completed":
                return run
            logger.info("Run %s: status=%s (%ds)", run["id"], status, int(time.time() - started))
        time.sleep(30)
    raise TimeoutError(f"Run nao concluiu em {timeout}s")


def _format_message(run: dict) -> str:
    conclusion = run.get("conclusion", "unknown")
    html_url = run.get("html_url", "")
    if conclusion == "success":
        return (
            "<b>Sync GitHub: sucesso</b>\n"
            f"Run: <a href=\"{html_url}\">{run.get('id')}</a>\n"
            f"Conclusao: <code>{conclusion}</code>"
        )
    return (
        "<b>Sync GitHub: falha</b>\n"
        f"Run: <a href=\"{html_url}\">{run.get('id')}</a>\n"
        f"Conclusao: <code>{conclusion}</code>"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dispara o workflow diario de sync no GitHub a partir da VPS."
    )
    parser.add_argument("--verbose", action="store_true", help="Logs detalhados.")
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Dispara e sai, sem aguardar a conclusao do workflow.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=3600,
        help="Tempo maximo (s) aguardando a conclusao da run.",
    )
    parser.add_argument("--skip-telegram", action="store_true", help="Nao envia Telegram.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logger = _configure_logging(args.verbose)

    try:
        info = _trigger_workflow(logger)

        if args.no_wait:
            logger.info("Workflow disparado. Saindo sem aguardar (--no-wait).")
            return 0

        run = _find_run(info["owner"], info["repo"], logger)
        if run is None:
            logger.warning("Nao localizei a run recem-criada.")
            return 0

        final = _poll_run(run, logger, args.timeout)
        message = _format_message(final)
        logger.info(message)

        if not args.skip_telegram:
            send_telegram_message(message, logger)

        return 0 if final.get("conclusion") == "success" else 1
    except Exception as exc:
        logger.exception("Falha ao disparar/aguardar workflow")
        if not args.skip_telegram:
            try:
                send_telegram_message(f"<b>Falha ao disparar sync GitHub</b>\n<code>{exc}</code>", logger)
            except Exception:
                logger.exception("Falha ao enviar alerta Telegram")
        return 1


if __name__ == "__main__":
    sys.exit(main())
