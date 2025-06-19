from typing import Callable, Literal

LogLevel = Literal["error", "warning", "info", "debug"]

RED = "\033[31m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
GREEN = "\033[32m"
RESET = "\033[0m"


class Logger:
    """
    Simple logger class to log messages to the console
    """

    def __init__(self, level: LogLevel = "info", log: Callable[[str], None] = print):
        self.level = level
        self.log = log

    def error(self, message: str):
        if self.level in ["error", "warning", "info", "debug"]:
            self.log(f"{RED}[ERROR]{RESET} {message}")

    def warning(self, message: str):
        if self.level in ["warning", "info", "debug"]:
            self.log(f"{YELLOW}[WARNING]{RESET} {message}")

    def info(self, message: str):
        if self.level in ["info", "debug"]:
            self.log(f"{BLUE}[INFO]{RESET} {message}")

    def debug(self, message: str):
        if self.level == "debug":
            self.log(f"{GREEN}[DEBUG]{RESET} {message}")
