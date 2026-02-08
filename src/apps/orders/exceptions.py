"""Order domain exceptions."""


class InvalidStatusTransition(ValueError):
    def __init__(self, current_status: str, next_status: str) -> None:
        super().__init__(f"Transition not allowed: {current_status} -> {next_status}")
        self.current_status = current_status
        self.next_status = next_status
