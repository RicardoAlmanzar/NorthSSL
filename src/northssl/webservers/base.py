from dataclasses import dataclass


@dataclass(slots=True)
class WebServerResult:
    success: bool
    message: str
