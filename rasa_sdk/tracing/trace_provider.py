from typing import Optional
from rasa_sdk.utils import Singleton
from opentelemetry.trace import Tracer


class TraceProvider(metaclass=Singleton):
    """Represents a provider for tracer."""

    tracer: Optional[Tracer] = None

    def register_tracer(self, tracer: Tracer) -> None:
        """Register a tracer.
        Args:
            trace: The tracer to register.
        """
        self.tracer = tracer

    def get_tracer(self) -> Optional[Tracer]:
        """Get the tracer.
        Returns:
            The tracer.
        """
        return self.tracer
