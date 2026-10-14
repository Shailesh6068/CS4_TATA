from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel

class LLMService(ABC):
    """Abstract base class for privacy-preserving local LLM providers."""
    
    @abstractmethod
    def check_status(self) -> Dict[str, Any]:
        """Returns connection health, active model, and availability."""
        pass

    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Returns list of installed local models."""
        pass

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None, model: Optional[str] = None) -> str:
        """Executes local LLM text generation."""
        pass

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str],
        schema_cls: Type[BaseModel],
        model: Optional[str] = None
    ) -> BaseModel:
        """Generates structured output conforming strictly to a Pydantic schema."""
        pass
