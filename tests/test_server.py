#!/usr/bin/env python3
"""Automated integration test suite for D2 Diagram Rendering Microservice.

Tests endpoints, query options (sketch, theme), error handling, caching,
and saves generated SVGs to tests/output/ for visual verification.
"""

import base64
import os
import sys
import unittest
import urllib.error
import urllib.parse
import urllib.request
import zlib

TARGET_URL = os.environ.get("TEST_TARGET_URL", "http://127.0.0.1:8080")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")


def encode_d2(d2_text: str) -> str:
    """Helper to deflate and URL-safe base64 encode a D2 script."""
    compressed = zlib.compress(d2_text.encode("utf-8"), 9)
    return base64.urlsafe_b64encode(compressed).decode("ascii")


class TestD2Server(unittest.TestCase):
    """Integration test suite executing against a live or containerized server."""

    @classmethod
    def setUpClass(cls):
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    def _http_get(self, path: str):
        url = urllib.parse.urljoin(TARGET_URL, path)
        req = urllib.request.Request(url)
        return urllib.request.urlopen(req, timeout=10)

    def _http_post(self, path: str, body: str):
        url = urllib.parse.urljoin(TARGET_URL, path)
        data = body.encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "text/plain"})
        return urllib.request.urlopen(req, timeout=10)

    def test_01_health_check(self):
        """Verifies GET /health returns 200 OK."""
        res = self._http_get("/health")
        self.assertEqual(res.status, 200)
        content = res.read().decode("utf-8")
        self.assertEqual(content, "OK")

    def test_02_get_simple_diagram(self):
        """Verifies GET /d2/svg/<encoded> renders a valid SVG."""
        d2_code = "x -> y: Ping\ny -> x: Pong"
        encoded = encode_d2(d2_code)

        res = self._http_get(f"/d2/svg/{encoded}")
        self.assertEqual(res.status, 200)
        self.assertIn("image/svg+xml", res.headers.get("Content-Type", ""))

        svg_content = res.read().decode("utf-8")
        self.assertTrue(svg_content.startswith("<svg") or "<svg" in svg_content)
        self.assertIn("</svg>", svg_content)
        self.assertIn("Ping", svg_content)
        self.assertIn("Pong", svg_content)

        # Save to output for visual check
        out_path = os.path.join(OUTPUT_DIR, "01_simple_diagram.svg")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(svg_content)

    def test_03_get_sketch_mode(self):
        """Verifies ?sketch=true produces a valid sketch-styled SVG."""
        d2_code = "client -> server: Request"
        encoded = encode_d2(d2_code)

        # Standard render
        res_standard = self._http_get(f"/d2/svg/{encoded}")
        svg_standard = res_standard.read().decode("utf-8")

        # Sketch render
        res_sketch = self._http_get(f"/d2/svg/{encoded}?sketch=true")
        self.assertEqual(res_sketch.status, 200)
        svg_sketch = res_sketch.read().decode("utf-8")

        self.assertIn("</svg>", svg_sketch)
        # Sketch mode generates rough path variations, so outputs must differ
        self.assertNotEqual(svg_standard, svg_sketch)

        out_path = os.path.join(OUTPUT_DIR, "02_sketch_mode.svg")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(svg_sketch)

    def test_04_get_theme(self):
        """Verifies ?theme=200 applies a custom theme."""
        d2_code = "database: Customer DB {\n  shape: cylinder\n}"
        encoded = encode_d2(d2_code)

        res = self._http_get(f"/d2/svg/{encoded}?theme=200")
        self.assertEqual(res.status, 200)
        svg_content = res.read().decode("utf-8")
        self.assertIn("</svg>", svg_content)

        out_path = os.path.join(OUTPUT_DIR, "03_theme_200.svg")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(svg_content)

    def test_05_post_raw_diagram(self):
        """Verifies POST /d2/svg accepts raw body text and returns SVG."""
        d2_code = """
        direction: right
        Frontend -> Backend: GraphQL Query
        Backend -> Database: SQL SELECT
        """
        res = self._http_post("/d2/svg", d2_code)
        self.assertEqual(res.status, 200)
        svg_content = res.read().decode("utf-8")
        self.assertIn("</svg>", svg_content)
        self.assertIn("GraphQL Query", svg_content)

        out_path = os.path.join(OUTPUT_DIR, "04_post_rendered.svg")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(svg_content)

    def test_06_render_example_architecture(self):
        """Verifies rendering of the full architecture.d2 example file."""
        example_path = os.path.join(os.path.dirname(__file__), "..", "examples", "architecture.d2")
        with open(example_path, "r", encoding="utf-8") as f:
            d2_code = f.read()

        res = self._http_post("/d2/svg", d2_code)
        self.assertEqual(res.status, 200)
        svg_content = res.read().decode("utf-8")
        self.assertIn("</svg>", svg_content)
        self.assertIn("Microservice Architecture", svg_content)

        out_path = os.path.join(OUTPUT_DIR, "05_architecture.svg")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(svg_content)

    def test_07_render_example_sequence(self):
        """Verifies rendering of the full sequence.d2 example file."""
        example_path = os.path.join(os.path.dirname(__file__), "..", "examples", "sequence.d2")
        with open(example_path, "r", encoding="utf-8") as f:
            d2_code = f.read()

        res = self._http_post("/d2/svg", d2_code)
        self.assertEqual(res.status, 200)
        svg_content = res.read().decode("utf-8")
        self.assertIn("</svg>", svg_content)
        self.assertIn("OAuth Provider", svg_content)

        out_path = os.path.join(OUTPUT_DIR, "06_sequence.svg")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(svg_content)

    def test_08_lru_caching(self):
        """Verifies in-memory LRU cache serves hits on duplicate requests."""
        d2_code = "cache_test -> pass: Caching test"
        encoded = encode_d2(d2_code)

        # First request (MISS)
        res1 = self._http_get(f"/d2/svg/{encoded}")
        self.assertEqual(res1.status, 200)
        self.assertEqual(res1.headers.get("X-Cache"), "MISS")

        # Second request (HIT)
        res2 = self._http_get(f"/d2/svg/{encoded}")
        self.assertEqual(res2.status, 200)
        self.assertEqual(res2.headers.get("X-Cache"), "HIT")

    def test_09_invalid_base64_returns_400(self):
        """Verifies malformed base64 strings return HTTP 400 Bad Request."""
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._http_get("/d2/svg/this_is_not_valid_deflate_base64!!!")
        self.assertEqual(ctx.exception.code, 400)

    def test_10_invalid_d2_syntax_returns_400(self):
        """Verifies invalid D2 syntax triggers HTTP 400 with compiler error message."""
        bad_syntax = "invalid syntax { unclosed bracket"
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._http_post("/d2/svg", bad_syntax)
        self.assertEqual(ctx.exception.code, 400)
        body = ctx.exception.read().decode("utf-8")
        self.assertIn("D2", body)

    def test_11_unmatched_route_returns_404(self):
        """Verifies unmatched routes return HTTP 404 Not Found."""
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._http_get("/non_existent_endpoint")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
