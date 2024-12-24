#!/bin/env python3
"""This is a simple self-contained script to reload an arbitrary application
when its source changes (like using Flask in debug mode). It comes without
any 3rd party dependencies and can run standalone - a copy of this script is
all you need.

Examples:
    ./autostart.py -p '*.py' -i 'venv/*' flake8 autostart.py --max-line-length 120
    ./autostart.py -p '*.py' -i 'venv/*' mypy ./autostart.py
    ./autostart.py -p '*.py' -i 'venv/*' "$(which python3)" ./server.py
"""
import ctypes
import errno
import fnmatch
import functools
import logging
import os
import pathlib
import signal
import struct
import subprocess
import sys
import time
from argparse import ArgumentParser, Namespace, REMAINDER
from dataclasses import dataclass
from typing import Optional, List

# =============================================================================
# Constants
# =============================================================================

IN_CREATE = 0x00000100
IN_MODIFY = 0x00000002

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


# =============================================================================
# Argument Parsing
# =============================================================================

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
        help="Path to the script or executable to run."
    )
    parser.add_argument(
        "app_args",
        nargs=REMAINDER,
        help="Extra arguments to pass to the application, e.g. my_script.py --someopt"
    )
    parser.add_argument(
        "-d", "--directory",
        type=pathlib.Path,
        default=pathlib.Path('.'),
        help="Directory to watch for changes (default: current directory)."
    )
    parser.add_argument(
        "-p", "--patterns",
        default="",
        help=(
            "Comma-separated list of patterns to match. "
            "If not empty, only filenames matching at least one of these patterns "
            "will trigger a restart. Example: '*.py,*.json'"
        )
    )
    parser.add_argument(
        "-i", "--ignore_patterns",
        default="",
        help=(
            "Comma-separated list of patterns to ignore. "
            "Any filename matching any ignore pattern will NOT trigger a restart. "
            "Example: 'venv/*,^\\.'"
        )
    )

    args = parser.parse_args(argv[1:])
    return args


# =============================================================================
# Rate-limiting decorator
# =============================================================================

def rate_limit(min_interval: float):
    """
    Decorator to prevent a function from being called more than once
    every `min_interval` seconds.
    """
    def decorator(func):
        last_called = [0.0]  # use a mutable object to allow closure updates

        @functools.wraps(func)
        def wrapper(*fargs, **fkwargs):
            now = time.time()
            elapsed = now - last_called[0]
            if elapsed < min_interval:
                logger.debug(
                    f"Skipping call (interval < {min_interval:.2f}s). "
                    f"Elapsed: {elapsed:.2f}s."
                )
                return
            last_called[0] = now
            return func(*fargs, **fkwargs)

        return wrapper
    return decorator


# =============================================================================
# ApplicationReloader
# =============================================================================

class ApplicationReloader:
    """
    Manages a child process that can be started/restarted whenever file changes occur.
    """
    def __init__(self, script_path: pathlib.Path, args: List[str] | None = None) -> None:
        if args is None:
            args = []
        self.script_path: pathlib.Path = script_path
        self.args = args
        self.process: Optional[subprocess.Popen] = None

    def start_app(self) -> None:
        """
        Start the child process with the given script + args.
        """
        logger.debug(f"Starting child process: {self.script_path} {self.args}")
        try:
            self.process = subprocess.Popen([str(self.script_path)] + self.args)
            logger.debug(f"Child process started with PID: {self.process.pid}")
        except FileNotFoundError as e:
            logger.error(f"Failed to start process: {e}")
            sys.exit(1)

    @rate_limit(1.0)
    def restart_app(self) -> None:
        """
        Stop the existing process and restart it. Enforces a minimum 1-second interval
        between restarts via @rate_limit.
        """
        if self.process:
            logger.debug(f"Stopping process with PID: {self.process.pid}")
            self.process.send_signal(signal.SIGTERM)
            self.process.wait()
            logger.debug("Process stopped.")
        self.start_app()


# =============================================================================
# FileSystemEvent + Base Handler
# =============================================================================

@dataclass
class FileSystemEvent:
    """Represents one inotify event."""
    wd: int
    mask: int
    cookie: int
    length: int
    name: str
    path: pathlib.Path


