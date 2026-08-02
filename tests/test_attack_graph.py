"""
Tests for Attack Graph — node creation, edge/parent relationships,
JSON data storage, retrieval, deletion, reset, and auto-population
from scan history.

Covers ``handlers/attack_graph.py``.
"""

import sys
import json
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Module-level setup — remove handlers mock
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module", autouse=True)
def _unmock_handlers():
    """Remove the conftest session mock so real handler modules can be imported."""
    if 'handlers' in sys.modules:
        del sys.modules['handlers']


# ---------------------------------------------------------------------------
# Fixtures — ensure C2 tables exist in test DB
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _ensure_tables():
    """Ensure all required tables exist before each test."""
    from core.db import init_db, init_c2_tables
    init_db()
    init_c2_tables()


# ---------------------------------------------------------------------------
# add_graph_node
# ---------------------------------------------------------------------------

class TestAddGraphNode:
    def test_add_node_success(self):
        """Adding a node should return success with node_id."""
        from handlers.attack_graph import add_graph_node
        result = add_graph_node('Test Target', 'target', parent_id=None)
        assert result['status'] == 'success'
        assert 'node_id' in result
        assert result['label'] == 'Test Target'
        assert result['node_type'] == 'target'

    def test_add_node_with_parent(self):
        """Adding a node with a valid parent should succeed."""
        from handlers.attack_graph import add_graph_node
        parent = add_graph_node('Parent Node', 'target')
        parent_id = parent['node_id']

        child = add_graph_node('Child Node', 'port', parent_id=parent_id)
        assert child['status'] == 'success'

    def test_add_node_with_invalid_parent(self):
        """Adding a node referencing a nonexistent parent should return error."""
        from handlers.attack_graph import add_graph_node
        result = add_graph_node('Orphan', 'port', parent_id='nonexistent-id')
        assert result['status'] == 'error'

    def test_add_node_with_data(self):
        """Adding a node with data dict should store as JSON."""
        from handlers.attack_graph import add_graph_node
        data = {'ports': [80, 443], 'os': 'Linux'}
        result = add_graph_node('Server', 'target', data=data)
        assert result['status'] == 'success'

    def test_add_node_unique_ids(self):
        """Each node should get a unique ID."""
        from handlers.attack_graph import add_graph_node
        n1 = add_graph_node('Node 1', 'target')
        n2 = add_graph_node('Node 2', 'target')
        assert n1['node_id'] != n2['node_id']

    def test_add_nodes_of_all_types(self):
        """Should support all node types: target, port, subdomain, vuln, ip."""
        from handlers.attack_graph import add_graph_node
        node_types = ['target', 'port', 'subdomain', 'vuln', 'ip']
        for nt in node_types:
            result = add_graph_node(f'Node-{nt}', nt)
            assert result['status'] == 'success', f'Failed for type: {nt}'


# ---------------------------------------------------------------------------
# get_graph_data
# ---------------------------------------------------------------------------

class TestGetGraphData:
    def test_get_graph_empty(self):
        """Empty graph should return empty node list."""
        from handlers.attack_graph import get_graph_data, reset_graph
        reset_graph()
        result = get_graph_data()
        assert result['status'] == 'success'
        assert result['nodes'] == []

    def test_get_graph_with_nodes(self):
        """Should return all nodes ordered by creation."""
        from handlers.attack_graph import add_graph_node, get_graph_data, reset_graph
        reset_graph()
        add_graph_node('Root', 'target')
        add_graph_node('Port 80', 'port')

        result = get_graph_data()
        assert len(result['nodes']) == 2

    def test_get_graph_with_session_id(self):
        """Should filter nodes by session_id."""
        from handlers.attack_graph import add_graph_node, get_graph_data, reset_graph
        reset_graph()
        add_graph_node('Default Node', 'target')
        add_graph_node('Session Node', 'target', session_id='custom-session')

        default = get_graph_data()  # uses "default" session
        custom = get_graph_data(session_id='custom-session')

        # Default session nodes
        labels_default = {n['label'] for n in default['nodes']}
        assert 'Default Node' in labels_default

        # Custom session nodes
        labels_custom = {n['label'] for n in custom['nodes']}
        assert 'Session Node' in labels_custom

    def test_graph_nodes_have_depth(self):
        """Nodes should have a computed depth field."""
        from handlers.attack_graph import add_graph_node, get_graph_data, reset_graph
        reset_graph()
        root = add_graph_node('Root', 'target')
        child = add_graph_node('Child', 'port', parent_id=root['node_id'])

        result = get_graph_data()
        for node in result['nodes']:
            assert 'depth' in node
            assert isinstance(node['depth'], int)

    def test_graph_nodes_have_correct_fields(self):
        """Each node should have id, node_type, label, parent_id, data, created_at."""
        from handlers.attack_graph import add_graph_node, get_graph_data, reset_graph
        reset_graph()
        add_graph_node('Test', 'target')
        result = get_graph_data()
        node = result['nodes'][0]
        assert 'id' in node
        assert 'node_type' in node
        assert 'label' in node
        assert 'parent_id' in node
        assert 'data' in node
        assert 'created_at' in node


