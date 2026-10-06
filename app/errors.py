import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.errors")

# Maps an HTTP status to a short, stable code that client apps can check.
STATUS_TO_CODE = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
}


def error_response(status_code, code, message, fields=None, headers=None):
    body = {"error": {"code": code, "message": message}}
    if fields:
        body["error"]["fields"] = fields
    return JSONResponse(status_code=status_code, content=body, headers=headers)


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    code = STATUS_TO_CODE.get(exc.status_code, "error")
    # exc.headers matters: 401 responses must keep "WWW-Authenticate: Bearer".
    return error_response(exc.status_code, code, str(exc.detail), headers=exc.headers)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    fields = []
    for err in exc.errors():
        location = ".".join(str(part) for part in err["loc"])
        message = err["msg"].removeprefix("Value error, ")
        fields.append({"field": location, "message": message})
    return error_response(422, "validation_error", "Request validation failed", fields=fields)


async def integrity_error_handler(request: Request, exc: IntegrityError):
    # The database rejected the write (e.g. a duplicate email). We log the real
    # reason but never send database text to the client.
    logger.warning("Integrity error on %s %s: %s", request.method, request.url.path, exc.orig)
    return error_response(409, "conflict", "The request conflicts with existing data")


async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return error_response(500, "internal_error", "Something went wrong on our side")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)