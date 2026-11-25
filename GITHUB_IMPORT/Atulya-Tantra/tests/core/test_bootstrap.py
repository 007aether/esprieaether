from __future__ import annotations

import hashlib
import io
import tarfile
from pathlib import Path

import pytest

from tools import bootstrap
from tools.plugins.brain.local_llm import _extract_runtime


class _Response(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def test_bootstrap_download_checks_sha256_before_replacing_target(
    project_temp_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = b"trusted asset"
    target = project_temp_dir / "asset.bin"
    target.write_bytes(b"existing verified asset")
    monkeypatch.setattr(bootstrap, "urlopen", lambda *_args, **_kwargs: _Response(content))

    with pytest.raises(OSError, match="integrity"):
        bootstrap._download("https://example.invalid/asset", target, expected_sha256="0" * 64)

    assert target.read_bytes() == b"existing verified asset"
    assert not target.with_suffix(".bin.part").exists()

    expected = hashlib.sha256(content).hexdigest()
    bootstrap._download("https://example.invalid/asset", target, expected_sha256=expected)
    assert target.read_bytes() == content


def test_runtime_tar_rejects_path_traversal(project_temp_dir: Path) -> None:
    archive_path = project_temp_dir / "unsafe.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        payload = b"outside"
        entry = tarfile.TarInfo("../outside.txt")
        entry.size = len(payload)
        archive.addfile(entry, io.BytesIO(payload))

    destination = project_temp_dir / "runtime"
    destination.mkdir()
    with pytest.raises(RuntimeError, match="unsafe path"):
        _extract_runtime(archive_path, destination)
    assert not (project_temp_dir / "outside.txt").exists()


def test_prepare_gesture_assets_accepts_npm_package_without_license_docs(
    project_temp_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RED: npm 1.1.0 ships the runtime but no LICENSE/NOTICE.md inside the tarball."""
    payloads = {
        "vision_bundle.mjs": b"bundle",
        "wasm/vision_wasm_internal.js": b"internal-js",
        "wasm/vision_wasm_internal.wasm": b"internal-wasm",
        "wasm/vision_wasm_module_internal.js": b"module-js",
        "wasm/vision_wasm_module_internal.wasm": b"module-wasm",
        "wasm/vision_wasm_nosimd_internal.js": b"nosimd-js",
        "wasm/vision_wasm_nosimd_internal.wasm": b"nosimd-wasm",
    }
    archive_stream = io.BytesIO()
    with tarfile.open(fileobj=archive_stream, mode="w:gz") as archive:
        for name, payload in payloads.items():
            info = tarfile.TarInfo(f"package/{name}")
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    tarball = archive_stream.getvalue()
    integrity = "sha512-" + __import__("base64").b64encode(
        hashlib.sha512(tarball).digest()
    ).decode("ascii")
    metadata = (
        '{"version":"'
        + bootstrap.MEDIAPIPE_VERSION
        + '","dist":{"integrity":"'
        + integrity
        + '"}}'
    ).encode("utf-8")
    model = b"gesture-model-bytes"

    monkeypatch.setattr(bootstrap, "PROJECT_ROOT", project_temp_dir)
    monkeypatch.setattr(
        bootstrap,
        "MEDIAPIPE_FILE_SHA256",
        {name: hashlib.sha256(payload).hexdigest() for name, payload in payloads.items()},
    )
    monkeypatch.setattr(bootstrap, "GESTURE_MODEL_SHA256", hashlib.sha256(model).hexdigest())

    def fake_urlopen(url, *_args, **_kwargs):
        if "/tasks-vision/" in url and url.endswith(".tgz"):
            return _Response(tarball)
        if url.endswith("/" + bootstrap.MEDIAPIPE_VERSION):
            return _Response(metadata)
        return _Response(model)

    monkeypatch.setattr(bootstrap, "urlopen", fake_urlopen)

    assert bootstrap.prepare_gesture_assets() is True

    runtime = project_temp_dir / "models" / "runtime" / "mediapipe"
    for name, payload in payloads.items():
        assert (runtime / name).read_bytes() == payload
    assert (project_temp_dir / "models" / "gesture" / "gesture_recognizer.task").read_bytes() == model