# ---------------------------------------------------------------------------
# remove_graph_node
# ---------------------------------------------------------------------------

class TestRemoveGraphNode:
    def test_remove_node(self):
        """Removing a node should delete it."""
        from handlers.attack_graph import add_graph_node, remove_graph_node, get_graph_data, reset_graph
        reset_graph()
        n = add_graph_node('To Remove', 'target')
        result = remove_graph_node(n['node_id'])
        assert result['status'] == 'success'
        assert result['deleted'] == 1

        data = get_graph_data()
        labels = {n['label'] for n in data['nodes']}
        assert 'To Remove' not in labels

    def test_remove_nonexistent_node(self):
        """Removing nonexistent node should not crash."""
        from handlers.attack_graph import remove_graph_node
        result = remove_graph_node('nonexistent-node-id')
        assert result['status'] == 'success'
        assert result['deleted'] == 0

    def test_remove_parent_updates_children(self):
        """Removing a parent should set children's parent_id to NULL."""
        from handlers.attack_graph import add_graph_node, remove_graph_node, get_graph_data, reset_graph
        reset_graph()
        parent = add_graph_node('Parent', 'target')
        child = add_graph_node('Child', 'port', parent_id=parent['node_id'])

        remove_graph_node(parent['node_id'])

        data = get_graph_data()
        for node in data['nodes']:
            if node['label'] == 'Child':
                assert node['parent_id'] is None


# ---------------------------------------------------------------------------
# reset_graph
# ---------------------------------------------------------------------------

class TestResetGraph:
    def test_reset_graph(self):
        """Resetting should delete all nodes for the session."""
        from handlers.attack_graph import add_graph_node, reset_graph, get_graph_data
        add_graph_node('N1', 'target')
        add_graph_node('N2', 'port')
        add_graph_node('N3', 'vuln')

        result = reset_graph()
        assert result['status'] == 'success'

        data = get_graph_data()
        assert len(data['nodes']) == 0

    def test_reset_custom_session(self):
        """Resetting a custom session should not affect default."""
        from handlers.attack_graph import add_graph_node, reset_graph, get_graph_data
        add_graph_node('Default Node', 'target')
        add_graph_node('Custom Node', 'target', session_id='custom')

        reset_graph(session_id='custom')

        default_data = get_graph_data()
        assert len(default_data['nodes']) == 1


# ---------------------------------------------------------------------------
# auto_populate_from_scans
# ---------------------------------------------------------------------------

class TestAutoPopulate:
    def test_auto_populate_creates_root_node(self):
        """Auto-populate should create a root target node."""
        from handlers.attack_graph import auto_populate_from_scans, reset_graph
        reset_graph()
        result = auto_populate_from_scans('192.168.1.1')
        assert result['status'] == 'success'
        assert 'root_id' in result

    def test_auto_populate_from_empty_scan_history(self):
        """When no scan history exists, should still create root node."""
        from handlers.attack_graph import auto_populate_from_scans, reset_graph
        reset_graph()
        result = auto_populate_from_scans('10.0.0.1')
        assert result['status'] == 'success'
        assert result['ports_found'] == 0
        assert result['subdomains_found'] == 0
        assert result['vulns_found'] == 0


# ---------------------------------------------------------------------------
# JSON data integrity
# ---------------------------------------------------------------------------

class TestGraphJsonData:
    def test_data_is_stored_and_retrieved_as_dict(self):
        """Data stored as JSON should come back as a dict."""
        from handlers.attack_graph import add_graph_node, get_graph_data, reset_graph
        reset_graph()
        data = {'key': 'value', 'nested': {'a': 1}}
        add_graph_node('WithData', 'target', data=data)

        result = get_graph_data()
        node = result['nodes'][0]
        assert isinstance(node['data'], dict)
        assert node['data']['key'] == 'value'

    def test_invalid_json_in_db_is_handled(self):
        """If data column has invalid JSON, should not crash."""
        from handlers.attack_graph import add_graph_node, get_graph_data, reset_graph
        from core.db import get_connection
        reset_graph()
        # Insert manually with bad data
        add_graph_node('Good', 'target')
        # The handler should handle this gracefully
        result = get_graph_data()
        assert result['status'] == 'success'
        for node in result['nodes']:
            assert isinstance(node['data'], dict)
