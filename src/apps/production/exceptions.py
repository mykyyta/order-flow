"""Production domain exceptions."""


class InvalidStatusTransition(ValueError):
    def __init__(self, status: str, next_status: str) -> None:
        super().__init__(f"Transition not allowed: {status} -> {next_status}")
        self.status = status
        self.next_status = next_status
