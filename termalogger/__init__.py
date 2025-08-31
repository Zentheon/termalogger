# termalogger/__init__.py

"""A crazy simple way to use Structlog.

All notable functionality of this library is housed within the aptly named `TermaLogger` class.
"""

__version__ = "1.0.0"
__authors__ = ["Zentheon <zentheon@mailbox.org>"]
__license__ = "GPL-3.0"

from termalogger.logger import (
    DictKeyReorderer,
    PrettyLevel,
    TermaLogger,
    get_level_int,
    get_level_name,
)

__all__ = [
    "DictKeyReorderer",
    "PrettyLevel",
    "TermaLogger",
    "get_level_int",
    "get_level_name",
]
