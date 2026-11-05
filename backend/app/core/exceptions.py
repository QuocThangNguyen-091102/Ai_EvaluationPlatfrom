"""Lỗi nghiệp vụ và bộ chuyển mọi lỗi thành một định dạng JSON thống nhất.

Định dạng (xem docs/08_api_contracts.md):
    {"error": {"code": "...", "message": "...", "details": ...}}
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

_CODE_BY_STATUS = {
    400: "bad_request",
    401: "unauthorized",
    404: "not_found",
    409: "conflict",
    413: "file_too_large",
    415: "unsupported_file_type",
    422: "validation_error",
    429: "rate_limited",
    502: "provider_error",
}


class AppError(Exception):
    """Lỗi nghiệp vụ có chủ đích. Service ném lỗi này, bộ xử lý bên dưới đổi thành phản hồi HTTP."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Any = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        self.headers = headers


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: Any = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details}},
        headers=headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return error_response(exc.status_code, exc.code, exc.message, exc.details, exc.headers)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"field": ".".join(str(part) for part in err["loc"] if part != "body"), "issue": err["msg"]}
            for err in exc.errors()
        ]
        return error_response(422, "validation_error", "Dữ liệu gửi lên không hợp lệ", details)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _CODE_BY_STATUS.get(exc.status_code, "http_error")
        return error_response(exc.status_code, code, str(exc.detail))

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        # Ghi traceback vào log để debug, nhưng không trả chi tiết nội bộ cho client.
        logger.error("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
        return error_response(500, "internal_error", "Lỗi hệ thống, vui lòng thử lại sau")
