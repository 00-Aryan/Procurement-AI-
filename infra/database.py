import os
import uuid
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.exc import SQLAlchemyError


class TenantContextError(Exception):
    """Exception raised for errors in the tenant context verification or missing context."""
    pass


class DatabaseLayerError(Exception):
    """Exception raised for database connection timeouts, transaction failures, and query errors."""
    pass


def normalize_asyncpg_database_url(raw_url: str) -> tuple[str, dict[str, Any]]:
    if raw_url.startswith("postgresql://"):
        normalized_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif raw_url.startswith("postgres://"):
        normalized_url = raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
    else:
        normalized_url = raw_url

    parsed_url = make_url(normalized_url)
    query = dict(parsed_url.query)
    sslmode = query.pop("sslmode", None)
    connect_args = {"ssl": sslmode} if sslmode else {}
    return parsed_url.set(query=query).render_as_string(hide_password=False), connect_args


raw_db_url = os.getenv("DATABASE_URL")
if not raw_db_url:
    if os.getenv("ENV_MODE") == "production":
        from core.config_parser import log_and_raise, ProcurementException
        class SecurityConfigurationError(ProcurementException):
            pass
        log_and_raise(
            SecurityConfigurationError,
            "CRITICAL_SECURITY_FAULT",
            "SYSTEM_GLOBAL",
            "database_startup",
            "Production environment detected but vital DATABASE_URL is missing."
        )
    else:
        raw_db_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/procuremind"

DATABASE_URL, DATABASE_CONNECT_ARGS = normalize_asyncpg_database_url(raw_db_url)


# Async engine creation with connection pool checking enabled
engine = create_async_engine(
    DATABASE_URL,
    connect_args=DATABASE_CONNECT_ARGS,
    echo=False,
    pool_pre_ping=True
)

# Asynchronous session factory
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@asynccontextmanager
async def tenant_session(tenant_id: Optional[uuid.UUID]) -> AsyncGenerator[AsyncSession, None]:
    """
    Asynchronous context manager to manage database session lifecycle with Row-Level Security (RLS) enforcement.
    Ensures that app.current_tenant_id is set before any other database operations are executed.
    """
    if not tenant_id:
        raise TenantContextError("A valid tenant context identifier is required.")

    if not isinstance(tenant_id, uuid.UUID):
        try:
            tenant_id = uuid.UUID(str(tenant_id))
        except ValueError as e:
            raise TenantContextError(f"Invalid tenant UUID format: {tenant_id}") from e

    session = AsyncSessionFactory()
    try:
        # Precede transaction initialization to lock RLS filters at the engine layer
        await session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)}
        )

        yield session
        await session.commit()
    except (SQLAlchemyError, TimeoutError) as e:
        await session.rollback()
        raise DatabaseLayerError(f"Database transaction or connection failure occurred: {str(e)}") from e
    except Exception as e:
        await session.rollback()
        raise DatabaseLayerError(f"Unexpected database layer error occurred: {str(e)}") from e
    finally:
        await session.close()


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"), nullable=False)

    # ponytail: stripped unused bidirectional relationship lists (DEBT-003)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"), nullable=False)

    tenant: Mapped["Tenant"] = relationship()


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Industry attributes and dynamic manifest JSONB fields
    # Defined as native, mutable SQLAlchemy JSONB types
    industry_attributes: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSONB), 
        nullable=False, 
        server_default=text("'{}'::jsonb")
    )
    dynamic_manifest: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSONB), 
        nullable=False, 
        server_default=text("'{}'::jsonb")
    )
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"), nullable=False)

    tenant: Mapped["Tenant"] = relationship()


class Flow(Base):
    __tablename__ = "flows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    source_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("nodes.id", ondelete="RESTRICT"), nullable=False, index=True)
    target_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("nodes.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    industry_attributes: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSONB), 
        nullable=False, 
        server_default=text("'{}'::jsonb")
    )
    dynamic_manifest: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSONB), 
        nullable=False, 
        server_default=text("'{}'::jsonb")
    )
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"), nullable=False)

    tenant: Mapped["Tenant"] = relationship()

    source_node: Mapped["Node"] = relationship("Node", foreign_keys=[source_node_id])
    target_node: Mapped["Node"] = relationship("Node", foreign_keys=[target_node_id])


class SessionStateRegistry(Base):
    __tablename__ = "session_state_registry"

    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_history: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, 
        nullable=False, 
        server_default=text("'[]'::jsonb")
    )
    cached_telemetry_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB, 
        nullable=False, 
        server_default=text("'{}'::jsonb")
    )

    tenant: Mapped["Tenant"] = relationship()


class StagedIngestion(Base):
    __tablename__ = "staged_ingestion"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "file_name",
            "row_index",
            name="uq_staged_ingestion_tenant_file_row",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    vector_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)

    tenant: Mapped["Tenant"] = relationship()


class MLOpsModelRegistry(Base):
    __tablename__ = "mlops_model_registry"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "run_id",
            "execution_timestamp",
            name="uq_mlops_model_registry_tenant_run_execution",
        ),
    )

    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    associated_business_question: Mapped[str] = mapped_column(String, nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    hyperparameters_used: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb")
    )
    calculated_metrics_score: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb")
    )
    execution_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)

    tenant: Mapped["Tenant"] = relationship()


# ponytail: GIN indexes removed (DEBT-003)
