import json

import synapse_mcp
import synapse_mcp.tools as tools
from synapse_mcp.context_helpers import ConnectionAuthError


class DummyContext:
    pass


def test_search_synapse_builds_payload(monkeypatch):
    ctx = DummyContext()
    captured = {}

    class DummySynapse:
        def restPOST(self, path, body):
            captured["path"] = path
            captured["body"] = json.loads(body)
            return {
                "found": 1,
                "start": 0,
                "hits": [{"id": "syn999", "name": "Cancer Study", "node_type": "project"}],
                "facets": [],
            }

    monkeypatch.setattr(tools, "get_synapse_client", lambda _: DummySynapse())

    result = synapse_mcp.search_synapse.fn(
        ctx,
        query_term="Cancer",
        name="Cancer",
        entity_type="Project",
        parent_id="syn123",
        limit=5,
        offset=2,
    )

    assert captured["path"] == "/search"
    payload = captured["body"]
    assert payload["queryTerm"] == ["Cancer"]
    assert payload["start"] == 2
    assert payload["size"] == 5
    assert {"key": "node_type", "value": "project"} in payload["booleanQuery"]
    assert {"key": "path", "value": "syn123"} in payload["booleanQuery"]
    assert result["hits"][0]["id"] == "syn999"


def test_search_synapse_requires_auth(monkeypatch):
    ctx = DummyContext()

    def fake_client(_):
        raise ConnectionAuthError("missing context")

    monkeypatch.setattr(tools, "get_synapse_client", fake_client)

    result = synapse_mcp.search_synapse.fn(ctx)

    assert "error" in result
    assert "Authentication required" in result["error"]
