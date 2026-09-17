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


class ResendNotifier(Notifier):
    nome = "resend"

    def __init__(self):
        import os
        self.api_key = os.getenv("RESEND_API_KEY", "").strip()
        self.from_email = os.getenv("RESEND_FROM_EMAIL", "Leilão Insights <onboarding@resend.dev>")

    @property
    def disponivel(self) -> bool:
        return bool(self.api_key)

    def enviar(self, destinatario: str, assunto: str, mensagem: str) -> bool:
        if not self.disponivel:
            logger.info("Resend nao configurado (RESEND_API_KEY ausente); pulando envio.")
            return False
        try:
            import resend
            resend.api_key = self.api_key
            resend.Emails.send({
                "from": self.from_email,
                "to": [destinatario],
                "subject": assunto,
                "html": mensagem,
            })
            return True
        except Exception:
            logger.exception("Falha ao enviar e-mail via Resend para %s", destinatario)
            return False
