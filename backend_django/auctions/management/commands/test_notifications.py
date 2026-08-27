from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from backend_django.auctions.notifiers import EmailNotifier, TelegramNotifier


class Command(BaseCommand):
    help = "Testa o envio de notificacoes por e-mail e/ou Telegram."

    def add_arguments(self, parser):
        parser.add_argument("--email", help="Destinatario do teste de e-mail.")
        parser.add_argument("--telegram", action="store_true", help="Envia um teste pelo Telegram.")
        parser.add_argument("--to", help="Telegram chat ID. Se omitido, usa TELEGRAM_CHAT_ID.")
        parser.add_argument("--subject", default="Teste de notificacao — Leilao Insights")
        parser.add_argument("--message", default="Esta e uma mensagem de teste do Leilao Insights.")
        parser.add_argument("--dry-run", action="store_true", help="Apenas mostra os canais, sem enviar.")
        parser.add_argument("--show-message", action="store_true", help="Exibe assunto e mensagem antes do envio.")

    def handle(self, *args, **options):
        email = (options.get("email") or "").strip()
        telegram_requested = options.get("telegram", False)
        chat_id = (options.get("to") or "").strip()
        subject = options["subject"]
        message = options["message"]
        dry_run = options.get("dry_run", False)
        show_message = options.get("show_message", False)

        if not email and not telegram_requested:
            raise CommandError("Informe --email, --telegram ou ambos.")

        if show_message or dry_run:
            self.stdout.write(f"Assunto: {subject}")
            self.stdout.write(f"Mensagem:\n{message}")

        failures = 0
        if email:
            if dry_run:
                self.stdout.write(f"[DRY] E-mail -> {email}")
            else:
                ok = EmailNotifier().enviar(email, subject, message)
                self.stdout.write(f"[{'OK' if ok else 'ERRO'}] E-mail -> {email}")
                failures += not ok

        if telegram_requested:
            notifier = TelegramNotifier()
            target = chat_id or notifier.default_chat_id
            if dry_run:
                self.stdout.write(f"[DRY] Telegram -> {target or '(TELEGRAM_CHAT_ID ausente)'}")
            else:
                ok = notifier.enviar(target, subject, message)
                self.stdout.write(f"[{'OK' if ok else 'ERRO'}] Telegram -> {target or '(chat ID ausente)'}")
                failures += not ok

        if failures:
            raise CommandError("Um ou mais canais falharam. Consulte os logs para detalhes.")
