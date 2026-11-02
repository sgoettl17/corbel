import json
from pathlib import Path

import pytest
from client import ProcoreClient, ProcoreError
from config import Config
from corbel_mcp import build_server
from spec_index import SpecIndex
from tools import encode_query, expand_path


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, method, url, headers, data, timeout):
        self.calls.append((method, url, dict(headers), data))
        status, body, resp_headers = self.responses.pop(0)
        return status, resp_headers, json.dumps(body).encode()


SPEC_DIR = Path(__file__).resolve().parent.parent / "spec" / "index"
TOKEN = (200, {"access_token": "tok", "expires_in": 3600}, {})


def make_server(responses, **config):
    cfg = Config(client_id="id", client_secret="secret", company_id="42", **config)
    transport = FakeTransport([TOKEN, *responses])
    server = build_server(cfg, ProcoreClient(cfg, transport, sleep=lambda _: None))
    return server, transport


def call(server, name, arguments):
    reply = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
    )
    return reply["result"]


def test_index_covers_all_rest_operations():
    manifest = json.loads((SPEC_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert len(SpecIndex().operations) == manifest["operation_count"] > 3000


def test_initialize_and_tool_list_are_read_only_by_default():
    server, _ = make_server([])
    init = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
        }
    )
    assert init["result"]["serverInfo"]["name"] == "corbel"
    listed = server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]
    names = {t["name"] for t in listed}
    assert names == {"corbel_search_endpoints", "corbel_describe_endpoint", "corbel_get"}
    assert all(t["annotations"]["readOnlyHint"] for t in listed)


def test_write_tools_registered_only_when_enabled():
    server, _ = make_server([], allow_writes=True)
    for name in ("corbel_create", "corbel_update", "corbel_delete"):
        tool = server.tools[name].describe()
        assert tool["annotations"]["destructiveHint"] is True
        assert tool["annotations"]["readOnlyHint"] is False


def test_tool_names_and_titles():
    server, _ = make_server([], allow_writes=True)
    for tool in server.tools.values():
        assert len(tool.name) <= 64
        assert tool.title


def test_search_finds_rfis():
    server, _ = make_server([])
    result = call(server, "corbel_search_endpoints", {"query": "rfis", "method": "get"})
    assert not result["isError"]
    assert "rfis" in result["content"][0]["text"].lower()


def test_get_calls_procore_with_headers_and_path():
    server, transport = make_server([(200, [{"id": 1}], {})])
    op = next(
        o
        for o in SpecIndex().operations.values()
        if o["p"] == "/rest/v1.0/companies" and o["m"] == "get"
    )
    result = call(server, "corbel_get", {"operation_id": op["id"], "query": {"per_page": 5}})
    assert json.loads(result["content"][0]["text"]) == [{"id": 1}]
    method, url, headers, _ = transport.calls[1]
    assert (method, url) == ("GET", "https://api.procore.com/rest/v1.0/companies?per_page=5")
    assert headers["Procore-Company-Id"] == "42"
    assert headers["Authorization"] == "Bearer tok"


def test_get_rejects_write_operation():
    server, _ = make_server([])
    post = next(o for o in SpecIndex().operations.values() if o["m"] == "post")
    result = call(server, "corbel_get", {"operation_id": post["id"]})
    assert result["isError"]
    assert "POST" in result["content"][0]["text"]


def test_retry_on_rate_limit_then_succeed():
    server, transport = make_server([(429, {}, {"Retry-After": "1"}), (200, [], {})])
    op = next(
        o
        for o in SpecIndex().operations.values()
        if o["p"] == "/rest/v1.0/companies" and o["m"] == "get"
    )
    result = call(server, "corbel_get", {"operation_id": op["id"]})
    assert not result["isError"]
    assert len(transport.calls) == 3


def test_bad_credentials_message_has_no_secret():
    cfg = Config(client_id="id", client_secret="topsecret")
    client = ProcoreClient(cfg, FakeTransport([(401, {}, {})]), sleep=lambda _: None)
    with pytest.raises(ProcoreError) as exc:
        client.request("GET", "/rest/v1.0/companies")
    assert "topsecret" not in str(exc.value)


def test_expand_path_encodes_and_requires_params():
    op = {"p": "/rest/v1.0/projects/{project_id}/rfis", "pp": ["project_id"]}
    assert expand_path(op, {"project_id": "a/b"}).endswith("/projects/a%2Fb/rfis")
    with pytest.raises(Exception, match="Missing path parameters"):
        expand_path(op, {})


def test_encode_query_nested_and_lists():
    assert encode_query({"filters": {"status": "open"}, "ids": [1, 2], "x": True}) == [
        ("filters[status]", "open"),
        ("ids[]", "1"),
        ("ids[]", "2"),
        ("x", "true"),
    ]


def test_encode_query_does_not_double_array_suffix():
    assert encode_query({"filters[id][]": [1, 2]}) == [
        ("filters[id][]", "1"),
        ("filters[id][]", "2"),
    ]


def test_unknown_method_returns_jsonrpc_error():
    server, _ = make_server([])
    assert server.handle({"jsonrpc": "2.0", "id": 9, "method": "nope"})["error"]["code"] == -32601
    assert server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
