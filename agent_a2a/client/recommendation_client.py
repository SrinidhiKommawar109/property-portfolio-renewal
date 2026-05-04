import httpx
from typing import Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class RecommendationClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8004"):
        self.base_url = base_url.rstrip("/")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.ReadTimeout, httpx.ConnectError, httpx.ConnectTimeout)),
        reraise=True
    )
    async def generate_recommendation_async(
        self,
        property_id: str,
        change_report: Dict[str, Any],
        risk_reevaluation: Dict[str, Any],
        property_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Sends an A2A request to the Recommendation Server.
        Implements exponential backoff for network-level failures and timeouts.
        """
        payload = {
            "property_id": property_id,
            "change_report": change_report,
            "risk_reevaluation": risk_reevaluation,
            "property_context": property_context
        }
        
        # LLMs take time, so we need a healthy timeout (e.g., 90 seconds)
        timeout = httpx.Timeout(90.0)
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self.base_url}/generate-recommendation",
                json=payload
            )
            
            # Raise exception for HTTP errors (e.g., 500 internal server error)
            response.raise_for_status()
            
            # The server wraps the report in `recommendation`
            data = response.json()
            return data["recommendation"]