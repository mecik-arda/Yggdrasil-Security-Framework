"""handlers/valkyrie_reporter.py için testler — eksikse skip"""
import pytest
pytest.importorskip("handlers.valkyrie_reporter", reason="valkyrie modülü yok")


class TestValkyrieHTMLOutput:
    def test_valkyrie_produces_html(self):
        from handlers.valkyrie_reporter import generate_report
        # generate_report expects a dict (scan_data)
        result = generate_report({"target": "test-target", "scan_results": {}})
        assert isinstance(result, str)
        assert len(result) > 0
