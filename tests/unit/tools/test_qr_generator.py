"""Unit tests for tools/manufacturing/qr_generator.py"""

import pytest

import qrcode
from qr_generator import QRGenerator


@pytest.fixture
def gen(tmp_path):
    g = QRGenerator(base_url="https://lamps.example.com/")
    g.output_dir = str(tmp_path)   # never write into the repo
    return g


@pytest.fixture
def captured_urls(monkeypatch):
    urls = []
    original = qrcode.QRCode.add_data

    def spy(self, data, *a, **k):
        urls.append(data)
        return original(self, data, *a, **k)

    monkeypatch.setattr(qrcode.QRCode, "add_data", spy)
    return urls


@pytest.mark.unit
class TestQrGenerator:
    def test_base_url_trailing_slash_stripped(self, gen):
        assert gen.base_url == "https://lamps.example.com"

    def test_qr_encodes_registration_url(self, gen, captured_urls):
        gen.generate_qr_code(6689108)
        assert captured_urls == ["https://lamps.example.com/register?id=6689108"]

    def test_qr_url_matches_what_auth_register_expects(self, gen, captured_urls):
        """The web side reads ?id=<int>; the QR must use exactly that parameter."""
        from urllib.parse import parse_qs, urlparse
        gen.generate_qr_code(14)
        q = parse_qs(urlparse(captured_urls[0]).query)
        assert q == {"id": ["14"]}

    def test_writes_png_named_by_id(self, gen, tmp_path):
        path = gen.generate_qr_code(14)
        assert path == str(tmp_path / "arduino_14.png")
        with open(path, "rb") as f:
            assert f.read(8) == b"\x89PNG\r\n\x1a\n"

    def test_label_adds_height(self, gen):
        from PIL import Image
        with Image.open(gen.generate_qr_code(1, size=200, add_label=True)) as labelled:
            assert labelled.size == (200, 250)
        with Image.open(gen.generate_qr_code(2, size=200, add_label=False)) as plain:
            assert plain.size == (200, 200)

    def test_default_base_url_is_production(self):
        assert QRGenerator().base_url == "https://final-surf-lamp-web.onrender.com"

    def test_batch_generates_each_id(self, gen, captured_urls):
        paths = gen.generate_batch(3, 5)
        assert len(paths) == 3
        assert [u.rsplit("=", 1)[1] for u in captured_urls] == ["3", "4", "5"]
