import pytest

from app.generator import LocustClientType, generate_locustfile, parse_operations


@pytest.fixture()
def sample_spec():
    return {
        "openapi": "3.0.0",
        "paths": {
            "/items": {
                "get": {"summary": "List items", "operationId": "listItems"},
                "post": {
                    "summary": "Create item",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}},
                },
            },
            "/items/{item_id}": {
                "get": {
                    "summary": "Get item",
                    "parameters": [{"name": "item_id", "in": "path"}],
                }
            },
        },
    }


def test_parse_operations_discovers_methods(sample_spec):
    operations = parse_operations(sample_spec)
    assert {op.operation_id for op in operations} >= {"listItems", "post_items", "get_items_item_id"}


def test_generate_locustfile_creates_tasks(sample_spec):
    output = generate_locustfile(sample_spec, host="https://api.example.com", client_type=LocustClientType.REQUESTS)
    assert "class GeneratedUser(HttpUser):" in output
    assert "def listItems" in output
    assert "def post_items" in output
    assert "json=payload" in output  # post includes placeholder body
    assert '"/items/{item_id}"' in output


def test_generate_locustfile_defaults_to_fast_http(sample_spec):
    output = generate_locustfile(sample_spec, host="https://api.example.com")
    assert "class GeneratedUser(FastHttpUser):" in output
