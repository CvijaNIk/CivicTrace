"""Synthetic publication failures; no real DNCP data or network."""

import errno
import json
import os
import signal
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import civictrace.dncp as dncp
import pytest
from test_dncp import setup


def complete(out):
    assert json.loads((out / "summary.json").read_text())["accepted"] == 1
    assert (out / "manifest.json").is_file()
    assert (out / "source.jsonl.gz").is_file()
    assert len(list(out.glob("*.canonical.json"))) == 1
    assert len(list(out.glob("*.raw"))) == 1
    assert (out / "validation.jsonl").is_file()


@pytest.mark.parametrize(
    "phase", ["mkdir", "snapshot", "raw", "canonical", "manifest", "summary", "rename"]
)
def test_faults(tmp_path, monkeypatch, phase):
    src, m = setup(tmp_path)
    out = tmp_path / "out"

    def fail(*args, **kwargs):
        raise OSError(errno.EIO, "injected")

    if phase == "mkdir":
        monkeypatch.setattr(dncp.tempfile, "mkdtemp", fail)
    elif phase == "rename":
        monkeypatch.setattr(dncp, "_publisher", lambda: fail)
    elif phase == "snapshot":
        original = Path.open

        def opening(p, *args, **kwargs):
            if p.name == "source.jsonl.gz" and args == ("wb",):
                fail()
            return original(p, *args, **kwargs)

        monkeypatch.setattr(Path, "open", opening)
    else:
        method = "write_bytes" if phase == "raw" else "write_text"
        original = getattr(Path, method)

        def writing(p, *args, **kwargs):
            if (phase == "raw" and p.suffix == ".raw") or p.name.endswith(phase + ".json"):
                original(p, args[0][:3], **kwargs)
                fail()
            return original(p, *args, **kwargs)

        monkeypatch.setattr(Path, method, writing)
    with pytest.raises(OSError, match="injected"):
        dncp.import_file(src, out, m)
    assert not os.path.lexists(out)
    assert not list(tmp_path.glob(".dncp-*"))


def test_cleanup_failure_is_explicit_and_never_publishes(tmp_path, monkeypatch):
    src, m = setup(tmp_path)
    m["expanded_sha256"] = "0" * 64

    def fail(*args):
        raise PermissionError("injected cleanup")

    monkeypatch.setattr(dncp.shutil, "rmtree", fail)
    with pytest.raises(dncp.IntakeError, match="private_staging_cleanup_failed") as exc:
        dncp.import_file(src, tmp_path / "out", m)
    assert isinstance(exc.value.__cause__, PermissionError)
    assert not (tmp_path / "out").exists()
    assert len(list(tmp_path.glob(".dncp-*"))) == 1


@pytest.mark.parametrize("kind", ["empty", "complete", "file", "link", "dangling"])
def test_existing_never_replaced(tmp_path, kind):
    src, m = setup(tmp_path)
    out = tmp_path / "out"
    target = tmp_path / "target"
    target.mkdir()
    if kind == "complete":
        dncp.import_file(src, out, m)
    elif kind == "empty":
        out.mkdir()
    elif kind == "file":
        out.write_text("keep")
    else:
        out.symlink_to(target if kind == "link" else tmp_path / "missing")
    before = out.lstat()
    with pytest.raises(dncp.IntakeError, match="output_exists"):
        dncp.import_file(src, out, m)
    assert out.lstat() == before
    if kind == "complete":
        complete(out)
    assert list(target.iterdir()) == []


@pytest.mark.parametrize("kind", ["empty", "file", "link", "dangling"])
def test_destination_created_at_commit_is_not_replaced(tmp_path, monkeypatch, kind):
    src, m = setup(tmp_path)
    out = tmp_path / "out"
    publish = dncp._publisher()

    def race(stage, dest):
        if kind == "empty":
            dest.mkdir()
        elif kind == "file":
            dest.write_text("keep")
        else:
            dest.symlink_to(tmp_path / ("missing" if kind == "dangling" else "sample.jsonl.gz"))
        publish(stage, dest)

    monkeypatch.setattr(dncp, "_publisher", lambda: race)
    with pytest.raises(FileExistsError):
        dncp.import_file(src, out, m)
    assert os.path.lexists(out)
    assert not list(tmp_path.glob(".dncp-*"))
    if kind == "empty":
        assert list(out.iterdir()) == []
    elif kind == "file":
        assert out.read_text() == "keep"
    else:
        assert out.is_symlink()


def test_parent_symlink(tmp_path):
    src, m = setup(tmp_path)
    parent = tmp_path / "alias"
    parent.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(dncp.IntakeError, match="output_parent_not_directory"):
        dncp.import_file(src, parent / "out", m)
    assert not (tmp_path / "out").exists()


