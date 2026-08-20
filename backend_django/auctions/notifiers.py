from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod

from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger("auctions.notifiers")


def _limpar_numero_whatsapp(contato: str) -> str:
    return "".join(ch for ch in str(contato) if ch.isdigit())


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


class WhatsAppNotifier(Notifier):
    nome = "whatsapp"

    def __init__(self):
        self.token = os.getenv("WHATSAPP_TOKEN", "").strip()
        self.phone_id = os.getenv("WHATSAPP_PHONE_ID", "").strip()
        self.api_url = os.getenv(
            "WHATSAPP_API_URL",
            "https://graph.facebook.com/v18.0/{phone_id}/messages",
        ).strip()

    @property
    def disponivel(self) -> bool:
        return bool(self.token and self.phone_id)

    def enviar(self, destinatario: str, assunto: str, mensagem: str) -> bool:
        if not self.disponivel:
            logger.info("WhatsApp nao configurado; pulando canal.")
            return False
        try:
            import requests

            numero = _limpar_numero_whatsapp(destinatario)
            if not numero:
                logger.warning("Numero de WhatsApp invalido: %s", destinatario)
                return False
            url = self.api_url.format(phone_id=self.phone_id)
            response = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
                json={
                    "messaging_product": "whatsapp",
                    "to": numero,
                    "type": "text",
                    "text": {"body": mensagem},
                },
                timeout=30,
            )
            response.raise_for_status()
            return True
        except Exception:
            logger.exception("Falha ao enviar WhatsApp para %s", destinatario)
            return False


def obter_notifiers() -> list[Notifier]:
    return [EmailNotifier(), WhatsAppNotifier()]
