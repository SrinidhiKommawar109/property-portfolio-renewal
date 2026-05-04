import httpx
from typing import Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class ChangeDetectionClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8002"):
        self.base_url = base_url.rstrip("/")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.ReadTimeout, httpx.ConnectError, httpx.ConnectTimeout)),
        reraise=True
    )
    async def detect_changes_async(
        self, 
        property_id: str, 
        current_year: Dict[str, Any], 
        prior_year: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Sends an A2A request to the Change Detection Server.
        Implements exponential backoff for network-level failures and timeouts.
        """
        payload = {
            "property_id": property_id,
            "current_year": current_year,
            "prior_year": prior_year
        }
        
        # LLMs take time, so we need a healthy timeout (e.g., 90 seconds)
        timeout = httpx.Timeout(90.0)
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self.base_url}/detect-changes",
                json=payload
            )
            
            # Raise exception for HTTP errors (e.g., 500 internal server error)
            response.raise_for_status()
            
            # The server wraps the report in `change_report`
            data = response.json()
            return data["change_report"]
