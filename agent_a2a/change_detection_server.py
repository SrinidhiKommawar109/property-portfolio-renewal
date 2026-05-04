import json
import asyncio
from a2a.server import A2AServer, TaskHandler
from a2a.types import TaskResult, Artifact, TextPart
from agents.change_detection import detect_changes_for_property

class ChangeDetectionA2AHandler(TaskHandler):
    async def handle_task(self, task):
        """
        Receives a task with property data in task.message.parts[0].text as JSON.
        Expected input: {"property_id": str, "current_year": dict, "prior_year": dict}
        Runs the full change detection pipeline (detect + classify + summarize).
        Returns: TaskResult with change report JSON as artifact.
        """
        try:
            # Parse input JSON from the first text part
            input_data = json.loads(task.message.parts[0].text)
            property_id = input_data.get("property_id")
            current_year = input_data.get("current_year")
            prior_year = input_data.get("prior_year")
            
            if not all([property_id, current_year, prior_year]):
                return TaskResult(
                    status="failed",
                    message="Missing required fields: property_id, current_year, or prior_year"
                )
            
            # Run the change detection pipeline
            change_report = await detect_changes_for_property(property_id, current_year, prior_year)
            
            # Create artifact with results
            artifact = Artifact(
                id=f"change-report-{property_id}",
                type="json",
                content=json.dumps(change_report)
            )
            
            return TaskResult(
                status="completed",
                message=f"Change detection complete for {property_id}",
                artifacts=[artifact]
            )
            
        except Exception as e:
            return TaskResult(
                status="failed",
                message=f"Error in change detection: {str(e)}"
            )

def create_change_detection_server():
    """Creates and returns A2A server for Change Detection Agent."""
    # Note: In a real implementation, we'd load the card from the JSON file
    card_path = os.path.join(os.path.dirname(__file__), "agent_cards", "change_detection_agent.json")
    
    server = A2AServer(
        port=8002,
        handler=ChangeDetectionA2AHandler(),
        agent_card_path=card_path
    )
    return server

if __name__ == "__main__":
    import os
    server = create_change_detection_server()
    server.run()
