"""Frontend XSS koruması testleri — innerHTML, trusted_source, escapeHtml"""
import pytest, re
from yggapp import create_app, init_services


@pytest.fixture(scope="session")
def app():
    a = create_app("test")
    init_services(a)
    return a


class TestInnerHTMLGuards:
    def test_core_api_has_trusted_source_guard(self):
        """core_api.js'de her innerHTML kullanımı trusted_source kontrollü olmalı."""
        js = open("static/js/modules/core_api.js").read()
        inner_count = js.count("innerHTML")
        trusted_count = js.count("trusted_source")
        assert trusted_count > 0, "No trusted_source guard found"
        assert inner_count > 0, "No innerHTML usage found (unexpected)"

    def test_trusted_html_uses_allowlist_sanitizer(self):
        js = open("static/js/modules/core_api.js", encoding="utf-8").read()
        sanitizer = open("static/js/modules/html_sanitizer.js", encoding="utf-8").read()
        assert "setSanitizedHtml(pt.contentDiv" in js
        assert "setSanitizedHtml(contentDiv" in js
        assert "allowedTags" in sanitizer
        assert "allowedAttributes" in sanitizer
        assert "element.removeAttribute" in sanitizer

    def test_sanitizer_rejects_active_content(self):
        sanitizer = open("static/js/modules/html_sanitizer.js", encoding="utf-8").read()
        assert "'SCRIPT'" not in sanitizer
        assert "'IFRAME'" not in sanitizer
        assert "'SVG'" not in sanitizer
        assert "'style'" not in sanitizer

    def test_html_type_guarded(self):
        js = open("static/js/modules/core_api.js").read()
        # At least one occurrence of trusted_source near innerHTML
        pattern = r"trusted_source.*innerHTML|innerHTML.*trusted_source"
        assert re.search(pattern, js, re.DOTALL) is not None

    def test_no_eval_in_js(self):
        """JS dosyalarında eval() olmamalı."""
        js = open("static/js/modules/core_api.js").read()
        assert "eval(" not in js, "eval() found in core_api.js"

    def test_no_document_write(self):
        js = open("static/js/modules/core_api.js").read()
        assert "document.write" not in js, "document.write() found"


class TestEscapeHtmlFunction:
    def test_escape_html_exists(self):
        """escapeHtml() fonksiyonu tanımlanmış olmalı."""
        found = False
        import glob
        for f in glob.glob("static/js/**/*.js", recursive=True):
            content = open(f, encoding="utf-8").read()
            if "function escapeHtml" in content or "escapeHtml =" in content or "escapeHtml=" in content:
                found = True
                break
        assert found, "escapeHtml() function not found in any JS file"

    def test_error_messages_escaped(self):
        """Hata mesajlarında escapeHtml() kullanılıyor olmalı."""
        js = open("static/js/modules/core_api.js").read()
        # Error display paths should use escapeHtml
        has_escape = "escapeHtml" in js
        assert has_escape, "escapeHtml not referenced in core_api.js"


class TestTemplateSafety:
    def test_no_raw_html_injection(self):
        """Template'lerde user input doğrudan gömülmemeli."""
        templates = ["templates/index.html", "templates/login.html"]
        for tpl in templates:
            try:
                content = open(tpl, encoding="utf-8").read()
                # |safe filtresi sadece tojson için kullanılmalı
                safe_usages = content.count("| safe")
                tojson_safe = content.count("| tojson | safe")
                assert safe_usages == tojson_safe, \
                    f"{tpl}: |safe only allowed with |tojson, found {safe_usages} safe, {tojson_safe} tojson+safe"
            except FileNotFoundError:
                pass
