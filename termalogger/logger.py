# termalogger/logger.py

"""Houses all the setup and handling of logs, built upon Structlog."""

import logging
import typing as tp
from copy import deepcopy

import orjson
import structlog
from structlog.typing import EventDict

STYLES = {
    "fore": {
        "red": "\033[31m",
        "blue": "\033[34m",
        "cyan": "\033[36m",
        "magenta": "\033[35m",
        "yellow": "\033[33m",
        "green": "\033[32m",
    },
    "back": {"black": "\x1b[40m"},
    "reset": "\033[0m",
    "bright": "\033[1m",
    "dim": "\033[2m",
}

try:
    import colorama

    colorama.init()
    STYLES = {
        "fore": {
            "blue": colorama.Fore.BLUE,
            "cyan": colorama.Fore.CYAN,
            "magenta": colorama.Fore.MAGENTA,
            "green": colorama.Fore.GREEN,
            "yellow": colorama.Fore.YELLOW,
            "red": colorama.Fore.RED,
        },
        "back": {"black": colorama.Back.BLACK},
        "reset": colorama.Style.RESET_ALL,
        "bright": colorama.Style.BRIGHT,
        "dim": colorama.Style.DIM,
    }
except ImportError:
    pass

LEVEL_STYLES = {
    "debug": STYLES["fore"]["blue"],
    "info": STYLES["fore"]["green"],
    "warning": STYLES["fore"]["yellow"],
    "error": STYLES["fore"]["red"],
    "critical": STYLES["back"]["black"] + STYLES["fore"]["red"] + STYLES["bright"],
    "unknown": STYLES["dim"],
}

LogLevelName = tp.Literal[
    "notset",
    "debug",
    "info",
    "warning",
    "warn",
    "error",
    "err",
    "critical",
    "crit",
]

LogLevelInt = tp.Literal[0, 10, 20, 30, 40, 50]

LogLevel = tp.Literal[LogLevelName, LogLevelInt]


def get_level_name(level: LogLevelInt) -> LogLevelName:
    """Takes a logging level name and returns its integer counterpart."""
    if level == 10:
        return "debug"
    elif level == 20:
        return "info"
    elif level == 30:
        return "warning"
    elif level == 40:
        return "error"
    elif level == 50:
        return "critical"
    else:
        return "notset"


def get_level_int(level_name: LogLevelName) -> LogLevelInt:
    """Takes a logging level integer and returns its string counterpart."""
    if level_name == "debug":
        return 10
    elif level_name == "info":
        return 20
    elif level_name == "warning" or "warn":
        return 30
    elif level_name == "error" or "err":
        return 40
    elif level_name == "critical" or "crit":
        return 50
    else:
        return 0  # notset


class PrettyLevel:
    """Alternate level name column renderer for console messages that're a bit prettier."""

    def __call__(self, key: str, value: object) -> str:
        value = str(value)
        level_width = 8  # Max width of a level name
        pad_amount = level_width - len(value)
        padded_level = f"- {LEVEL_STYLES.get(value, 'unknown')}{value}{STYLES['reset']}"
        padded_level = padded_level + " " * pad_amount if pad_amount >= 0 else ""

        return padded_level


class DictKeyReorderer:
    """A version of KeyValuerenderer that returns a dict instead of a string."""

    def __init__(
        self,
        sort_keys: bool = False,
        key_order: tp.Sequence[str] | None = None,
        drop_missing: bool = False,
        repr_native_str: bool = True,
    ):
        self._ordered_items = structlog.processors._items_sorter(sort_keys, key_order, drop_missing)

        if repr_native_str is True:
            self._repr = repr
        else:

            def _repr(inst: tp.Any) -> str:
                if isinstance(inst, str):
                    return inst

                return repr(inst)

            self._repr = _repr

    def __call__(self, _, __, event_dict: EventDict) -> dict:
        sorted_items = self._ordered_items(event_dict)
        sorted_dict = {key: value for key, value in sorted_items}
        return sorted_dict


