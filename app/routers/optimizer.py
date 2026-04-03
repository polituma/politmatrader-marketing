"""
Optimizer routes: recommendations.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..middleware import require_api_key
from ..schemas import RecommendationOut
from ..services.optimizer import OptimizerService

router = APIRouter(prefix="/optimizer", tags=["optimizer"])

optimizer = OptimizerService()


@router.get(
    "/recommendations",
    response_model=list[RecommendationOut],
    dependencies=[Depends(require_api_key)],
)
def optimizer_recommendations():
    return optimizer.recommend()
