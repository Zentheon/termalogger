# What is *TermaLogger*
A straightworward, centralized way of using Structlog that makes common functionality dead simple and adds some nice extras along the way.

# Usage
Simply import and create an instance of `TermaLogger`:
```python
from termalogger import TermaLogger

log = TermaLogger("coolapp")

target_dir = Path("images/coolphotos")
for file in target_dir.iterdir():
    log.info("Processing a photo...", label="photos", path=file)
    ...
```
You can provide a number of initial args, but the bound logger's `name` is the only required one.

The methodology behind TermaLogger follows that of the prevailant [Twelve-Factor Logging](https://12factor.net/logs), in that files are not of its concern. However, if you want that functionality, you can enable JSON output and set `log.json_factory` to use a factory such as `structlog.BytesLoggerFactory(file="logfile")`, where `logfile` is any Bytes file instance. Alternatively, you could do something like `log.json_processors.append(log.line_tracker)` and dump `log.bytes_lines` to a file, but using the line trackers is only really a good idea for tests.

## Filtering
### `level` - [`__init__, settings, set_level`] - (`str | int`)

Typical loglevel filtering. This uses `Structlog`'s quite efficient `make_filtering_bound_logger` and is useful to set up the overall run environment. Can be either a number corresponding to a [native loglevel](https://docs.python.org/3/library/logging.html#logging-levels) or the level's name.

### `cache_logger_on_first_use` - [`__init__, settings`] - (`bool`)

Directly corresponds to the Structlog opt: See [Structlog performance docs](https://www.structlog.org/en/stable/performance.html)

### `format_json` - [`__init__, set_json_output`] - (`bool`)

Sets appropriate configurations for structured JSON output using [orjson](https://pypi.org/project/orjson/)

### `filter` - [`__init__, settings, set_filter`] - (`list[str]`)

The real power behind `LogWrapper` is the `label` filtering. Labels effectively offer a much more versatile way of getting the information you want than jankily adding custom levels and trying to sift through them. This is the future, after all.

To use labels, simply add an event to a log message:
```python
for fruit in fruit_list:
    try:
        log.debug("Processing a fruit...", labels=["fruit", "loop"], fruit=fruit)
        # Do some fruity processing stuff
    except Exception as exc:
        log.error("Couldn't process a fruit!", label="fruit", fruit=fruit, exc_info=exc)
```
`label` and `labels` can be used interchangeably with either a single label or list of them. While debugging, you can start filtering out unwanted noise by setting:
```python
log.settings(level="debug", filter={"debug": ["fruit"]})
```
Which would drop any debug messages not containing a "fruit" label.

Filtering is only performed on `debug` messages by default, meaning that if you set loglevel to `debug`, then any `debug` message with labels won't be shown if `log.debug_filter=[]` (default). This is not the case for higher levels unless you explicitly set `log.set_filter({"warn": []})` or `log.filter_enable["warn"] = True`.

## Tracking & Tests
Structlog's immensely powerful processor pipeline and the self-contained nature of using a class to pull its strings comes with another, quite convenient bonus: **Event tracking**. `TermaLogger` has three noteworthy attributes (lists) for keeping historical data:

- `self.events`: Event dictionaries.
- `self.str_lines`: Rendered lines (strings)
- `self.bytes_lines` Rendered lines (bytes)

Normally, these lists won't be populated with anything. It's only until you add the respective processors when they become useful:
```python
from termalogger import TermaLogger

log = TermaLogger("app_tests")

# Event dictionary list
log.shared_processors.append(log.event_tracker)
# Rendered lines list (str or bytes, respectively)
log.console_processors.append(log.lines_tracker)
log.json_processors.append(log.lines_tracker)
# Recreate the logger with updated processors
log.settings()
```
At which point you'll see the aforementioned lists start to be populated by log entries! This is especially useful when building your tests, a more complete example of which can be found in TermaLogger's own test routines.

# Other Stuff

## Contributing

Contributions are very welcome!

- Issues: Don't hesitate to report something, even if it's as small as a semantics inconsistency.
- PRs: The main pointer to keep in mind is to take advantage Structlog's versatility wherever sensible when adding new things. Also ideally creating relevant tests!

## Resources

- Come hang out and share cool stuff with the community on [Discord](https://discord.gg/3gtNAQgv2G)!
- The (so far) one other project in the Terma* series: [TermaConfig](https://github.com/Zentheon/termaconfig)

## License

[GNU General Public License v3.0](./LICENSE)
