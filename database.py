"""
Database service with multi-tenant schema isolation.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, text, inspect
from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator
import logging

from config import get_settings
from models import Base, Tenant

logger = logging.getLogger(__name__)


class DatabaseService:
    """Database service with multi-tenant support."""
    
    def __init__(self):
        self.settings = get_settings()
        self._async_engine = None
        self._async_session_factory = None
        self._sync_engine = None
        self._initialize()
    
    def _initialize(self):
        """Initialize database engines."""
        # Async engine for main operations
        self._async_engine = create_async_engine(
            self.settings.database_url,
            pool_size=self.settings.database_pool_size,
            max_overflow=self.settings.database_max_overflow,
            echo=self.settings.debug,
        )
        
        self._async_session_factory = async_sessionmaker(
            self._async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        # Sync engine for migrations and admin tasks
        self._sync_engine = create_engine(
            self.settings.sync_database_url,
            pool_size=5,
            max_overflow=10,
            echo=self.settings.debug,
        )
        
        logger.info("Database service initialized")
    
    @asynccontextmanager
    async def get_session(
        self, 
        schema_name: Optional[str] = None
    ) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session with optional schema context.
        
        Args:
            schema_name: Schema name for multi-tenant isolation
        """
        async with self._async_session_factory() as session:
            try:
                # Set search_path for multi-tenant isolation
                if schema_name and self.settings.enable_schema_isolation:
                    await session.execute(
                        text(f"SET search_path TO {schema_name}, public")
                    )
                    logger.debug(f"Set search_path to: {schema_name}")
                
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Session error: {e}")
                raise
            finally:
                await session.close()
    
    async def create_tenant_schema(self, schema_name: str) -> bool:
        """
        Create a new tenant schema with all tables.
        
        Args:
            schema_name: Name of the schema to create
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async with self._async_engine.begin() as conn:
                # Create schema
                await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
                logger.info(f"Created schema: {schema_name}")
                
                # Set search_path and create tables
                await conn.execute(text(f"SET search_path TO {schema_name}, public"))
                
                # Create all tables in the schema
                await conn.run_sync(Base.metadata.create_all)
                logger.info(f"Created tables in schema: {schema_name}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to create tenant schema {schema_name}: {e}")
            return False
    
    async def schema_exists(self, schema_name: str) -> bool:
        """Check if schema exists."""
        try:
            async with self._async_engine.connect() as conn:
                result = await conn.execute(
                    text(
                        "SELECT schema_name FROM information_schema.schemata "
                        "WHERE schema_name = :schema_name"
                    ),
                    {"schema_name": schema_name}
                )
                return result.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking schema existence: {e}")
            return False
    
    async def initialize_public_schema(self):
        """Initialize public schema with tenant table."""
        try:
            async with self._async_engine.begin() as conn:
                await conn.execute(text("SET search_path TO public"))
                
                # Create only Tenant table in public schema
                await conn.run_sync(
                    lambda sync_conn: Tenant.__table__.create(
                        sync_conn, checkfirst=True
                    )
                )
                logger.info("Initialized public schema with Tenant table")
        except Exception as e:
            logger.error(f"Failed to initialize public schema: {e}")
            raise
    
    async def get_tenant_by_schema(self, schema_name: str) -> Optional[dict]:
        """Get tenant information by schema name."""
        try:
            async with self.get_session() as session:
                result = await session.execute(
                    text(
                        "SELECT * FROM public.tenants WHERE schema_name = :schema_name"
                    ),
                    {"schema_name": schema_name}
                )
                row = result.fetchone()
                if row:
                    return dict(row._mapping)
                return None
        except Exception as e:
            logger.error(f"Error fetching tenant: {e}")
            return None
    
    async def close(self):
        """Close database connections."""
        if self._async_engine:
            await self._async_engine.dispose()
            logger.info("Database connections closed")


# Singleton instance
_db_service: Optional[DatabaseService] = None


def get_db_service() -> DatabaseService:
    """Get or create database service instance."""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service
