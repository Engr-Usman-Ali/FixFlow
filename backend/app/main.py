"""FixFlow API entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError, OperationalError

from . import models  # noqa: F401  (registers every table on Base.metadata)
from .config import settings
from .database import Base, SessionLocal, engine
from .routers import ai, audit, auth, equipment, notifications, organization, reports, requests, users
from .services.org_setup import sync_rbac

logging.basicConfig(level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("fixflow")


def check_schema() -> None:
    """Stop early with a clear message if the database still has tables from an older FixFlow."""
    tables = inspect(engine)
    if tables.has_table("users"):
        columns = {c["name"] for c in tables.get_columns("users")}
        if "organization_id" not in columns or "password_salt" not in columns:
            raise SystemExit(
                "\nThe database has tables from an older FixFlow version.\n"
                "Reset it once with:  python -m app.manage reset-db --yes\n"
            )


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        logger.info("Step 1/2: connecting to the database and checking tables...")
        check_schema()
        Base.metadata.create_all(bind=engine)  # creates any missing tables
        with SessionLocal() as db:
            logger.info("Step 2/2: syncing roles and permissions...")
            sync_rbac(db)
    except OperationalError as exc:
        raise SystemExit(
            f"\nDatabase problem during start-up.\n"
            f"Check that PostgreSQL is running, the user/password/database in DATABASE_URL exist, and no other\n"
            f"FixFlow backend or pgAdmin query is holding the tables (restart PostgreSQL if unsure).\nDetails: {exc.orig}\n"
        ) from None
    logger.info("FixFlow API ready (%s). AI suggestions: %s", settings.app_env, "on" if settings.ai_configured else "off")
    yield


app = FastAPI(
    title="FixFlow API",
    version="2.0.0",
    description="Maintenance and repair management. Multi-company, role-based access.",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None,
    openapi_url=None if settings.is_production else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def limits_and_headers(request: Request, call_next):
    """IR-012: reject oversized bodies. Adds basic security headers to every response."""
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > settings.max_request_bytes:
        return JSONResponse(status_code=413, content={"detail": "The request is too large."})
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


for module in (auth, users, organization, requests, equipment, notifications, reports, audit, ai):
    app.include_router(module.router, prefix=settings.api_prefix)


@app.get(f"{settings.api_prefix}/health", tags=["health"])
def health():
    return {"status": "ok"}


# ------------------------------------------------------------ error handling ---
@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    """Explain which fields are wrong, in plain language (FR-013, NFR-USA-003)."""
    problems = []
    for err in exc.errors():
        field = " ".join(str(p) for p in err.get("loc", [])[1:]) or "request"
        problems.append({"field": field, "message": err.get("msg", "is not valid")})
    return JSONResponse(status_code=422, content={"detail": problems})


@app.exception_handler(IntegrityError)
async def integrity_error(_: Request, exc: IntegrityError):
    logger.warning("Integrity error: %s", type(exc.orig).__name__)
    return JSONResponse(status_code=409, content={"detail": "This conflicts with an existing record. Refresh and try again."})


@app.exception_handler(Exception)
async def unhandled_error(_: Request, exc: Exception):
    """Log details on the server; return a safe message without stack traces or secrets (FR-103)."""
    logger.exception("Unhandled error", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong on the server. Please try again."})
