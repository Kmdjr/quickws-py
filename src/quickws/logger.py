from .utils import color_codes as COLORS

class Logger:
    """
    A simple logging utility with customizable levels and color-coded output.

    Parameters:
        log_lvl (int): The initial logging level (default is 5).
        log_codes (dict[int, str]): Optional dictionary defining log message formatting by level.
    """
    def __init__(self, log_lvl: int = 5, log_codes: dict[int, str] = {}):
        self.lvl = log_lvl
        self.log_codes: dict[int] = {}

    def log(self, msg: str, lvl: int = 0):
        """
        Logs a message if the provided level meets or exceeds the current logging threshold.

        Parameters:
            msg (str): The message to log.
            lvl (int): The level of the message (default is 0).
        """
        if self.lvl < lvl and self.lvl > -1:
            return
        self._build_msg(msg,lvl)

    def set(self, lvl: int):
        """
        Sets the logging level.

        Parameters:
            lvl (int): The new logging level.
        """
        if isinstance(lvl, int):
            self.lvl = lvl

    def _build_msg(self, raw_msg: str, lvl: int):
        """
        Builds a formatted message string with optional prefixes, suffixes, and colors.

        Parameters:
            raw_msg (str): The main message content.
            lvl (int): The log level, used to determine formatting.
        """
        code = self.log_codes.get(lvl)
        msg: str = ""
        if code:
            prefix = code.get("prefix")
            suffix = code.get("suffix")
            if prefix:
                msg += self._color(code.get("prefix_color")) + prefix
            msg += " " + self._color(code.get("msg_color")) + raw_msg
            if suffix:
                msg += self._color(code.get("suffix_color")) + suffix
        else:
            msg = raw_msg

        print(msg)

    def get_log_codes(self):
        """
        Prints the current dictionary of log codes and formatting.
        """
        print(f"Log Codes: {str(self.log_codes)}")

    def _color(self, color: str) -> str:
        """
        Retrieves the ANSI escape code for the given color name.

        Parameters:
            color (str): The color name to retrieve.

        Returns:
            str: ANSI color code, or reset if not found.
        """
        if color:
            return COLORS.get(color.lower(), COLORS["reset"])

    def __str__(self):
        """
        Returns a human-readable string representation of the logger.

        Returns:
            str: The current log level.
        """
        return f"Log Level: {str(self.lvl)}"
