from __future__ import annotations

import json
import logging
from datetime import date

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.template.loader import render_to_string

from backend_django.auctions.models import (
    Auction,
    NotificacaoEnviada,
    PreferenciaAlerta,
)
from backend_django.auctions.notifiers import ResendNotifier

logger = logging.getLogger("auctions.notify")


def _pref_casa(pref: PreferenciaAlerta, imovel: Auction) -> bool:
    if pref.uf and pref.uf.upper() != (imovel.uf or "").upper():
        return False
    if pref.cidades and (imovel.cidade or "").strip() not in pref.cidades:
        return False
    if pref.bairros and (imovel.bairro or "").strip() not in pref.bairros:
        return False
    if pref.modalidades and (imovel.modalidade or "").strip() not in pref.modalidades:
        return False
    if pref.tipos and (imovel.tipo_imovel or "").strip() not in pref.tipos:
        return False
    return True


def _normalizar_payload(payload) -> dict:
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        try:
            value = json.loads(payload)
            if isinstance(value, dict):
                return value
        except (json.JSONDecodeError, TypeError):
            pass
    return {}


def _payload_value(payload: dict, *keys: str):
    for key in keys:
        value = payload.get(key)
        if value is not None and str(value).strip():
            return value
    return ""


def _pref_payload_casa(pref: PreferenciaAlerta, payload: dict, uf: str) -> bool:
    if pref.uf and pref.uf.upper() != (uf or "").upper():
        return False
    if pref.cidades and _payload_value(payload, "Cidade") not in pref.cidades:
        return False
    if pref.bairros and _payload_value(payload, "Bairro") not in pref.bairros:
        return False
    if pref.modalidades and _payload_value(payload, "Modalidade de venda") not in pref.modalidades:
        return False
    if pref.tipos and _payload_value(payload, "tipo_imovel", "Tipo de imóvel", "Tipo de imovel") not in pref.tipos:
        return False
    return True


def _descrever_evento(tipo_evento: str) -> str:
    return {
        "ENTER": "Novo imóvel adicionado",
        "EXIT": "Imóvel removido",
        "UPDATE": "Imóvel atualizado",
    }.get(tipo_evento, tipo_evento)


def _montar_evento_html(evento: dict, imovel: Auction | None, payload: dict | None = None) -> dict:
    base = _descrever_evento(evento["tipo_evento"])
    dados = {
        "titulo": base,
        "numero_imovel": evento["numero_imovel"],
        "uf": evento["uf"],
        "cidade": None,
        "bairro": None,
        "modalidade": None,
        "tipo": None,
        "preco": None,
        "link": None,
    }
    if imovel:
        dados.update({
            "cidade": imovel.cidade,
            "bairro": imovel.bairro,
            "modalidade": imovel.modalidade,
            "tipo": imovel.tipo_imovel,
            "preco": imovel.preco,
            "link": imovel.link,
        })
    elif payload:
        dados["cidade"] = _payload_value(payload, "Cidade") or None
        dados["bairro"] = _payload_value(payload, "Bairro") or None
        dados["modalidade"] = _payload_value(payload, "Modalidade de venda") or None
        dados["tipo"] = _payload_value(payload, "tipo_imovel", "Tipo de imóvel", "Tipo de imovel") or None
        dados["preco"] = _payload_value(payload, "Preço", "Pre\u00e7o") or None
        dados["link"] = _payload_value(payload, "Link de acesso") or None
    return dados


def _preferencias_ativas() -> list[PreferenciaAlerta]:
    return list(
        PreferenciaAlerta.objects.filter(canal_email=True).select_related("usuario")
    )