class FileChangeHandler:
    """
    Base class for callbacks.
    Subclass this or use as-is to implement your own logic in on_any_event().
    """
    def on_any_event(self, event: FileSystemEvent) -> None:
        """Callback that is triggered for every inotify event."""
        logger.debug("FileChangeHandler.on_any_event called with:")
        logger.debug(f"  wd     = {event.wd}")
        logger.debug(f"  mask   = {event.mask:#010x}")
        logger.debug(f"  cookie = {event.cookie}")
        logger.debug(f"  len    = {event.length}")
        logger.debug(f"  name   = {event.name}")
        logger.debug(f"  path   = {event.path}")


# =============================================================================
# Ctypes: inotify syscalls
# =============================================================================

libc = ctypes.CDLL("libc.so.6", use_errno=True)

inotify_init = libc.inotify_init
inotify_init.argtypes = []
inotify_init.restype = ctypes.c_int

inotify_add_watch = libc.inotify_add_watch
inotify_add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
inotify_add_watch.restype = ctypes.c_int

inotify_rm_watch = libc.inotify_rm_watch
inotify_rm_watch.argtypes = [ctypes.c_int, ctypes.c_int]
inotify_rm_watch.restype = ctypes.c_int


# =============================================================================
# InotifyWatcher
# =============================================================================

class InotifyWatcher:
    """
    A wrapper around the inotify FD, allowing you to:
      - Add watches on directories/paths with specific masks.
      - Register FileChangeHandlers for subsets of masks.
      - Loop over inotify events and dispatch to handlers.
    """

    def __init__(self):
        self._inotify_fd = inotify_init()
        if self._inotify_fd < 0:
            err = ctypes.get_errno()
            raise OSError(err, f"inotify_init failed: {os.strerror(err)}")

        self._wd_map = {}  # wd -> (path, mask)
        self._handlers = []  # List of (mask, handler)

    def add_watch(self, path: pathlib.Path, mask: int) -> int:
        """Add a watch on `path` with the given `mask`; returns the watch descriptor."""
        wd = inotify_add_watch(self._inotify_fd, str(path).encode('utf-8'), mask)
        if wd < 0:
            err = ctypes.get_errno()
            raise OSError(err, f"inotify_add_watch failed on {path}: {os.strerror(err)}")

        self._wd_map[wd] = (path, mask)
        return wd

    def add_dir_watch(self, path: pathlib.Path, mask: int) -> None:
        """Adds a watch recursively for the given directory path."""
        if not path.is_dir() or not path.exists():
            raise OSError(errno.ENOTDIR, os.strerror(errno.ENOTDIR), path)
        self.add_watch(path, mask)

        # Recurse
        for root, dirnames, _ in path.walk():
            for dirname in dirnames:
                full_path = root.joinpath(dirname)
                # os.path.islink(full_path)
                if full_path.is_symlink():
                    continue
                logger.debug(f'Adding watch to {full_path}')
                self.add_watch(full_path, mask)

    def remove_watch(self, wd: int) -> None:
        """Remove a previously added watch."""
        if wd not in self._wd_map:
            return
        res = inotify_rm_watch(self._inotify_fd, wd)
        if res < 0:
            err = ctypes.get_errno()
            raise OSError(err, f"inotify_rm_watch failed: {os.strerror(err)}")
        del self._wd_map[wd]

    def register_handler(self, mask: int, handler: FileChangeHandler) -> None:
        """
        Register a handler for events specified by `mask`.
        If (event_mask & mask) != 0, we call handler.on_any_event().
        """
        self._handlers.append((mask, handler))

    def watch_loop(self) -> None:
        """
        Blocking loop that reads events from the inotify FD and dispatches them
        to registered handlers whose masks intersect with the event mask.
        """
        logger.info("Starting inotify watch loop. Press Ctrl+C to stop.")
        try:
            while True:
                data = os.read(self._inotify_fd, 4096)
                if not data:
                    continue

                offset = 0
                while offset < len(data):
                    event_fmt = 'iIII'
                    event_size = struct.calcsize(event_fmt)
                    wd, mask, cookie, name_len = struct.unpack_from(event_fmt, data, offset)
                    offset += event_size

                    name_bytes = data[offset:offset + name_len]
                    offset += name_len

                    filename = name_bytes.rstrip(b'\x00').decode('utf-8', errors='replace')

                    fs_event = FileSystemEvent(
                        wd=wd,
                        mask=mask,
                        cookie=cookie,
                        length=name_len,
                        name=filename,
                        path=self._wd_map[wd][0].joinpath(filename)
                    )

                    logger.debug(f'[InotifyWatcher] Received FS event: {fs_event.name}')

                    # Dispatch to any handler for which (mask & h_mask) != 0
                    for h_mask, h_instance in self._handlers:
                        if fs_event.mask & h_mask:
                            h_instance.on_any_event(fs_event)

        except KeyboardInterrupt:
            logger.info("Watch loop interrupted by user.")
        finally:
            os.close(self._inotify_fd)
            self._inotify_fd = -1
            logger.info("Inotify file descriptor closed.")


