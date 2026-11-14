from fastapi import APIRouter
from typing import List, Dict, Any

from backend.app.services.analytics_service import analytics_service
from backend.app.schemas.schemas import OverviewAnalyticsResponse, TrendDataPoint

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/overview", response_model=OverviewAnalyticsResponse)
async def get_overview_analytics():
    """Retrieves aggregated statistics: defect totals, severity distribution, risk distribution, and hardware status."""
    return analytics_service.get_overview()

@router.get("/trends", response_model=List[TrendDataPoint])
async def get_damage_trends():
    """Retrieves chronological damage trends for charting."""
    return analytics_service.get_trends()
