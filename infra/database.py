import os
import uuid
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
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


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/aegisprocure"
)

# Async engine creation with connection pool checking enabled
engine = create_async_engine(
    DATABASE_URL,
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
            text("SET LOCAL app.current_tenant_id = :tenant_id"),
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

    users: Mapped[list["User"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    nodes: Mapped[list["Node"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    flows: Mapped[list["Flow"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"), nullable=False)

    tenant: Mapped["Tenant"] = relationship(back_populates="users")


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

    tenant: Mapped["Tenant"] = relationship(back_populates="nodes")


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

    tenant: Mapped["Tenant"] = relationship(back_populates="flows")

    source_node: Mapped["Node"] = relationship("Node", foreign_keys=[source_node_id])
    target_node: Mapped["Node"] = relationship("Node", foreign_keys=[target_node_id])


# Explicit database indexes layout (using GIN indexes for JSONB fields)
Index("idx_nodes_industry_attributes", Node.industry_attributes, postgresql_using="gin")
Index("idx_nodes_dynamic_manifest", Node.dynamic_manifest, postgresql_using="gin")
Index("idx_flows_industry_attributes", Flow.industry_attributes, postgresql_using="gin")
Index("idx_flows_dynamic_manifest", Flow.dynamic_manifest, postgresql_using="gin")
