from typing import Callable, Literal

LogLevel = Literal["error", "warning", "info", "debug"]

RED = "\033[31m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
GREEN = "\033[32m"
GRAY = "\033[90m"
RESET = "\033[0m"


class Logger:
    """
    Simple logger class to log messages to the console
    """

    def __init__(
        self,
        level: LogLevel = "info",
        log: Callable[[str], None] = print,
        copy_definition_name: str | None = None,
        nid: int | None = None,
    ):
        self.level = level
        self.log = log
        self.copy_definition_name = copy_definition_name
        self.nid = nid

    def reset_prefix(self):
        self.copy_definition_name = None
        self.nid = None

    def _prefix(self) -> str:
        prefix_str = ""
        if self.copy_definition_name:
            prefix_str += f"[{self.copy_definition_name}]"
        if self.nid:
            prefix_str += f"[NID:{self.nid}]"
        return prefix_str

    def error(self, message: str):
        if self.level in ["error", "warning", "info", "debug"]:
            self.log(f"{RED}[ERROR]{RESET} {GRAY}{self._prefix()}{RESET}{message}")

    def warning(self, message: str):
        if self.level in ["warning", "info", "debug"]:
            self.log(f"{YELLOW}[WARNING]{RESET} {GRAY}{self._prefix()}{RESET}{message}")

    def info(self, message: str):
        if self.level in ["info", "debug"]:
            self.log(f"{BLUE}[INFO]{RESET} {GRAY}{self._prefix()}{RESET}{message}")

    def debug(self, message: str):
        if self.level == "debug":
            self.log(f"{GREEN}[DEBUG]{RESET} {GRAY}{self._prefix()}{RESET}{message}")
