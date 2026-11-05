import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.exceptions import AppError, register_exception_handlers


class _Payload(BaseModel):
    email: str
    age: int


@pytest.fixture
def error_client() -> TestClient:
    """App nhỏ chỉ để kiểm tra bộ xử lý lỗi, không phụ thuộc DB."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/app-error")
    def raise_app_error():
        raise AppError(409, "conflict", "Email đã tồn tại", details={"field": "email"})

    @app.get("/http-error")
    def raise_http_error():
        raise HTTPException(status_code=404, detail="Không tìm thấy")

    @app.post("/validate")
    def validate(payload: _Payload):
        return payload

    @app.get("/boom")
    def boom():
        raise RuntimeError("secret internal detail")

    return TestClient(app, raise_server_exceptions=False)


def _assert_error_shape(body):
    assert set(body.keys()) == {"error"}
    assert set(body["error"].keys()) == {"code", "message", "details"}


def test_app_error_uses_standard_format(error_client):
    response = error_client.get("/app-error")

    assert response.status_code == 409
    body = response.json()
    _assert_error_shape(body)
    assert body["error"]["code"] == "conflict"
    assert body["error"]["details"] == {"field": "email"}


def test_http_exception_is_mapped_to_standard_format(error_client):
    response = error_client.get("/http-error")

    assert response.status_code == 404
    body = response.json()
    _assert_error_shape(body)
    assert body["error"]["code"] == "not_found"


def test_validation_error_lists_fields(error_client):
    response = error_client.post("/validate", json={"email": "a@b.c", "age": "không phải số"})

    assert response.status_code == 422
    body = response.json()
    _assert_error_shape(body)
    assert body["error"]["code"] == "validation_error"
    assert [item["field"] for item in body["error"]["details"]] == ["age"]


def test_unexpected_error_does_not_leak_internal_detail(error_client):
    response = error_client.get("/boom")

    assert response.status_code == 500
    body = response.json()
    _assert_error_shape(body)
    assert body["error"]["code"] == "internal_error"
    assert "secret internal detail" not in response.text
