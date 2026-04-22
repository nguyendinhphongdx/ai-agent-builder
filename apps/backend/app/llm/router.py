"""Public endpoints for LLM catalog.

Read-only: catalog is static during a server lifetime. Frontend fetches
once (TanStack staleTime Infinity) and caches.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.llm.catalog import MODEL_CATALOG, PROVIDERS, ModelCatalogEntry, ProviderEntry

router = APIRouter(prefix="/llm", tags=["llm"])


class CatalogResponse(BaseModel):
    providers: list[ProviderEntry]
    models: list[ModelCatalogEntry]


@router.get("/catalog", response_model=CatalogResponse)
async def get_catalog() -> CatalogResponse:
    return CatalogResponse(providers=PROVIDERS, models=MODEL_CATALOG)
