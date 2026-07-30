from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    name: str = ""
    description: str = ""
    parameters: dict = {}

    @classmethod
    @abstractmethod
    def check_available(cls) -> bool:
        ...

    @abstractmethod
    def execute(self, **kwargs: Any) -> str:
        ...
