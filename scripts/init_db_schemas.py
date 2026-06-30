import asyncio
import logging
import os
import sys
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres_secure_2026@localhost:5432/procuremind_db",
)

from infra.database import Base, engine


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("schema_compiler")

MAX_ATTEMPTS = 5
RETRY_DELAY_SECONDS = 2
SYSTEM_TENANT = "SYSTEM_LOCAL_DOCKER"


class DatabaseLayerException(Exception):
    """Raised when the local PostgreSQL schema compiler cannot initialize metadata."""


def create_all_with_engine(engine) -> None:
    Base.metadata.create_all(bind=engine)


async def create_database_schemas() -> None:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            async with engine.begin() as connection:
                await connection.run_sync(create_all_with_engine)
            logger.info(
                "[SCHEMA_INIT_SUCCESS] Tenant: %s | Scope: init_db_schemas | Trace Context: "
                "Materialized SQLAlchemy metadata, including session_state_registry.",
                SYSTEM_TENANT,
            )
            return
        except (ConnectionError, TimeoutError, OSError, SQLAlchemyError) as exc:
            logger.warning(
                "[SCHEMA_INIT_RETRY] Tenant: %s | Scope: init_db_schemas | Trace Context: "
                "PostgreSQL connection attempt %s/%s failed: %s",
                SYSTEM_TENANT,
                attempt,
                MAX_ATTEMPTS,
                exc,
            )
            if attempt == MAX_ATTEMPTS:
                raise DatabaseLayerException(
                    "PostgreSQL schema initialization failed after retry budget was exhausted."
                ) from exc
            await asyncio.sleep(RETRY_DELAY_SECONDS)
        except Exception as exc:
            logger.error(
                "[SCHEMA_INIT_FAILURE] Tenant: %s | Scope: init_db_schemas | Trace Context: "
                "Unexpected schema compiler failure: %s",
                SYSTEM_TENANT,
                exc,
            )
            raise DatabaseLayerException("Unexpected PostgreSQL schema initialization failure.") from exc
    raise DatabaseLayerException("PostgreSQL schema initialization exited without a terminal state.")


if __name__ == "__main__":
    asyncio.run(create_database_schemas())
