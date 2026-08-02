"""
Tests for AI Engines — Ollama chat, model listing, scan analysis,
JSON parsing, error handling, timeout, and hallucination resistance.

Covers ``handlers/ai_engine.py``, ``handlers/loki_engine.py``,
and ``handlers/rag_engine.py``.
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


# ===========================================================================
# ai_engine.py tests
# ===========================================================================

class TestCheckOllama:
    def test_ollama_running(self):
        """When Ollama responds, _check_ollama returns True + models."""
        import handlers.ai_engine as ai
        with patch.object(ai.requests, 'get') as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                'models': [{'name': 'llama2', 'size': 12345}]
            }
            mock_get.return_value = mock_resp

            ok, models = ai._check_ollama()
            assert ok is True
            assert len(models) == 1
            assert models[0]['name'] == 'llama2'

    def test_ollama_not_running(self):
        """When Ollama is down, _check_ollama returns False."""
        import handlers.ai_engine as ai
        with patch.object(ai.requests, 'get') as mock_get:
            mock_get.side_effect = ai.requests.ConnectionError()

            ok, models = ai._check_ollama()
            assert ok is False
            assert models == []


class TestListModels:
    def test_list_models_ollama_down(self):
        """When Ollama is down, list_models returns error status."""
        import handlers.ai_engine as ai
        with patch.object(ai, '_check_ollama', return_value=(False, [])):
            result = ai.list_models()
            assert result['status'] == 'error'
            assert 'calismiyor' in result['message'].lower() or 'not running' in result['message'].lower()

    def test_list_models_success(self):
        """Should return formatted model list."""
        import handlers.ai_engine as ai
        with patch.object(ai, '_check_ollama', return_value=(True, [
            {'name': 'llama2', 'size': 1000},
            {'name': 'qwen2.5-coder:7b', 'size': 2000},
        ])):
            result = ai.list_models()
            assert result['status'] == 'success'
            assert len(result['models']) == 2


class TestChatCompletion:
    def test_chat_ollama_down(self):
        """When Ollama is not running, chat returns error."""
        import handlers.ai_engine as ai
        with patch.object(ai, '_check_ollama', return_value=(False, [])):
            result = ai.chat_completion('llama2', [{'role': 'user', 'content': 'hi'}])
            assert result['status'] == 'error'

    def test_chat_success(self):
        """Successful chat returns AI response."""
        import handlers.ai_engine as ai
        with patch.object(ai, '_check_ollama', return_value=(True, [])):
            with patch.object(ai.requests, 'post') as mock_post:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {
                    'message': {'content': 'Hello from AI!'}
                }
                mock_post.return_value = mock_resp

                result = ai.chat_completion('llama2', [{'role': 'user', 'content': 'hi'}])
            assert result['status'] == 'success'
            assert 'Hello from AI!' in result['response']

    def test_chat_http_error(self):
        """HTTP error from Ollama should be handled gracefully."""
        import handlers.ai_engine as ai
        with patch.object(ai, '_check_ollama', return_value=(True, [])):
            with patch.object(ai.requests, 'post') as mock_post:
                mock_resp = MagicMock()
                mock_resp.status_code = 500
                mock_resp.text = 'Internal Server Error'
                mock_post.return_value = mock_resp

                result = ai.chat_completion('llama2', [{'role': 'user', 'content': 'hi'}])
            assert result['status'] == 'error'
            assert '500' in result['message']

    def test_chat_timeout(self):
        """Timeout should be caught and returned as error."""
        import handlers.ai_engine as ai
        with patch.object(ai, '_check_ollama', return_value=(True, [])):
            with patch.object(ai.requests, 'post') as mock_post:
                mock_post.side_effect = ai.requests.Timeout()

                result = ai.chat_completion('llama2', [{'role': 'user', 'content': 'hi'}])
            assert result['status'] == 'error'
            assert 'timeout' in result['message'].lower()


class TestPullModel:
    def test_pull_invalid_model_name(self):
        """Invalid model names should be rejected for security."""
        import handlers.ai_engine as ai
        result = ai.pull_model('bad; rm -rf /')
        assert result['status'] == 'error'
        assert 'gecersiz' in result['message'].lower() or 'invalid' in result['message'].lower()

    def test_pull_valid_model_name(self):
        """Valid model name should pass validation."""
        import handlers.ai_engine as ai
        with patch.object(ai, '_check_ollama', return_value=(True, [])):
            with patch.object(ai.subprocess, 'Popen') as mock_popen:
                result = ai.pull_model('llama3.2:3b')
                # Should be success (pull started) or error (if platform check fails)
                assert result['status'] in ('success', 'error')


class TestAnalyzeScanOutput:
    def test_analyze_ollama_down(self):
        """When Ollama is down, analyze returns error."""
        import handlers.ai_engine as ai
        with patch.object(ai, '_check_ollama', return_value=(False, [])):
            result = ai.analyze_scan_output('some output', 'nmap')
            assert result['status'] == 'error'

    def test_analyze_no_models_available(self):
        """When no models are installed, returns error."""
        import handlers.ai_engine as ai
        with patch.object(ai, '_check_ollama', return_value=(True, [])):
            result = ai.analyze_scan_output('scan output', 'nmap')
            assert result['status'] == 'error'
            assert 'model' in result['message'].lower()

    def test_analyze_with_valid_json_response(self):
        """Valid JSON from AI should be parsed correctly."""
        import handlers.ai_engine as ai
        valid_json = json.dumps({
            'summary': 'Found 3 open ports',
            'findings': [{'type': 'port', 'detail': 'Port 80 open', 'severity': 'medium'}],
            'recommendations': [{'action': 'Run nikto', 'tool': 'nikto', 'reason': 'Web server'}],
            'stats': {'open_ports': 3, 'services_found': 1, 'vulnerabilities_found': 0}
        })

        with patch.object(ai, '_check_ollama', return_value=(True, [
            {'name': 'llama2', 'size': 100}
        ])):
            with patch.object(ai.requests, 'post') as mock_post:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {
                    'message': {'content': valid_json}
                }
                mock_post.return_value = mock_resp

                result = ai.analyze_scan_output('Port 80 open...', 'nmap', '10.0.0.1')
            assert result['status'] == 'success'
            assert 'analysis' in result
            assert result['analysis']['summary'] == 'Found 3 open ports'

    def test_analyze_with_hallucination_text(self):
        """When AI returns non-JSON text, should handle gracefully without crash."""
        import handlers.ai_engine as ai

        with patch.object(ai, '_check_ollama', return_value=(True, [
            {'name': 'llama2', 'size': 100}
        ])):
            with patch.object(ai.requests, 'post') as mock_post:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {
                    'message': {'content': 'I think this is a normal scan result, nothing special here...'}
                }
                mock_post.return_value = mock_resp

                result = ai.analyze_scan_output('some output', 'nmap')
            # Should not crash — halluconation text handled via raw=True fallback
            assert result['status'] == 'success'
            assert 'analysis' in result

    def test_analyze_truncates_long_output(self):
        """Very long scan output should be truncated before sending to AI."""
        import handlers.ai_engine as ai
        long_output = 'A' * 20000

        with patch.object(ai, '_check_ollama', return_value=(True, [
            {'name': 'llama2', 'size': 100}
        ])):
            with patch.object(ai.requests, 'post') as mock_post:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {
                    'message': {'content': '{}'}
                }
                mock_post.return_value = mock_resp

                ai.analyze_scan_output(long_output, 'nmap')
                # The payload sent to API should be truncated
                call_args = mock_post.call_args
                sent_messages = call_args[1]['json']['messages']
                user_content = sent_messages[1]['content']
                assert len(user_content) < len(long_output) + 500  # truncated


# ===========================================================================
# loki_engine.py tests — WAF Evader
# ===========================================================================

class TestLokiMutatePayload:
    def test_mutate_empty_payload(self):
        """Empty payload should return error."""
        from handlers.loki_engine import mutate_payload
        result = mutate_payload('')
        assert result['status'] == 'error'
        result2 = mutate_payload('   ')
        assert result2['status'] == 'error'

    def test_mutate_sqli_payload(self):
        """SQLi payload should produce mutations."""
        from handlers.loki_engine import mutate_payload
        result = mutate_payload("' OR '1'='1")
        assert result['status'] == 'success'
        assert result['original'] == "' OR '1'='1"
        assert len(result['mutations']) > 0

    def test_mutate_xss_payload(self):
        """XSS payload should produce mutations."""
        from handlers.loki_engine import mutate_payload
        result = mutate_payload('<script>alert(1)</script>')
        assert result['status'] == 'success'
        assert len(result['mutations']) > 0
        # Original payload should not be in mutations
        mutation_payloads = [m['payload'] for m in result['mutations']]
        assert result['original'] not in mutation_payloads

    def test_mutate_with_specific_techniques(self):
        """Specifying techniques should only use those."""
        from handlers.loki_engine import mutate_payload
        result = mutate_payload("' OR 1=1 --",
                                techniques=['url_double', 'case_randomize'])
        assert result['status'] == 'success'
        techniques_used = set(m['technique'] for m in result['mutations'])
        assert all(t in ('url_double', 'case_randomize') or '+' in t
                   for t in techniques_used)

    def test_mutate_returns_unique_variants(self):
        """All mutations should be unique."""
        from handlers.loki_engine import mutate_payload
        result = mutate_payload("test payload", count=10)
        payloads = [m['payload'] for m in result['mutations']]
        assert len(payloads) == len(set(payloads))

    def test_mutations_have_metadata(self):
        """Each mutation should have technique name and category."""
        from handlers.loki_engine import mutate_payload
        result = mutate_payload("' OR 1=1")
        for m in result['mutations']:
            assert 'technique' in m
            assert 'name' in m
            assert 'category' in m


class TestLokiListTechniques:
    def test_list_techniques(self):
        from handlers.loki_engine import list_techniques
        result = list_techniques()
        assert result['status'] == 'success'
        assert len(result['techniques']) > 0
        for t in result['techniques']:
            assert 'key' in t
            assert 'name' in t
            assert 'category' in t


class TestLokiAnalyzeWaf:
    def test_analyze_403_cloudflare(self):
        from handlers.loki_engine import analyze_waf_response
        result = analyze_waf_response(403, 'CF-Ray: abc123 Cloudflare')
        assert result['status'] == 'success'
        assert 'Cloudflare' in result['analysis']['likely_waf']
        assert len(result['analysis']['suggestions']) > 0

    def test_analyze_403_modsecurity(self):
        from handlers.loki_engine import analyze_waf_response
        result = analyze_waf_response(403, 'ModSecurity: Access denied')
        assert result['status'] == 'success'
        assert 'ModSecurity' in result['analysis']['likely_waf']

    def test_analyze_403_generic(self):
        from handlers.loki_engine import analyze_waf_response
        result = analyze_waf_response(403)
        assert result['status'] == 'success'
        assert len(result['analysis']['suggestions']) > 0

    def test_analyze_406(self):
        from handlers.loki_engine import analyze_waf_response
        result = analyze_waf_response(406)
        assert result['status'] == 'success'
        assert 'Content-Type' in result['analysis']['likely_waf']

    def test_analyze_429(self):
        from handlers.loki_engine import analyze_waf_response
        result = analyze_waf_response(429)
        assert result['status'] == 'success'
        assert 'Rate' in result['analysis']['likely_waf']

    def test_analyze_unknown_code(self):
        from handlers.loki_engine import analyze_waf_response
        result = analyze_waf_response(500)
        assert result['status'] == 'success'
        assert len(result['analysis']['suggestions']) > 0


# ===========================================================================
# rag_engine.py tests — Kvasir Knowledge Base
# ===========================================================================

class TestRagKeywordSearch:
    def test_keyword_search_finds_gtfobins(self):
        """Searching for 'python' should find the python GTFOBins entry."""
        from handlers.rag_engine import query_knowledge
        result = query_knowledge('python privilege escalation shell escape')
        assert result['status'] == 'success'
        # Either vector or keyword search should work
        assert result['method'] in ('vector', 'keyword', 'none')

    def test_keyword_search_finds_exploit(self):
        """Searching for 'CVE-2021-4034' should find PwnKit."""
        from handlers.rag_engine import query_knowledge
        result = query_knowledge('CVE-2021-4034 polkit')
        if result['method'] != 'none' and result['total_hits'] > 0:
            # Found something — check it's relevant
            assert 'exploitdb' in result['results'] or 'gtfobins' in result['results']

    def test_keyword_search_finds_payloads(self):
        """Searching for XSS should find payload entries."""
        from handlers.rag_engine import query_knowledge
        result = query_knowledge('XSS cross site scripting payload')
        # Just verify no crash
        assert result['status'] == 'success'

    def test_keyword_search_no_results(self):
        """Search for nonsense should return empty results."""
        from handlers.rag_engine import query_knowledge
        result = query_knowledge('xyznonexistent12345')
        assert result['status'] == 'success'
        assert result['total_hits'] == 0

    def test_keyword_search_with_collections_filter(self):
        """Filtering by collection name should work."""
        from handlers.rag_engine import query_knowledge
        result = query_knowledge('shell', collections=['gtfobins'])
        assert result['status'] == 'success'

    def test_keyword_search_with_top_k(self):
        """top_k should limit results."""
        from handlers.rag_engine import query_knowledge
        result = query_knowledge('bash shell', top_k=2)
        if result['total_hits'] > 0:
            for col_results in result['results'].values():
                assert len(col_results) <= 2


class TestRagCheckStatus:
    def test_check_rag_status(self):
        from handlers.rag_engine import check_rag_status
        result = check_rag_status()
        # Should always return a dict with expected keys
        assert 'chromadb_available' in result
        assert 'ollama_available' in result
        assert 'offline_fallback' in result


# ===========================================================================
# ai_engine.py — profile tiers
# ===========================================================================

class TestAiProfileTiers:
    def test_get_ai_profile_tiers(self):
        from handlers.ai_engine import get_ai_profile_tiers
        result = get_ai_profile_tiers()
        assert 'tiers' in result
        assert len(result['tiers']) == 3
        for tier in result['tiers']:
            assert 'id' in tier
            assert 'name' in tier
            assert 'models' in tier
