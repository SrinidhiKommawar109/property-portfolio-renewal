from .manager import PromptManager
from .templates.change_detection import register_change_detection_templates
from .templates.re_evaluation import register_re_evaluation_templates
from .templates.renewal_recommendation import register_renewal_recommendation_templates
from .templates.orchestrator import register_orchestrator_templates

def create_prompt_manager():
    manager = PromptManager()
    register_change_detection_templates(manager)
    register_re_evaluation_templates(manager)
    register_renewal_recommendation_templates(manager)
    register_orchestrator_templates(manager)
    return manager
