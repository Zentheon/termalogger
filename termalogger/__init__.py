# termalogger/__init__.py

"""A crazy simple way to use Structlog.

All notable functionality of this library is housed within the aptly named `TermaLogger` class.
"""

__version__ = "0.0.1"
__authors__ = ["Zentheon <zentheon@mailbox.org>"]
__license__ = "GPL-3.0"

from termalogger.logger import (
    DictKeyReorderer,
    PrettyLevel,
    TermaLogger,
)

__all__ = [
    "DictKeyReorderer",
    "PrettyLevel",
    "TermaLogger",
]
