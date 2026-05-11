from dataclasses import dataclass

@dataclass(slots=True)
class ProviderResult:
    success: bool
    message: str
    command: list[str] | None = None
