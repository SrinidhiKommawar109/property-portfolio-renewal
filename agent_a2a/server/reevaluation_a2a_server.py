from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import logging
from agents.property_reevaluation import reevaluate_property_risk

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reevaluation-a2a-server")

app = FastAPI(title="Property Reevaluation A2A Server")

class ReevaluationRequest(BaseModel):
    property_id: str
    current_data: Dict[str, Any]
    prior_data: Dict[str, Any]
    change_report: Dict[str, Any]

class ReevaluationResponse(BaseModel):
    status: str
    property_id: str
    risk_reevaluation: Dict[str, Any]

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "property-reevaluation-agent"}

@app.post("/reevaluate-risk", response_model=ReevaluationResponse)
async def reevaluate_risk_endpoint(request: ReevaluationRequest):
    """
    Standard A2A endpoint for property risk reevaluation.
    Delegates to the property_reevaluation agent logic.
    """
    logger.info(f"🚀 Received risk reevaluation request for property: {request.property_id}")
    
    try:
        # Call the actual agent logic
        risk_report = await reevaluate_property_risk(
            request.property_id,
            request.current_data,
            request.prior_data,
            request.change_report
        )
        
        return ReevaluationResponse(
            status="success",
            property_id=request.property_id,
            risk_reevaluation=risk_report
        )
    except Exception as e:
        logger.error(f"❌ Error processing {request.property_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8003)