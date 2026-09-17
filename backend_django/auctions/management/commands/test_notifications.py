from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from backend_django.auctions.notifiers import EmailNotifier, ResendNotifier


class Command(BaseCommand):
    help = "Testa o envio de notificacoes por e-mail e/ou Resend."

    def add_arguments(self, parser):
        parser.add_argument("--email", help="Destinatario do teste de e-mail.")
        parser.add_argument("--resend", help="Destinatario do teste via Resend (HTML).")
        parser.add_argument("--subject", default="Teste de notificacao — Leilao Insights")
        parser.add_argument("--message", default="<p>Esta e uma mensagem de teste do Leilao Insights.</p>")
        parser.add_argument("--dry-run", action="store_true", help="Apenas mostra os canais, sem enviar.")
        parser.add_argument("--show-message", action="store_true", help="Exibe assunto e mensagem antes do envio.")

    def handle(self, *args, **options):
        email = (options.get("email") or "").strip()
        resend_to = (options.get("resend") or "").strip()
        subject = options["subject"]
        message = options["message"]
        dry_run = options.get("dry_run", False)
        show_message = options.get("show_message", False)

        if not email and not resend_to:
            raise CommandError("Informe --email, --resend ou ambos.")

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

        if resend_to:
            notifier = ResendNotifier()
            if dry_run:
                self.stdout.write(f"[DRY] Resend -> {resend_to}")
            else:
                ok = notifier.enviar(resend_to, subject, message)
                self.stdout.write(f"[{'OK' if ok else 'ERRO'}] Resend -> {resend_to}")
                failures += not ok

        if failures:
            raise CommandError("Um ou mais canais falharam. Consulte os logs para detalhes.")