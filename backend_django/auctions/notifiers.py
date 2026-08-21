from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod

from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger("auctions.notifiers")


class Notifier(ABC):
    nome = "base"

    @abstractmethod
    def enviar(self, destinatario: str, assunto: str, mensagem: str) -> bool:
        ...


class EmailNotifier(Notifier):
    nome = "email"

    def enviar(self, destinatario: str, assunto: str, mensagem: str) -> bool:
        try:
            send_mail(
                subject=assunto,
                message=mensagem,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[destinatario],
                fail_silently=False,
            )
            return True
        except Exception:
            logger.exception("Falha ao enviar e-mail para %s", destinatario)
            return False


class TelegramNotifier(Notifier):
    nome = "telegram"

    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        self.default_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        self.api_url = os.getenv("TELEGRAM_API_URL", "https://api.telegram.org").rstrip("/")

    @property
    def disponivel(self) -> bool:
        return bool(self.token)

    def enviar(self, destinatario: str, assunto: str, mensagem: str) -> bool:
        if not self.disponivel:
            logger.info("Telegram nao configurado; pulando canal.")
            return False
        try:
            import requests

            chat_id = str(destinatario or self.default_chat_id).strip()
            if not chat_id:
                logger.warning("Telegram chat ID nao informado.")
                return False
            url = f"{self.api_url}/bot{self.token}/sendMessage"
            texto = f"{assunto}\n\n{mensagem}" if assunto else mensagem
            response = requests.post(
                url,
                json={"chat_id": chat_id, "text": texto},
                timeout=30,
            )
            response.raise_for_status()
            return True
        except Exception:
            logger.exception("Falha ao enviar Telegram para %s", destinatario)
            return False


def obter_notifiers() -> list[Notifier]:
    return [EmailNotifier(), TelegramNotifier()]
