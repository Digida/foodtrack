"""Tool Registry — discovers and dispatches all 40 codified tools.

The registry introspects the `tools` package (via its public exports) and
indexes every concrete ``BaseTool`` subclass by its ``name``. It is the single
entry point the orchestrator uses to enumerate, check and execute tools.
"""
from __future__ import annotations

import inspect
import json
from typing import Any

import tools as tools_pkg
from agent.base_tool import BaseTool


class ToolRegistry:
    """Index of tool classes with cached instances and safe dispatch."""

    def __init__(self) -> None:
        self._classes: dict[str, type[BaseTool]] = {}
        self._instances: dict[str, BaseTool] = {}
        self._discovered = False

    def _ensure_discovered(self) -> None:
        """Discover lazily.

        ``tools`` is imported by the registry, while every tools module imports
        ``agent.base_tool`` — a benign cycle at import time. Guarding discovery
        behind first use guarantees ``tools.__all__`` is fully populated before
        we read it, regardless of module import order.
        """
        if self._discovered:
            return
        self._discover()
        self._discovered = True

    def _discover(self) -> None:
        for name in getattr(tools_pkg, "__all__", []):
            obj = getattr(tools_pkg, name, None)
            if not inspect.isclass(obj):
                continue
            if obj is BaseTool or not issubclass(obj, BaseTool):
                continue
            tool_name = getattr(obj, "name", "") or ""
            if not tool_name:
                continue
            self._classes[tool_name] = obj

    def get(self, name: str) -> BaseTool | None:
        self._ensure_discovered()
        cls = self._classes.get(name)
        if cls is None:
            return None
        instance = self._instances.get(name)
        if instance is None:
            instance = cls()
            self._instances[name] = instance
        return instance

    def has(self, name: str) -> bool:
        self._ensure_discovered()
        return name in self._classes

    def available(self, name: str) -> bool:
        self._ensure_discovered()
        cls = self._classes.get(name)
        if cls is None:
            return False
        try:
            return bool(cls.check_available())
        except Exception:
            return False

    def list_tools(self) -> list[dict]:
        self._ensure_discovered()
        return [
            {
                "name": name,
                "description": cls.description,
                "parameters": cls.parameters,
                "available": self.available(name),
            }
            for name, cls in sorted(self._classes.items())
        ]

    def tool_names(self) -> list[str]:
        self._ensure_discovered()
        return sorted(self._classes)

    def count(self) -> int:
        self._ensure_discovered()
        return len(self._classes)

    def execute(self, name: str, **kwargs: Any) -> Any:
        """Dispatch a tool, returning a parsed dict (or raw value on failure)."""
        tool = self.get(name)
        if tool is None:
            raise KeyError(f"Unknown tool: {name!r}")
        raw = tool.execute(**kwargs)
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            return raw


registry = ToolRegistry()
