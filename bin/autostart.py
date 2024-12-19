#!/bin/env python3
"""Restart an application when its source changes (like using Flask in Debug-Mode).

Requires Watchdog: https://github.com/gorakhargosh/watchdog

> pip install watchdog

Examples:
    ./autostart.py -p '*.py' -i 'venv/*' flake8 autostart.py --max-line-length 120
    ./autostart.py -p '*.py' -i 'venv/*' mypy ./autostart.py
"""
import pathlib
import shutil
import signal
import subprocess
import sys
import logging
from typing import Callable, Optional, List, Any

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler, FileSystemEvent
from argparse import ArgumentParser, Namespace, REMAINDER
import time

# Constants
EVENT_TYPES_TO_CONSIDER: tuple[str, ...] = ('modified', 'created', 'deleted')
DEFAULT_PATTERNS: List[str] = ['*.py']
DEFAULT_IGNORE_PATTERNS: List[str] = ['venv/*']

# Setup Logging
logging.basicConfig(format='[%(asctime)s %(funcName)s]:: %(message)s', datefmt='%s')
logger = logging.getLogger('watcher')
logger.setLevel(logging.DEBUG)


class FileChangeHandler(PatternMatchingEventHandler):
    def __init__(self, restart_callback: Callable[[], None], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.restart_callback: Callable[[], None] = restart_callback

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.event_type in EVENT_TYPES_TO_CONSIDER and not event.is_directory:
            logger.debug(f"Change detected in: {event.src_path!r}")
            self.restart_callback()


class ApplicationReloader:
    def __init__(self, script_path: pathlib.Path, args: list[str] = []) -> None:
        self.script_path: pathlib.Path = script_path
        self.args = args
        self.process: Optional[subprocess.Popen] = None

    def start_app(self) -> None:
        logger.debug(f'Create child process: {str(self.script_path)} [{self.args}]')
        self.process = subprocess.Popen([sys.executable, str(self.script_path)] + self.args)
        logger.debug(f"Started process with PID: {self.process.pid}")

    def restart_app(self) -> None:
        if self.process:
            logger.debug(f"Stopping process with PID: {self.process.pid}")
            self.process.send_signal(signal.SIGTERM)
            self.process.wait()
        self.start_app()


def main(exe_path: pathlib.Path, args: list[str], watch_dir: pathlib.Path) -> None:
    reloader = ApplicationReloader(exe_path, args=args)
    reloader.start_app()

    event_handler = FileChangeHandler(
        reloader.restart_app,
        patterns=DEFAULT_PATTERNS,
        ignore_patterns=DEFAULT_IGNORE_PATTERNS
    )
    observer = Observer()
    observer.schedule(event_handler, str(watch_dir), recursive=True)
    observer.start()

    try:
        while True:
            # keep the main thread active
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Stopping...")
        observer.stop()
        if reloader.process is not None:
            reloader.process.terminate()
        observer.join()


def parse_args(argv: List[str]) -> Namespace:
    """
    Parses the command-line arguments.
    Args:
        argv (List[str]): Command-line arguments.
    """
    parser = ArgumentParser(
        prog='autostart.py',
        description="Restart an application when its source changes."
    )
    parser.add_argument(
        "executable",
        type=pathlib.Path,
        help="Path to the script to run.",
    )
    parser.add_argument(
        "-d",
        "--directory",
        type=pathlib.Path,
        default=pathlib.Path('.'),
        help="Directory to watch for changes.",
    )
    parser.add_argument(
        "-p",
        "--patterns",
        type=pathlib.Path,
        default=DEFAULT_PATTERNS,
        help=f"Patterns to watch. Default: {DEFAULT_PATTERNS}",
    )
    parser.add_argument(
        "-i",
        "--ignore_patterns",
        type=pathlib.Path,
        default=DEFAULT_IGNORE_PATTERNS,
        help=f"Patterns to ignore. Default: {DEFAULT_IGNORE_PATTERNS}",
    )
    parser.add_argument(
        "extra_args",
        nargs=REMAINDER,
        help="Extra arguments to pass to another application"
    )

    args = parser.parse_args(argv[1:])
    return args


def get_exe(arg: pathlib.Path) -> pathlib.Path | None:
    if arg.is_file() and arg.exists():
        return arg
    path = shutil.which(arg)
    if path:
        return pathlib.Path(path)
    return None


if __name__ == "__main__":
    args = parse_args(sys.argv)

    executable: pathlib.Path | None = get_exe(args.executable)
    directory_to_watch: pathlib.Path = pathlib.Path(args.directory)

    if not executable:
        print(f"Error: {args.executable} is not a valid file/executable.", file=sys.stderr)
        sys.exit(1)

    if not directory_to_watch.is_dir() or not directory_to_watch.exists():
        print(f"Error: {directory_to_watch} is not a valid directory.", file=sys.stderr)
        sys.exit(1)

    main(executable, args.extra_args, directory_to_watch)
