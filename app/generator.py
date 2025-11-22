from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Iterable, List

from jinja2 import Environment


class LocustClientType(str, Enum):
    FAST_HTTP = "fast_http"
    REQUESTS = "requests"


@dataclass
class Operation:
    path: str
    method: str
    operation_id: str
    summary: str
    has_request_body: bool
    path_params: List[str]
    query_params: List[str]


def parse_operations(spec: Dict[str, Any]) -> List[Operation]:
    paths = spec.get("paths", {})
    operations: List[Operation] = []

    for raw_path, methods in paths.items():
        if not isinstance(methods, dict):
            continue

        for method, operation in methods.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete", "options", "head"}:
                continue

            op_id = _derive_operation_id(operation, method, raw_path)
            summary = operation.get("summary") or operation.get("description") or op_id
            has_request_body = "requestBody" in operation

            params = _collect_parameters(operation)
            path_params = [param[0] for param in params if param[1] == "path"]
            query_params = [param[0] for param in params if param[1] == "query"]

            operations.append(
                Operation(
                    path=raw_path,
                    method=method.upper(),
                    operation_id=op_id,
                    summary=summary,
                    has_request_body=has_request_body,
                    path_params=path_params,
                    query_params=query_params,
                )
            )

    return operations


def generate_locustfile(
    spec: Dict[str, Any],
    *,
    host: str,
    client_type: LocustClientType = LocustClientType.FAST_HTTP,
    user_class_name: str = "GeneratedUser",
    task_weight: int = 1,
) -> str:
    operations = parse_operations(spec)
    client_import = "FastHttpUser" if client_type == LocustClientType.FAST_HTTP else "HttpUser"

    return LOCUST_TEMPLATE.render(
        host=host,
        client_import=client_import,
        operations=[
            {
                "method_name": _safe_method_name(op.operation_id),
                "summary": op.summary,
                "has_request_body": op.has_request_body,
                "param_comments": _build_param_comments(op),
                "method": op.method,
                "path": op.path,
                "request_name": f"{op.method} {op.path}",
            }
            for op in operations
        ],
        user_class_name=user_class_name,
        task_weight=task_weight,
    )


def _derive_operation_id(operation: Dict[str, Any], method: str, path: str) -> str:
    if isinstance(operation, dict) and "operationId" in operation:
        return operation["operationId"]

    sanitized_path = path.strip("/").replace("/", "_").replace("{", "").replace("}", "")
    sanitized_path = sanitized_path or "root"
    return f"{method.lower()}_{sanitized_path}"


def _collect_parameters(operation: Dict[str, Any]) -> Iterable[tuple[str, str]]:
    parameters = operation.get("parameters") or []
    for param in parameters:
        name = param.get("name") or "unknown"
        location = param.get("in") or "unknown"
        yield name, location


def _build_param_comments(operation: Operation) -> str:
    parts: List[str] = []
    if operation.path_params:
        parts.append(f"path: {', '.join(operation.path_params)}")
    if operation.query_params:
        parts.append(f"query: {', '.join(operation.query_params)}")
    return "; ".join(parts)


def _safe_method_name(operation_id: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in operation_id)
    if cleaned and cleaned[0].isdigit():
        cleaned = f"op_{cleaned}"
    return cleaned or "unnamed_operation"


LOCUST_TEMPLATE = Environment(trim_blocks=True, lstrip_blocks=True).from_string(
    '''
from typing import Any, Dict

from locust import HttpUser, FastHttpUser, between, task


class {{ user_class_name }}({{ client_import }}):
    """
    Auto-generated skeleton tasks.

    Fill in payloads and sequencing based on your domain logic.
    You can move validated data between tasks using shared attributes.
    """

    wait_time = between(1, 5)
    host = "{{ host }}"

{% if not operations %}
    # No operations were discovered in the provided OpenAPI document.
{% endif %}
{% for op in operations %}
    @task({{ task_weight }})
    def {{ op.method_name }}(self) -> None:
        """{{ op.summary }}"""
        # TODO: Replace placeholder payloads with schema-aware data
        payload{% if op.has_request_body %}: Dict[str, Any] = {
            # populate request body using the schema in the OpenAPI document
        }{% else %} = None{% endif %}
        {% if op.param_comments %}# Parameters: {{ op.param_comments }}
        {% endif %}with self.client.request(
            "{{ op.method }}",
            "{{ op.path }}",
            name="{{ op.request_name }}",
            json=payload,
            params={},
        ) as response:
            response.raise_for_status()
            # TODO: capture response data to chain into subsequent tasks

{% endfor %}
'''
)
