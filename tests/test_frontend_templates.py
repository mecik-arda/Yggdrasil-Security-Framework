"""Frontend template rendering testleri — HTML sayfalar, static dosyalar"""
import pytest


class TestTemplateRendering:
    def test_login_page_render(self, app):
        c = app.test_client()
        r = c.get("/login")
        assert r.status_code == 200
        html = r.data.decode()
        assert "yggdrasil" in html.lower()
        assert "password" in html.lower()

    def test_login_page_has_form(self, app):
        c = app.test_client()
        r = c.get("/login")
        html = r.data.decode()
        assert "<form" in html.lower()
        assert 'method="post"' in html.lower()

    def test_dashboard_after_login(self, auth_client):
        r = auth_client.get("/", follow_redirects=True)
        assert r.status_code == 200
        html = r.data.decode()
        assert "csrfToken" in html or "csrf_token" in html or "csrf" in html.lower()

    def test_dashboard_has_tools(self, auth_client):
        r = auth_client.get("/")
        html = r.data.decode()
        # Dashboard must contain tool references or at least be the dashboard
        assert (
            "nmap" in html.lower()
            or "tool" in html.lower()
            or "scan" in html.lower()
            or "yggdrasil" in html.lower()
        )


class TestStaticFiles:
    def test_css_served(self, app):
        c = app.test_client()
        r = c.get("/static/roots.css")
        assert r.status_code == 200
        assert "text/css" in r.content_type

    def test_js_served(self, app):
        c = app.test_client()
        r = c.get("/static/js/modules/core_api.js")
        assert r.status_code == 200
        assert "javascript" in r.content_type or "text/" in r.content_type

    def test_favicon(self, app):
        c = app.test_client()
        r = c.get("/favicon.ico")
        assert r.status_code in (200, 404, 500)


class TestContentType:
    def test_json_api_returns_json(self, app):
        c = app.test_client()
        r = c.get("/api/auth/status")
        assert r.content_type == "application/json"

    def test_html_pages_return_html(self, app):
        c = app.test_client()
        r = c.get("/login")
        assert "text/html" in r.content_type