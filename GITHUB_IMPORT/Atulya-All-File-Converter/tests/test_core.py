import json

import pytest
from PIL import Image

from atulya_all_file_converter import core


@pytest.fixture
def csv_file(tmp_path):
    p = tmp_path / "data.csv"
    p.write_text("name,age\nada,36\nlin,29\n")
    return str(p)


def test_csv_to_json(csv_file, tmp_path):
    out = str(tmp_path / "out.json")
    core.convert_file(csv_file, out)
    rows = json.load(open(out))
    assert [r["name"] for r in rows] == ["ada", "lin"]


def test_csv_to_xlsx(csv_file, tmp_path):
    out = str(tmp_path / "out.xlsx")
    core.convert_file(csv_file, out)
    assert (tmp_path / "out.xlsx").stat().st_size > 0


def test_json_to_yaml_roundtrip(tmp_path):
    src = tmp_path / "a.json"
    src.write_text(json.dumps({"k": "v"}))
    out = tmp_path / "a.yaml"
    core.convert_file(str(src), str(out))
    assert "k: v" in out.read_text()


def test_image_convert(tmp_path):
    src = tmp_path / "a.png"
    Image.new("RGB", (8, 8), "red").save(src)
    out = tmp_path / "a.jpg"
    core.convert_file(str(src), str(out))
    assert Image.open(out).format == "JPEG"


def test_batch_convert(csv_file, tmp_path):
    import os
    results = core.batch_convert(os.path.dirname(csv_file), "*.csv", str(tmp_path / "o"), "json")
    assert results[0][1] == "ok"


def test_file_hash(csv_file):
    assert core.compute_file_hash(csv_file)


def test_batch_progress_callback(csv_file, tmp_path):
    import os
    calls = []
    core.batch_convert(os.path.dirname(csv_file), "*.csv", str(tmp_path / "p"), "json",
                       progress=lambda d, t, n: calls.append((d, t, n)))
    assert calls == [(1, 1, "data")]


def test_batch_error_reported(tmp_path):
    (tmp_path / "bad.json").write_text("{not json")
    results = core.batch_convert(str(tmp_path), "*.json", str(tmp_path / "o"), "csv")
    assert results[0][1] == "error"
