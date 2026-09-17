from django.test import TestCase
from django.template.loader import render_to_string


class EmailTemplateTests(TestCase):
    def test_alerta_imoveis_renders_events(self):
        html = render_to_string("emails/alerta_imoveis.html", {
            "assunto": "Alerta de leilão — 2026-09-16",
            "eventos": [
                {"titulo": "Novo imóvel adicionado", "numero_imovel": "123", "uf": "SP",
                 "cidade": "São Paulo", "bairro": "Centro", "modalidade": "Leilão",
                 "tipo": "Apartamento", "preco": "100000.00", "link": "https://exemplo.com"},
            ],
        })
        self.assertIn("Novo imóvel adicionado", html)
        self.assertIn("123", html)
        self.assertIn("São Paulo", html)