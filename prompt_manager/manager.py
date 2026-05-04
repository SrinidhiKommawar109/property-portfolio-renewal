from datetime import datetime
import json

class SafeDict(dict):
    def __missing__(self, key):
        return '{' + key + '}'

class PromptManager:
    def __init__(self):
        self._templates = {}   # {agent: {template_name: {version: template_str}}}
        self._usage_log = []

    def register(self, agent: str, name: str, version: str, template: str):
        """Register a versioned prompt template."""
        if agent not in self._templates:
            self._templates[agent] = {}
        if name not in self._templates[agent]:
            self._templates[agent][name] = {}
        self._templates[agent][name][version] = template

    def get_prompt(self, agent: str, name: str, variables: dict = None, version: str = "latest") -> str:
        """
        Retrieve and render prompt. Use str.format_map for variable substitution.
        Log usage to self._usage_log with timestamp, agent, template name, version.
        If version='latest', use the highest version key.
        Handle KeyError gracefully if variable is missing (use SafeDict pattern).
        """
        if agent not in self._templates or name not in self._templates[agent]:
            raise KeyError(f"Template '{name}' for agent '{agent}' not found.")

        versions = self._templates[agent][name]
        if version == "latest":
            actual_version = sorted(versions.keys())[-1]
        else:
            actual_version = version

        if actual_version not in versions:
            raise KeyError(f"Version '{actual_version}' of template '{name}' for agent '{agent}' not found.")

        template_str = versions[actual_version]
        
        # Log usage
        self._usage_log.append({
            "timestamp": datetime.now().isoformat(),
            "agent": agent,
            "template_name": name,
            "version": actual_version,
            "variables": list(variables.keys()) if variables else []
        })

        if variables:
            return template_str.format_map(SafeDict(variables))
        return template_str

    def list_templates(self, agent: str = None) -> dict:
        """List all templates with versions."""
        if agent:
            return self._templates.get(agent, {})
        return self._templates

    def get_usage_log(self) -> list:
        """Return usage log for Arize tracing."""
        return self._usage_log
