"""Deployment behavior without installing packages or changing host startup."""

import importlib.util
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(
        "wes_test_" + name, ROOT / "scripts" / (name + ".py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("platform", ["win32", "linux"])
def test_install_repairs_incomplete_venv_and_uses_its_python(tmp_path, monkeypatch, platform):
    package = load_script("package")
    monkeypatch.setattr(package, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        package,
        "sys",
        SimpleNamespace(platform=platform, executable=sys.executable, version_info=(3, 12)),
    )
    (tmp_path / ".venv").mkdir()
    (tmp_path / "requirements.txt").write_text("pygame==2.6.1\n")
    for name in ("start.sh", "run_game.sh", "setup_rpi.sh", "install_autostart.sh"):
        (tmp_path / name).write_text("#!/bin/bash\n")
    calls = []

    def command(args):
        calls.append(args)
        if args[1:3] == ["-m", "venv"]:
            python = package.venv_python()
            python.parent.mkdir(parents=True, exist_ok=True)
            python.touch()
        return True

    monkeypatch.setattr(package, "run_command", command)
    assert package.install()
    assert calls[0] == [sys.executable, "-m", "venv", str(tmp_path / ".venv")]
    assert calls[1] == [
        str(package.venv_python()),
        "-m",
        "pip",
        "install",
        "-r",
        str(tmp_path / "requirements.txt"),
    ]
    assert len(calls) == 2


def test_failed_install_never_configures_autostart(tmp_path, monkeypatch):
    package = load_script("package")
    monkeypatch.setattr(package, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        package,
        "sys",
        SimpleNamespace(platform="linux", executable=sys.executable, version_info=(3, 12)),
    )
    calls = []
    monkeypatch.setattr(package, "run_command", lambda args: calls.append(args) or False)
    assert not package.rpi_setup()
    assert calls == [[sys.executable, "-m", "venv", str(tmp_path / ".venv")]]


def test_build_stops_when_packager_install_fails(tmp_path, monkeypatch):
    package = load_script("package")
    monkeypatch.setattr(package, "PROJECT_ROOT", tmp_path)
    python = package.venv_python()
    python.parent.mkdir(parents=True)
    python.touch()
    calls = []
    monkeypatch.setattr(package, "run_command", lambda args: calls.append(args) or False)
    assert not package.build()
    assert calls == [[str(python), "-m", "pip", "install", "pyinstaller==6.19.0"]]


def test_missing_command_returns_failure(monkeypatch):
    package = load_script("package")

    def missing(*args, **kwargs):
        raise FileNotFoundError("missing interpreter")

    monkeypatch.setattr(package.subprocess, "run", missing)
    assert package.run_command(["does-not-exist"]) is False


def test_clean_preserves_dependencies_and_external_paths(tmp_path, monkeypatch):
    package = load_script("package")
    project = tmp_path / "project"
    external = tmp_path / "external"
    monkeypatch.setattr(package, "PROJECT_ROOT", project)
    for directory in (
        project / "build",
        project / "dist",
        project / "engine" / "__pycache__",
        project / ".venv" / "__pycache__",
        project / "legacy_reference" / "__pycache__",
        external,
    ):
        directory.mkdir(parents=True)
        (directory / "keep.txt").write_text("data")
    with pytest.raises(ValueError):
        package._remove_artifact(external)
    with pytest.raises(ValueError):
        package._remove_artifact(project)
    assert package.clean()
    assert not (project / "build").exists()
    assert not (project / "dist").exists()
    assert not (project / "engine" / "__pycache__").exists()
    assert (project / ".venv" / "__pycache__" / "keep.txt").exists()
    assert (project / "legacy_reference" / "__pycache__" / "keep.txt").exists()
    assert (external / "keep.txt").exists()


def test_spec_includes_only_active_runtime_assets():
    captured = {}

    def analysis(scripts, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(pure=[], scripts=scripts, binaries=[], datas=kwargs["datas"])

    runpy.run_path(
        str(ROOT / "wes.spec"),
        init_globals={
            "SPECPATH": str(ROOT),
            "Analysis": analysis,
            "PYZ": lambda *a, **kw: object(),
            "EXE": lambda *a, **kw: object(),
            "COLLECT": lambda *a, **kw: object(),
        },
    )
    assert set(captured["excludes"]) == {"numpy", "pkg_resources"}
    included = [Path(source) for source, destination in captured["datas"]]
    assert all(path.is_file() for path in included)
    assert {path.name for path in included if path.parent.name == "media"} == {
        "ferret-long-sprite.png",
        "ferret-long-sprite.json",
        "soupbowl.png",
    }
    assert {destination for source, destination in captured["datas"]} == {"media", "sounds"}
    assert all(path.suffix in (".png", ".json", ".wav") for path in included)
    assert not any("legacy_reference" in path.parts or "games" in path.parts for path in included)
    assert not any(
        path.name in ("settings.json", "high_scores.json", "controller_config.json")
        for path in included
    )


def test_autostart_rendering_quotes_expansion_characters():
    config = load_script("autostart_config")
    directory = "/home/user/My $Games %n"
    desktop = config.render_desktop(directory)
    assert 'Exec=/bin/bash "' in desktop
    assert "\\\\$Games %%n" in desktop
    service = config.render_service(directory, "test-user", "/home/test user")
    assert 'WorkingDirectory="/home/user/My $Games %%n"' in service
    assert 'Environment="HOME=/home/test user"' in service
    assert "My $$Games %%n" in service
    assert "Restart=always" in service
    assert service.count("ExecStart=") == 1
    with pytest.raises(ValueError):
        config.render_service("/home/user\nExecStart=bad", "user", "/home/user")
    with pytest.raises(ValueError):
        config.render_service("/home/user", "user\nUser=root", "/home/user")


def test_shell_scripts_have_linux_line_endings_and_valid_syntax():
    git_bash = Path("C:/Program Files/Git/bin/bash.exe")
    bash = str(git_bash) if git_bash.exists() else shutil.which("bash")
    filenames = ("setup_rpi.sh", "start.sh", "run_game.sh", "install_autostart.sh")
    for filename in filenames:
        data = (ROOT / filename).read_bytes()
        assert data.startswith(b"#!/usr/bin/env bash\n")
        assert b"\r\n" not in data
    if not bash:
        pytest.skip("Bash is unavailable; line endings were validated")
    for filename in filenames:
        result = subprocess.run([bash, "-n", filename], cwd=ROOT, capture_output=True, text=True)
        if sys.platform == "win32" and result.returncode == 0xC0000142:
            pytest.skip(
                "Git Bash cannot initialize in this Windows sandbox; run bash -n externally"
            )
        assert result.returncode == 0, result.stderr
