from __future__ import annotations

import logging
import os
from typing import Any

import requests


def send_telegram_message(text: str, logger: logging.Logger, disable_notification: bool = False) -> dict[str, Any]:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        logger.info("Telegram nao configurado (TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID ausentes).")
        return {"sent": False, "reason": "missing_credentials"}

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "disable_notification": disable_notification,
    }

    response = requests.post(url, json=payload, timeout=30)
    if response.status_code >= 400:
        logger.error("Falha HTTP ao enviar Telegram | status=%s | body=%s", response.status_code, response.text)
        response.raise_for_status()
    body = response.json()
    if not body.get("ok"):
        raise RuntimeError(f"Falha da API Telegram: {body}")

    return {"sent": True, "result": body.get("result")}
