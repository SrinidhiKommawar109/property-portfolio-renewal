from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import logging
from agents.change_detection import detect_changes_for_property

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("a2a-server")

app = FastAPI(title="Change Detection A2A Server")

class ChangeDetectionRequest(BaseModel):
    property_id: str
    current_year: Dict[str, Any]
    prior_year: Dict[str, Any]

class ChangeDetectionResponse(BaseModel):
    status: str
    property_id: str
    change_report: Dict[str, Any]

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "change-detection-agent"}

@app.post("/detect-changes", response_model=ChangeDetectionResponse)
async def detect_changes_endpoint(request: ChangeDetectionRequest):
    """
    Standard A2A endpoint for property change detection.
    Delegates to the change_detection agent logic.
    """
    logger.info(f"🚀 Received change detection request for property: {request.property_id}")
    
    try:
        # Call the actual agent logic
        report = await detect_changes_for_property(
            request.property_id, 
            request.current_year, 
            request.prior_year
        )
        
        return ChangeDetectionResponse(
            status="success",
            property_id=request.property_id,
            change_report=report
        )
    except Exception as e:
        logger.error(f"❌ Error processing {request.property_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002)
