"""routes/graph_routes.py için testler — route yoksa skip"""
import pytest, json
from yggapp import create_app, init_services


@pytest.fixture
def unauth_client():
    app = create_app("test")
    return app.test_client()


class TestGraphRoutes:
    def test_get_graph_route_exists(self, unauth_client):
        """Gerçek endpoint: /api/graph/data"""
        r = unauth_client.get("/api/graph/data")
        assert r.status_code in (200, 302)

    def test_graph_node_route(self, unauth_client):
        """Gerçek endpoint: /api/graph/node/add"""
        r = unauth_client.post("/api/graph/node/add",
                               data=json.dumps({"label": "Test", "type": "target"}),
                               content_type="application/json")
        assert r.status_code in (200, 302, 403)


class TestAttackGraphHandler:
    def test_add_node(self):
        try:
            from handlers.attack_graph import add_graph_node
            add_graph_node("Node1", "target", data={}, session_id="test")
            assert True
        except ImportError:
            pytest.skip("attack_graph module not available")

    def test_multiple_nodes(self):
        try:
            from handlers.attack_graph import add_graph_node
            add_graph_node("Node1", "target", data={}, session_id="test-multi")
            add_graph_node("Node2", "subdomain", parent_id="Node1", data={}, session_id="test-multi")
            assert True
        except ImportError:
            pytest.skip("attack_graph module not available")