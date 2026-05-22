from fastapi import APIRouter

from api.v1.leads import router as leads_router
from api.v1.outreach import router as outreach_router
from api.v1.rag_ingest import router as rag_ingest_router
from api.v1.rag_query import router as rag_router
from api.v1.search import router as search_router

router = APIRouter(prefix="/api/v1")

router.include_router(search_router)
router.include_router(leads_router, prefix="/leads")
router.include_router(outreach_router, prefix="/outreach")
router.include_router(rag_router, prefix="/rag")
router.include_router(rag_ingest_router, prefix="/rag")
