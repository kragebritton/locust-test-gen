from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Iterable, List


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
    client_comment = (
        "client: FastHttpSession" if client_type == LocustClientType.FAST_HTTP else "client: HttpSession"
    )

    lines: List[str] = [
        "from typing import Any, Dict",
        "",
        "from locust import HttpUser, FastHttpUser, between, task",
        "",
        f"class {user_class_name}({client_import}):",
        "    \"\"\"\n    Auto-generated skeleton tasks.\n\n"
        "    Fill in payloads and sequencing based on your domain logic.\n"
        "    You can move validated data between tasks using shared attributes.\n"
        "    \"\"\"",
        "    wait_time = between(1, 5)",
        f"    host = \"{host}\"",
        "",
    ]

    for op in operations:
        lines.extend(_render_operation_task(op, task_weight))

    if not operations:
        lines.append("    # No operations were discovered in the provided OpenAPI document.")

    return "\n".join(lines) + "\n"


def _render_operation_task(operation: Operation, weight: int) -> List[str]:
    method_name = _safe_method_name(operation.operation_id)
    lines = [
        "    @task({})".format(weight),
        f"    def {method_name}(self) -> None:",
        f"        \"\"\"{operation.summary}\"\"\"",
        "        # TODO: Replace placeholder payloads with schema-aware data",
    ]

    if operation.has_request_body:
        lines.extend(
            [
                "        payload: Dict[str, Any] = {",
                "            # populate request body using the schema in the OpenAPI document",
                "        }",
            ]
        )
    else:
        lines.append("        payload = None")

    param_comments = _build_param_comments(operation)
    if param_comments:
        lines.append(f"        # Parameters: {param_comments}")

    request_name = f"{operation.method} {operation.path}"
    lines.extend(
        [
            "        with self.client.request(",
            f"            \"{operation.method}\",",
            f"            \"{operation.path}\",",
            f"            name=\"{request_name}\",",
            "            json=payload,",
            "            params={},",
            "        ) as response:",
            "            response.raise_for_status()",
            "            # TODO: capture response data to chain into subsequent tasks",
        ]
    )

    return lines + [""]


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
