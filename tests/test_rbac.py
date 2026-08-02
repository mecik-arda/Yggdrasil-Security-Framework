def set_role(client, role):
    with client.session_transaction() as session_data:
        session_data["logged_in"] = True
        session_data["role"] = role
        session_data["csrf_token"] = "rbac-token"


def post_json(client, path, data):
    return client.post(path, json=data, headers={"X-CSRFToken": "rbac-token"})


class TestRBACDecorator:
    def test_require_role_import(self):
        from core import require_role
        assert callable(require_role)

    def test_roles_list(self):
        from core import DEFAULT_ROLE, ROLES
        assert ROLES == ["readonly", "analyst", "admin"]
        assert DEFAULT_ROLE == "admin"

    def test_require_role_accepts_multiple(self):
        from core import require_role
        assert callable(require_role("admin", "analyst"))


class TestRBACIntegration:
    def test_login_sets_role(self, app):
        client = app.test_client()
        response = client.post("/login", data={"password": "test123"})
        assert response.status_code == 302
        with client.session_transaction() as session_data:
            assert session_data["role"] == "admin"

    def test_readonly_role_cannot_start_c2_listener(self, app):
        client = app.test_client()
        set_role(client, "readonly")
        response = post_json(client, "/api/c2/listener/start", {"port": 4444})
        assert response.status_code == 403

    def test_analyst_role_cannot_generate_beacon(self, app):
        client = app.test_client()
        set_role(client, "analyst")
        response = post_json(
            client,
            "/api/beacon/generate",
            {"listener_url": "http://127.0.0.1:8080/api/beacon"},
        )
        assert response.status_code == 403

    def test_analyst_role_cannot_install_tool(self, app):
        client = app.test_client()
        set_role(client, "analyst")
        response = client.post(
            "/api/action",
            data={"tool": "whois", "action": "install"},
            headers={"X-CSRFToken": "rbac-token"},
        )
        assert response.status_code == 403

    def test_analyst_role_can_run_scan(self, app, mocker):
        task_manager = mocker.MagicMock()
        mocker.patch("routes.action_routes.get_task_manager", return_value=task_manager)
        client = app.test_client()
        set_role(client, "analyst")
        response = client.post(
            "/api/action",
            data={"tool": "whois", "target": "example.com", "action": "run"},
            headers={"X-CSRFToken": "rbac-token"},
        )
        assert response.status_code == 200
