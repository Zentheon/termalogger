# tests/test_logger.py

import pytest

from termalogger import TermaLogger


@pytest.fixture(scope="function")
def log():
    """Each test definition is run with a fresh TermaLogger instance with extra processors"""
    log = TermaLogger("test_logger")
    # Event dictionary list
    log.shared_processors.append(log.event_tracker)
    # Rendered lines list (str or bytes, respectively)
    log.console_processors.append(log.line_tracker)
    log.json_processors.append(log.line_tracker)
    # Recreate the logger with updated processors
    log.settings()
    return log


def test_log_levels(log: TermaLogger):
    # Test each of the levels at default configs
    test_events = [
        {"event": "This debug message should be dropped", "level": "debug"},
        {"event": "Regular old info message", "level": "info"},
        {"event": "A spicy warning message", "level": "warning"},
        {"event": "A dangerous error message", "level": "error"},
        {"event": "A catastrophic critical message!", "level": "critical"},
    ]
    log.debug(test_events[0]["event"])
    log.info(test_events[1]["event"])
    log.warning(test_events[2]["event"])
    log.error(test_events[3]["event"])
    log.critical(test_events[4]["event"])

    # Should contain all but the first (debug) message
    assert log.events == test_events[1:]


def test_filtering_with_labels(log: TermaLogger):
    # Set up filtering with labels and test logging
    log.set_filter({"debug": ["important"]})
    log.info("This debug message is important", label="important")
    assert {
        "event": "This debug message is important",
        "labels": ["important"],
        "level": "info",
    } in log.events

    log.debug("This debug message should not be logged")
    assert len(log.events) == 1


def test_json_output(log: TermaLogger):
    # Set up JSON output and test logging
    log.set_json_output(True)
    log.info("JSON-formatted info message", pancakes="waffles")
    assert log.bytes_lines[0].endswith(
        b'"level":"info","event":"JSON-formatted info message","labels":null,"exception":null,"pancakes":"waffles"}'
    )


def test_extra_context(log: TermaLogger):
    # Test asserting on event dictionaries directly
    log.info("This message has extra context entries", ip="174.192.0.1", thenumber=42)
    assert {
        "event": "This message has extra context entries",
        "level": "info",
        "ip": "174.192.0.1",
        "thenumber": 42,
    } in log.events


def test_bound_logger(log: TermaLogger):
    test_events = [
        {
            "event": "Bound logger with extra context",
            "level": "info",
            "bound_ctx": "persistent value",
            "non_bound_ctx": {"fruit": ["apple", "strawberry", "kiwi"]},
        },
        {
            "event": "Another for good measure",
            "level": "warning",
            "bound_ctx": "persistent value",
            "more_bound_ctx": [4, 8, 3, 63, 13],
        },
    ]
    bound1 = log.bind(bound_ctx=test_events[0]["bound_ctx"])
    bound1.info(test_events[0]["event"], non_bound_ctx=test_events[0]["non_bound_ctx"])
    # Binding is very versatile and can have depth
    bound2 = bound1.bind(more_bound_ctx=test_events[1]["more_bound_ctx"])
    bound2.warn(test_events[1]["event"])
    assert test_events == log.events
