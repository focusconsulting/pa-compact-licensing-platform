from enum import StrEnum

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorCode(StrEnum):
    InvalidToken = 'INVALID_TOKEN'
    UserNotFound = 'USER_NOT_FOUND'
    UserInactive = 'USER_INACTIVE'
    ValidationError = 'VALIDATION_ERROR'
    HttpError = 'HTTP_ERROR'


class ErrorResponse(BaseModel):
    code: ErrorCode
    details: list[str]


class AppError(HTTPException):
    """Application error with a machine-readable code and a list of detail messages."""

    def __init__(self, status_code: int, code: ErrorCode, details: list[str]) -> None:
        super().__init__(status_code=status_code)
        self.code = code
        self.details = details


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(code=exc.code, details=exc.details).model_dump(),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Catch-all for plain HTTPExceptions raised by FastAPI or third-party middleware."""
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(code=ErrorCode.HttpError, details=[detail]).model_dump(),
        headers=getattr(exc, 'headers', None),
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [f'{".".join(str(loc) for loc in e["loc"])}: {e["msg"]}' for e in exc.errors()]
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(code=ErrorCode.ValidationError, details=details).model_dump(),
    )
