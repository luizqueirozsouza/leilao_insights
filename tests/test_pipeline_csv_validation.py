import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

from pipeline import ingest_dlt
from pipeline.extrai import download_csv
from pipeline.utils import CsvValidationError, parse_caixa_csv_text, validate_caixa_csv_bytes


VALID_HEADER = "Nº do imóvel;UF;Cidade;Bairro;Preço"
VALID_ROW = "123;SP;Sao Paulo;Centro;R$ 100.000"


class CsvValidationTests(unittest.TestCase):
    def test_accepts_utf8_csv_with_preamble(self):
        frame = parse_caixa_csv_text(
            "Arquivo gerado pela Caixa\n" + VALID_HEADER + "\n" + VALID_ROW
        )

        self.assertEqual(list(frame["Nº do imóvel"]), ["123"])
        self.assertEqual(frame.loc[0, "Preço"], "R$ 100.000")

    def test_accepts_cp1252_csv_and_canonicalizes_headers(self):
        payload = (
            "Nº do imóvel;UF;Cidade;Endereço;Preço\n"
            "123;SP;Sao Paulo;Rua A;R$ 100.000\n"
        ).encode("cp1252")

        validate_caixa_csv_bytes(payload)

    def test_rejects_empty_and_html_responses(self):
        for payload in (b"", b"<html><body>Access denied</body></html>"):
            with self.subTest(payload=payload):
                with self.assertRaises(CsvValidationError):
                    validate_caixa_csv_bytes(payload)

    def test_rejects_tabular_content_without_header(self):
        with self.assertRaisesRegex(CsvValidationError, "cabecalho"):
            parse_caixa_csv_text("123;SP;Sao Paulo;Centro;100")

    def test_download_does_not_replace_previous_file_on_invalid_response(self):
        response = Mock(status_code=200, content=b"<html>blocked</html>")
        response.raise_for_status.return_value = None
        session = Mock()
        session.get.return_value = response

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            file_path = output_dir / "Lista_imoveis_SP.csv"
            file_path.write_bytes(b"previous valid snapshot")

            with self.assertRaises(CsvValidationError):
                download_csv("SP", output_dir, 1, Mock(), session=session)

            self.assertEqual(file_path.read_bytes(), b"previous valid snapshot")

    def test_ingestion_rejects_invalid_snapshot_before_database_connection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "UF=SP" / "Lista_imoveis_SP.csv"
            csv_path.parent.mkdir()
            csv_path.write_text("blocked response", encoding="utf-8")

            with (
                patch.object(ingest_dlt, "list_today_csvs", return_value=[csv_path]),
                patch.object(ingest_dlt, "validate_expected_csvs"),
                patch.object(ingest_dlt, "get_db_connection") as get_connection,
            ):
                with self.assertRaisesRegex(CsvValidationError, "UF=SP"):
                    ingest_dlt.ingest_day_dlt("2026-08-25", Mock())

            get_connection.assert_not_called()


if __name__ == "__main__":
    unittest.main()