CONSOLE_RENDERER: tp.Callable = structlog.dev.ConsoleRenderer(
    columns=[
        # Timestamps are the same as the default.
        structlog.dev.Column(
            "timestamp",
            structlog.dev.KeyValueColumnFormatter(
                key_style=None,
                value_style=STYLES["dim"],
                reset_style=STYLES["reset"],
                value_repr=str,
            ),
        ),
        structlog.dev.Column("level", PrettyLevel()),
        # Message content
        structlog.dev.Column(
            "event",
            structlog.dev.KeyValueColumnFormatter(
                key_style=None,
                value_style=STYLES["bright"],
                reset_style=STYLES["reset"],
                value_repr=str,
            ),
        ),
        # The extra arg the is used for filtering.
        structlog.dev.Column(
            "labels",
            structlog.dev.KeyValueColumnFormatter(
                key_style=None,
                value_style=STYLES["fore"]["cyan"],
                reset_style=STYLES["reset"],
                value_repr=str,
            ),
        ),
        # All other extra params.
        structlog.dev.Column(
            "",
            structlog.dev.KeyValueColumnFormatter(
                key_style=STYLES["fore"]["cyan"],
                value_style=STYLES["fore"]["green"],
                reset_style=STYLES["reset"],
                value_repr=str,
            ),
        ),
    ]
)


