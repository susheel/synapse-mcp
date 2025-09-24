from fastmcp.server.context import request_ctx

import synapse_mcp


class DummyContext:
    def __init__(self):
        self._state = {}

    def get_state(self, key, default=None):
        return self._state.get(key, default)

    def set_state(self, key, value):
        self._state[key] = value


def test_get_entity_resource_requires_context():
    result = synapse_mcp.get_entity_by_id_or_name.fn('syn123')
    assert 'No active request context' in result['error']


def test_get_entity_resource_uses_context(monkeypatch):
    ctx = DummyContext()
    token = request_ctx.set(ctx)

    def fake_get_entity(entity_id, ctx_arg):
        assert ctx_arg is ctx
        return {'id': entity_id, 'type': 'Project'}

    monkeypatch.setattr(synapse_mcp.get_entity, 'fn', fake_get_entity)

    try:
        result = synapse_mcp.get_entity_by_id_or_name.fn('syn123')
    finally:
        request_ctx.reset(token)

    assert result == {'id': 'syn123', 'type': 'Project'}


def test_get_entity_resource_uses_search(monkeypatch):
    ctx = DummyContext()
    token = request_ctx.set(ctx)

    captured = {}

    def fake_search(ctx_arg, **kwargs):
        captured['ctx'] = ctx_arg
        captured['kwargs'] = kwargs
        return {
            'found': 1,
            'start': 0,
            'hits': [{'id': 'syn999', 'name': 'Example Entity', 'node_type': 'project'}],
            'facets': [],
            'query': kwargs,
        }

    def fake_get_entity(entity_id, ctx_arg):
        assert ctx_arg is ctx
        return {'id': entity_id, 'name': 'Example Entity', 'type': 'Project'}

    monkeypatch.setattr(synapse_mcp.search_synapse, 'fn', fake_search)
    monkeypatch.setattr(synapse_mcp.get_entity, 'fn', fake_get_entity)

    try:
        result = synapse_mcp.get_entity_by_id_or_name.fn('Example Entity')
    finally:
        request_ctx.reset(token)

    assert result == {'id': 'syn999', 'name': 'Example Entity', 'type': 'Project'}
    assert captured['ctx'] is ctx
    assert captured['kwargs']['name'] == 'Example Entity'
