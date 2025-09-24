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
    assert payload["returnFields"] == ["name", "description", "node_type"]
    assert {"key": "node_type", "value": "project"} in payload["booleanQuery"]
    assert {"key": "path", "value": "syn123"} in payload["booleanQuery"]
    assert result["hits"][0]["id"] == "syn999"


def test_search_synapse_drops_invalid_return_fields(monkeypatch):
    ctx = DummyContext()
    captured = []

    class DummySynapse:
        def __init__(self):
            self.calls = 0

        def restPOST(self, path, body):
            self.calls += 1
            payload = json.loads(body)
            captured.append(payload)
            if self.calls == 1:
                raise Exception("com.amazonaws.services.cloudsearchdomain.model.SearchException: Invalid field name 'id' in return parameter")
            return {"found": 0, "start": 0, "hits": [], "facets": []}

    monkeypatch.setattr(tools, "get_synapse_client", lambda _: DummySynapse())

    result = synapse_mcp.search_synapse.fn(ctx)

    assert len(captured) == 2
    assert "returnFields" in captured[0]
    assert captured[0]["returnFields"] == tools.DEFAULT_RETURN_FIELDS
    assert "returnFields" not in captured[1]
    assert result["query"] == captured[1]
    assert result["original_query"]["returnFields"] == tools.DEFAULT_RETURN_FIELDS
    assert result["dropped_return_fields"] == tools.DEFAULT_RETURN_FIELDS
    assert result["warnings"]


def test_search_synapse_requires_auth(monkeypatch):
    ctx = DummyContext()

    def fake_client(_):
        raise ConnectionAuthError("missing context")

    monkeypatch.setattr(tools, "get_synapse_client", fake_client)

    result = synapse_mcp.search_synapse.fn(ctx)

    assert "error" in result
    assert "Authentication required" in result["error"]