def test_concurrent_writers_one_winner(tmp_path, monkeypatch):
    src, m = setup(tmp_path)
    barrier = Barrier(2)
    publish = dncp._publisher()

    def simultaneous(stage, out):
        barrier.wait(timeout=10)
        publish(stage, out)

    monkeypatch.setattr(dncp, "_publisher", lambda: simultaneous)

    def run():
        try:
            dncp.import_file(src, tmp_path / "out", m)
            return "ok"
        except FileExistsError:
            return "exists"

    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(lambda _: run(), range(2))) == ["exists", "ok"]
    complete(tmp_path / "out")
    assert not list(tmp_path.glob(".dncp-*"))


@pytest.mark.parametrize("phase", ["writing", "before", "after"])
def test_process_kill(tmp_path, phase):
    src, m = setup(tmp_path)
    manifest = tmp_path / "input.json"
    manifest.write_text(json.dumps(m))
    script = """
import json, os, signal, sys
from pathlib import Path
import civictrace.dncp as d
publish = d._publisher()
def crash(stage, out):
    if sys.argv[4] == 'after':
        publish(stage, out)
    os.kill(os.getpid(), signal.SIGKILL)
d._publisher = lambda: crash
if sys.argv[4] == 'writing':
    write = Path.write_bytes
    def interrupted(p, data):
        write(p, data[:3])
        os.kill(os.getpid(), signal.SIGKILL)
    Path.write_bytes = interrupted
d.import_file(sys.argv[1], sys.argv[2], json.loads(Path(sys.argv[3]).read_text()))
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(src), str(tmp_path / "out"), str(manifest), phase],
        timeout=15,
    )
    assert result.returncode == -signal.SIGKILL
    if phase == "after":
        complete(tmp_path / "out")
        assert not list(tmp_path.glob(".dncp-*"))
    else:
        assert not (tmp_path / "out").exists()
        stages = list(tmp_path.glob(".dncp-*"))
        assert len(stages) == 1
        assert stages[0].stat().st_mode & 0o777 == 0o700
        # Recovery never promotes an abandoned staging directory: retry afresh.
        dncp.import_file(src, tmp_path / "out", m)
        complete(tmp_path / "out")


def test_unsupported_fails_closed(tmp_path, monkeypatch):
    src, m = setup(tmp_path)
    monkeypatch.setattr(dncp.sys, "platform", "unsupported")
    with pytest.raises(dncp.IntakeError, match="atomic_publication_unsupported"):
        dncp.import_file(src, tmp_path / "out", m)
    assert not list(tmp_path.glob(".dncp-*"))


@pytest.mark.parametrize(
    "code", [errno.ENOSYS, errno.EINVAL, errno.EOPNOTSUPP, errno.EXDEV, errno.EIO]
)
def test_kernel_refusal_never_falls_back(tmp_path, monkeypatch, code):
    src, m = setup(tmp_path)

    class Rename:
        def __call__(self, *args):
            dncp.ctypes.set_errno(code)
            return -1

    class Library:
        renameat2 = Rename()

    monkeypatch.setattr(dncp.ctypes, "CDLL", lambda *a, **kw: Library())
    with pytest.raises((dncp.IntakeError, OSError)):
        dncp.import_file(src, tmp_path / "out", m)
    assert not (tmp_path / "out").exists()
    assert not list(tmp_path.glob(".dncp-*"))


def test_missing_libc_primitive(tmp_path, monkeypatch):
    src, m = setup(tmp_path)
    monkeypatch.setattr(dncp.ctypes, "CDLL", lambda *a, **kw: object())
    with pytest.raises(dncp.IntakeError, match="atomic_publication_unsupported"):
        dncp.import_file(src, tmp_path / "out", m)
    assert not list(tmp_path.glob(".dncp-*"))


def test_exception_after_committed_publication_preserves_output(tmp_path, monkeypatch):
    """A post-rename interrupt must not misreport a missing staging directory."""
    src, m = setup(tmp_path)
    out = tmp_path / "out"
    real_publish = dncp._publisher()

    def publish_then_interrupt(stage, destination):
        real_publish(stage, destination)
        raise KeyboardInterrupt("injected after successful publication")

    monkeypatch.setattr(dncp, "_publisher", lambda: publish_then_interrupt)
    with pytest.raises(KeyboardInterrupt, match="injected after successful publication"):
        dncp.import_file(src, out, m)
    complete(out)
    assert not list(tmp_path.glob(".dncp-*"))


def test_no_cleanup_after_success(tmp_path, monkeypatch):
    src, m = setup(tmp_path)

    def unexpected(*args):
        pytest.fail("published directory must never be cleaned up")

    monkeypatch.setattr(dncp.shutil, "rmtree", unexpected)
    dncp.import_file(src, tmp_path / "out", m)
    complete(tmp_path / "out")


def test_individual_move_failure_cannot_leave_partial_output(tmp_path, monkeypatch):
    """Regression: PR #30 leaves its first moved file when the second move fails."""
    src, m = setup(tmp_path)
    out = tmp_path / "out"

    rename = Path.rename
    calls = 0

    def fail(*args):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError(errno.EIO, "individual move failed")
        return rename(*args)

    monkeypatch.setattr(Path, "rename", fail)
    try:
        dncp.import_file(src, out, m)
    except OSError:
        assert not os.path.lexists(out)
    else:
        complete(out)
