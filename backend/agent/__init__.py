"""AI agent package: 40 codified tools orchestrated via MAG -> DAG -> RAG -> fallback.

Only cycle-safe, light modules are imported here. The registry, pipelines and
orchestrator import the ``tools`` package, while every tools module imports
``agent.base_tool`` — so those heavier modules are imported directly by name
(``from agent.orchestrator import orchestrator``) to keep the import graph
acyclic.
"""

from agent.base_tool import BaseTool

__all__ = ["BaseTool"]