# =============================================================================
# ReloadHandler
# =============================================================================

class ReloadHandler(FileChangeHandler):
    """
    Handler that restarts an application whenever an event
    is detected, subject to patterns/ignore_patterns.
    """
    def __init__(
        self,
        reloader: ApplicationReloader,
        patterns: List[str],
        ignore_patterns: List[str]
    ):
        super().__init__()
        self.reloader = reloader

        # Pre-compile each pattern into a regex object
        self.patterns = patterns
        self.ignore_patterns = ignore_patterns

    def is_ignored(self, path: pathlib.Path) -> bool:
        """Returns True if path is ignored by any ignore pattern"""
        # pathlib.Path(...).match() does not really work for this.
        # pathlib.Path(...).full_match() is Python 3.13+
        return bool(any(fnmatch.fnmatch(str(path), ip) for ip in self.ignore_patterns))

    def matches(self, path: pathlib.Path) -> bool:
        """Returns True if path matches at least one pattern"""
        return bool(any(path.match(ip) for ip in self.patterns))

    def on_any_event(self, event: FileSystemEvent) -> None:
        logger.debug(f"[ReloadHandler] Checking file: {event.path}")

        # 1. Check ignore patterns first
        if self.is_ignored(event.path):
            logger.debug(f"[ReloadHandler] Ignoring file '{event.name}'")
            return

        # 2. If we have any patterns, ensure it matches at least one
        if not self.matches(event.path):
            logger.debug(
                f"[ReloadHandler] Ignoring file '{event.name}' "
                f"(does NOT match any of the provided patterns)."
            )
            return

        logger.debug(
            f"[ReloadHandler] File changed: {event.name}, mask={hex(event.mask)}. "
            "Triggering application restart."
        )
        self.reloader.restart_app()


# =============================================================================
# Main
# =============================================================================

def main():
    args = parse_args(sys.argv)

    # 1) Parse comma-separated patterns into lists
    patterns_list = [p.strip() for p in args.patterns.split(',') if p.strip()]
    ignore_list = [p.strip() for p in args.ignore_patterns.split(',') if p.strip()]

    logger.info(f"Watching directory: {args.directory}")
    logger.info(f"Executable: {args.executable}")
    logger.info(f"Application args: {args.app_args}")
    logger.info(f"Include patterns: {patterns_list or '(none)'}")
    logger.info(f"Ignore patterns: {ignore_list or '(none)'}")

    # 2) Prepare the reloader
    reloader = ApplicationReloader(script_path=args.executable, args=args.app_args)

    # 3) Start the child process
    reloader.start_app()

    # 4) Create an InotifyWatcher
    watcher = InotifyWatcher()

    # 5) Add a watch for CREATE and MODIFY events
    watch_mask = IN_CREATE | IN_MODIFY
    wd = watcher.add_dir_watch(args.directory, watch_mask)
    logger.debug(f"Watching path '{args.directory}' (wd={wd})")

    # 6) Register a ReloadHandler with patterns/ignore_patterns
    handler = ReloadHandler(reloader, patterns_list, ignore_list)
    watcher.register_handler(watch_mask, handler)

    # 7) Start the blocking watch loop
    watcher.watch_loop()


if __name__ == "__main__":
    main()