class Command(BaseCommand):
    help = "Dispara notificacoes de alerta para assinantes com base nos eventos de mudanca do dia."

    def add_arguments(self, parser):
        parser.add_argument("--date", type=str, default=None, help="Data em YYYY-MM-DD. Padrao: hoje.")
        parser.add_argument("--dry-run", action="store_true", help="Nao envia, apenas lista o que seria enviado.")
        parser.add_argument("--show-message", action="store_true", help="Exibe a mensagem completa de cada alerta.")

    def handle(self, *args, **options):
        dt = options.get("date") or date.today().isoformat()
        dry_run = options.get("dry_run", False)
        show_message = options.get("show_message", False)

        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT uf, numero_imovel, tipo_evento, before_json, after_json
                FROM changes
                WHERE dt = %s AND tipo_evento IN ('ENTER', 'EXIT')
                """,
                (dt,),
            )
            eventos = [
                {
                    "uf": r[0],
                    "numero_imovel": r[1],
                    "tipo_evento": r[2],
                    "before_json": r[3] or {},
                    "after_json": r[4] or {},
                }
                for r in cur.fetchall()
            ]

        if not eventos:
            self.stdout.write(f"Nenhum evento em changes para {dt}.")
            return

        numeros = {(e["uf"], e["numero_imovel"]) for e in eventos}
        imoveis = {}
        for a in Auction.objects.filter(
            uf__in=[n[0] for n in numeros], numero_imovel__in=[n[1] for n in numeros]
        ):
            imoveis[(a.uf, a.numero_imovel)] = a

        preferencias = _preferencias_ativas()
        assunto = f"Alerta de leilão — {dt}"

        enviados = 0

        for pref in preferencias:
            if not (pref.canal_email and pref.usuario.email):
                continue

            lista = []
            registros = []
            vistos = set()

            for evento in eventos:
                chave = (evento["uf"], evento["numero_imovel"])
                imovel = imoveis.get(chave)

                payload = _normalizar_payload(evento["before_json"] if evento["tipo_evento"] == "EXIT" else evento["after_json"])
                if imovel:
                    if not _pref_casa(pref, imovel):
                        continue
                else:
                    if not _pref_payload_casa(pref, payload, evento["uf"]):
                        continue

                chave_evento = (evento["uf"], evento["numero_imovel"], evento["tipo_evento"])
                if chave_evento in vistos:
                    continue
                vistos.add(chave_evento)

                ja_enviado = NotificacaoEnviada.objects.filter(
                    preferencia=pref,
                    numero_imovel=evento["numero_imovel"],
                    uf=evento["uf"],
                    tipo_evento=evento["tipo_evento"],
                    dt=dt,
                ).exists()
                if ja_enviado:
                    continue

                lista.append(_montar_evento_html(evento, imovel, payload))
                registros.append(evento)

            if not lista:
                continue

            try:
                html = render_to_string("emails/alerta_imoveis.html", {"assunto": assunto, "eventos": lista})
            except Exception:
                logger.exception("Falha ao renderizar template de alerta para %s", pref.usuario.email)
                continue
            if show_message or dry_run:
                self.stdout.write(f"\n--- Email para {pref.usuario.email} ---\n{html}\n--- Fim do email ---")

            enviados += 1
            self.stdout.write(
                f"[{'DRY' if dry_run else 'ENV'}] {pref.usuario.email} ({len(lista)} evento(s))"
            )

            if not dry_run:
                ok = ResendNotifier().enviar(pref.usuario.email, assunto, html)
                if not ok:
                    self.stdout.write(f"[FALHA] Nao foi possivel enviar para {pref.usuario.email}; eventos nao marcados como enviados.")
                    continue
                with transaction.atomic():
                    for evento in registros:
                        NotificacaoEnviada.objects.create(
                            preferencia=pref,
                            tipo_evento=evento["tipo_evento"],
                            numero_imovel=evento["numero_imovel"],
                            uf=evento["uf"],
                            dt=dt,
                            canais=["resend"],
                        )

        self.stdout.write(
            self.style.SUCCESS(f"Concluido: {enviados} emails ({'dry-run' if dry_run else 'enviados'}).")
        )