class TermaLogger:
    """Structlog wrapper with level + label filtering, multiple formats and optional history.

    A logger is initialized with either pretty output for TTY sessions or json formatted lines
    for production/CI scenarios.

    Settings can be changed on the fly by calling `set_level`, `format_json`, ect. Internally,
    most `set_xxx` options just call `settings`, which recreates the logger with new settings.
    """

    def __init__(
        self,
        name: str,
        level: LogLevel = "info",
        filter: str | list[str] | dict[LogLevel, list[str]] = {},
        format_json: bool = False,
        cache_logger_on_first_use: bool = True,
    ):
        """Initialize the logger with the defaults, or values where provided.

        Args:
            name: What to name the logger.
            level: Loglevel to filter messages by. Default: "info" (20)
            filter: List of strings for filtering by the extra 'label' event. Default: []
            format_json: Switch to json-formatted logging. Default: False
            cache_logger_on_first_use: Sets the structlog parameter of the same name.
        """
        # Filter-related
        self.init_filter()
        self.set_filter(filter)
        self.filter_disable_keywords: list[str] = ["all", "everything", "open_the_floodgates"]

        # History tracking (when self.event_tracker or self.line_tracker are used)
        self.events: list[EventDict] = []
        self.str_lines: list[str] = []
        self.bytes_lines: list[bytes] = []

        # Other initial values
        self.name: str = name
        self.level: LogLevel = level
        self.format_json: bool = format_json
        self.enable_caching: bool = cache_logger_on_first_use

        # Factories
        self.console_factory: tp.Callable = structlog.PrintLoggerFactory()
        self.json_factory: tp.Callable = structlog.BytesLoggerFactory()

        self._current_processors: list[tp.Callable]
        self.shared_processors: list[tp.Callable] = [
            self.label_filterer,
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
        ]

        self.json_processors: list[tp.Callable] = [
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.format_exc_info,
            DictKeyReorderer(
                sort_keys=True,
                key_order=["timestamp", "level", "event", "labels", "exception"],
                drop_missing=False,
            ),
            structlog.processors.JSONRenderer(serializer=orjson.dumps),
        ]

        self.console_processors: list[tp.Callable] = [
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            CONSOLE_RENDERER,
        ]

        self.settings(
            name=self.name,
            level=self.level,
            format_json=self.format_json,
            cache_logger_on_first_use=self.enable_caching,
        )

    def settings(
        self,
        name: str | None = None,
        level: LogLevel | None = None,
        format_json: bool | None = None,
        cache_logger_on_first_use: bool | None = None,
    ) -> None:
        """Recreate the logger with new settings.

        All args default to None and remain unchanged unless specified.

        Args:
            name: What to name the logger.
            level: Loglevel to filter messages by.
            format_json: Switch to json-formatted logging.
            cache_logger_on_first_use: Sets the structlog parameter of the same name.
        """

        # Infer level from string name
        if isinstance(level, str):
            level = getattr(logging, level.upper())

        if name is not None:
            self.name = name
        if level is not None:
            self.level = level
        if format_json is not None:
            self.format_json = format_json
        if cache_logger_on_first_use is not None:
            self.enable_caching = cache_logger_on_first_use

        if self.format_json:
            self._current_processors = self.shared_processors + self.json_processors
            self.current_factory = self.json_factory
        else:
            self._current_processors = self.shared_processors + self.console_processors
            self.current_factory = self.console_factory

        structlog.configure(
            logger_factory=self.current_factory,
        )

        self.logger = structlog.get_logger(
            self.name,
            processors=self._current_processors,
            wrapper_class=structlog.make_filtering_bound_logger(self.level),
            cache_logger_on_first_use=self.enable_caching,
        )

    def set_json_output(self, format_json: bool) -> None:
        """Sets whether to use pretty formatting (False) or structured json (True)"""
        self.settings(format_json=format_json)

    def set_level(self, level: LogLevel) -> None:
        """Sets the loglevel to filter messages by."""
        self.settings(level=level)

    def init_filter(self) -> None:
        """Set the filter defaults."""
        self.filter_enabled: dict[str, bool] = {
            "debug": True,
            "info": False,
            "warning": False,
            "error": False,
            "critical": False,
        }

        self.filter: dict[str, list[str]] = {
            "debug": [],
            "info": [],
            "warning": [],
            "error": [],
            "critical": [],
        }

    def set_filter(
        self,
        filter: str | list[str] | dict[LogLevel, list[str]],
    ) -> None:
        """Sets the `label` filters for any of the provided levels.

        "debug" level is assumed as defualt if `filter` is a string or list.

        "all", "everything" and "open_the_floodgates" disables filtering for that level, or
        whatever is specified in `self.filter_disable_keywords`
        """

        if isinstance(filter, str):
            filter = [filter]
        if isinstance(filter, list):
            filter = {"debug": filter}

        for level in filter:
            if isinstance(level, int):
                level = get_level_name(level)

            self.filter_enabled[level] = True
            self.filter[level] = filter[level]
            if set(filter[level]) & set(self.filter_disable_keywords):
                self.filter_enabled[level] = False

    def label_filterer(
        self,
        _,
        method_name: LogLevelName,
        event_dict: EventDict,
    ) -> EventDict:
        """Normalizes label events and filters them by ones set in `self.filter`."""
        # Normalize labels entry
        if "label" in event_dict:
            event_dict["labels"] = event_dict.pop("label")
        # Change strings to single-item lists and add empty `labels` if non-present
        if "labels" in event_dict:
            if isinstance(event_dict["labels"], str):
                event_dict["labels"] = [event_dict["labels"]]
            else:
                event_dict["labels"] = []

        # Check if filtering should be performed on the current level
        if not self.filter_enabled[method_name]:
            return event_dict

        common_labels = set(event_dict["labels"]) & set(self.filter[method_name])

        # Skip logging events with unmatched labels
        if not common_labels:
            raise structlog.DropEvent

        return event_dict

    def event_tracker(
        self,
        _: tp.Callable,
        __: LogLevelName,
        event_dict: EventDict,
    ) -> EventDict:
        """Adds a copy of the current event_dict to `self.event_list`."""
        self.events.append(deepcopy(dict(event_dict)))
        return event_dict

    def line_tracker(
        self,
        _: tp.Callable,
        __: LogLevelName,
        rendered_msg: str | bytes,
    ) -> str | bytes:
        """Inserts the rendered message from the end of a processor chain into a list:

        - `self.str_list` for string lines (console)
        - `self.bytes_list` for bytes lines (json)
        """
        if isinstance(rendered_msg, str):
            self.str_lines.append(rendered_msg)
        else:
            self.bytes_lines.append(rendered_msg)

        return rendered_msg

    def bind(self, **kwargs) -> structlog.BoundLogger:
        """Calls Structlog's bind for creating localized, context-approprate logging"""
        return self.logger.bind(**kwargs)

    def debug(self, *args, **kwargs) -> None:
        """Logs to the configured logger with level `debug`"""
        self.logger.debug(*args, **kwargs)

    def info(self, *args, **kwargs) -> None:
        """Logs to the configured logger with level `info`"""
        self.logger.info(*args, **kwargs)

    def warning(self, *args, **kwargs) -> None:
        """Logs to the configured logger with level `warning`"""
        self.logger.warning(*args, **kwargs)

    def warn(self, *args, **kwargs) -> None:
        """Simply an alias to `warning`"""
        self.logger.warning(*args, **kwargs)

    def error(self, *args, **kwargs) -> None:
        """Logs to the configured logger with level `error`"""
        self.logger.error(*args, **kwargs)

    def err(self, *args, **kwargs) -> None:
        """Simply an alias to `error`"""
        self.logger.error(*args, **kwargs)

    def critical(self, *args, **kwargs) -> None:
        """Logs to the configured logger with level `critical`"""
        self.logger.critical(*args, **kwargs)

    def crit(self, *args, **kwargs) -> None:
        """Simply an alias to `critical`"""
        self.logger.critical(*args, **kwargs)
