"""Atomic user-data storage and scoped demo/difficulty context."""

from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
import json
import logging
import os
from pathlib import Path
import shutil
import tempfile
import time

log = logging.getLogger(__name__)
_demo = ContextVar("wes_demo", default=False)
_difficulty = ContextVar("wes_difficulty", default="normal")


def data_dir():
    """Return the writable data location without creating it merely by reading."""
    override = os.environ.get("WES_DATA_DIR")
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "WES"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "wes"


def data_path(name):
    path = Path(name)
    return path if path.is_absolute() else data_dir() / path


def is_demo():
    return _demo.get()


def difficulty_key(difficulty=None):
    value = _difficulty.get() if difficulty is None else difficulty
    return getattr(value, "name", str(value)).lower()


@contextmanager
def persistence_session(*, demo=False, difficulty=None):
    demo_token = _demo.set(bool(demo) or _demo.get())
    difficulty_token = _difficulty.set(difficulty_key(difficulty))
    try:
        yield
    finally:
        _difficulty.reset(difficulty_token)
        _demo.reset(demo_token)


class JsonStore:
    """JSON replacement is atomic; the previous good copy is retained as .bak.

    Read failures are logged and preserved as .corrupt-* before recovery. Legacy
    project data is imported only for the default location, never a test override.
    """

    def __init__(self, path, *, legacy_name=None):
        self.path = Path(path)
        self.last_error = None
        self.legacy_name = legacy_name

    def load(self, default=None):
        fallback = {} if default is None else default
        path = self.path
        if not path.exists() and self.legacy_name and not os.environ.get("WES_DATA_DIR"):
            legacy = Path(__file__).resolve().parent.parent / self.legacy_name
            if legacy.exists():
                path = legacy
        if not path.exists():
            return deepcopy(fallback)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("Expected a JSON object")
            if path != self.path and not is_demo():
                self.save(value)
            return value
        except (OSError, ValueError, TypeError) as exc:
            self.last_error = str(exc)
            log.warning("Cannot read %s: %s", path, exc)
            if path == self.path and not is_demo():
                try:
                    shutil.copy2(path, path.with_name(f"{path.name}.corrupt-{time.time_ns()}"))
                except OSError:
                    log.exception("Cannot preserve corrupt data: %s", path)
            backup = self.path.with_suffix(self.path.suffix + ".bak")
            try:
                value = json.loads(backup.read_text(encoding="utf-8"))
                if isinstance(value, dict):
                    return value
            except (OSError, ValueError, TypeError):
                pass
            return deepcopy(fallback)

    def save(self, value):
        if is_demo():
            return False
        temp_path = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=self.path.name + ".",
                suffix=".tmp",
                delete=False,
            ) as stream:
                temp_path = Path(stream.name)
                json.dump(value, stream, indent=2, allow_nan=False)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            if self.path.exists():
                # Never overwrite the recovery copy with malformed data.
                try:
                    old = json.loads(self.path.read_text(encoding="utf-8"))
                    if isinstance(old, dict):
                        shutil.copy2(self.path, self.path.with_suffix(self.path.suffix + ".bak"))
                except (OSError, ValueError):
                    pass
            os.replace(temp_path, self.path)
            if os.name != "nt":
                directory_fd = os.open(self.path.parent, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            self.last_error = None
            return True
        except (OSError, ValueError, TypeError) as exc:
            self.last_error = str(exc)
            log.error("Cannot save %s: %s", self.path, exc)
            return False
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    log.warning("Cannot remove temporary save file: %s", temp_path)
