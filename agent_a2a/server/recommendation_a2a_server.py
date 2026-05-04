from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import logging
from agents.renewal_recommendation import generate_renewal_recommendation

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("recommendation-a2a-server")

app = FastAPI(title="Renewal Recommendation A2A Server")

class RecommendationRequest(BaseModel):
    property_id: str
    change_report: Dict[str, Any]
    risk_reevaluation: Dict[str, Any]
    property_context: Dict[str, Any]

class RecommendationResponse(BaseModel):
    status: str
    property_id: str
    recommendation: Dict[str, Any]

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "renewal-recommendation-agent"}

@app.post("/generate-recommendation", response_model=RecommendationResponse)
async def generate_recommendation_endpoint(request: RecommendationRequest):
    """
    Standard A2A endpoint for renewal recommendation.
    Delegates to the renewal_recommendation agent logic.
    """
    logger.info(f"🚀 Received recommendation request for property: {request.property_id}")
    
    try:
        # Call the actual agent logic
        recommendation_report = await generate_renewal_recommendation(
            request.property_id,
            request.change_report,
            request.risk_reevaluation,
            request.property_context
        )
        
        return RecommendationResponse(
            status="success",
            property_id=request.property_id,
            recommendation=recommendation_report
        )
    except Exception as e:
        logger.error(f"❌ Error processing {request.property_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8004)