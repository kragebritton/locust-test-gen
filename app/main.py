from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator

from .generator import LocustClientType, generate_locustfile

app = FastAPI(title="Locust Test Generator", version="0.1.0")


class GenerateRequest(BaseModel):
    openapi: Dict[str, Any] = Field(..., description="Parsed OpenAPI specification")
    host: str = Field(..., description="Target host for Locust to load test, e.g. https://api.example.com")
    client_type: LocustClientType = Field(
        LocustClientType.FAST_HTTP, description="Generate users backed by FastHttpUser or HttpUser"
    )
    user_class_name: str = Field("GeneratedUser", description="Name of the generated Locust user class")
    task_weight: int = Field(1, ge=1, description="Default weight applied to every generated task")

    @validator("openapi")
    def ensure_paths(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        if "paths" not in value:
            raise ValueError("The OpenAPI document must contain a paths object")
        return value


class GenerateResponse(BaseModel):
    locustfile: str = Field(..., description="Python source code for a generated locustfile")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest) -> GenerateResponse:
    try:
        locustfile = generate_locustfile(
            req.openapi,
            host=req.host,
            client_type=req.client_type,
            user_class_name=req.user_class_name,
            task_weight=req.task_weight,
        )
    except Exception as exc:  # pragma: no cover - surfaced to clients
        raise HTTPException(status_code=400, detail=str(exc))

    return GenerateResponse(locustfile=locustfile)
