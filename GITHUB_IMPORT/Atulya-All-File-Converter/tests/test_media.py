import shutil
import subprocess

import pytest

from atulya_all_file_converter import core
from atulya_all_file_converter.utils import detect_format

needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")
needs_soffice = pytest.mark.skipif(not shutil.which("soffice"), reason="LibreOffice not installed")


def _ff(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


@needs_ffmpeg
def test_wav_detected_as_wav_not_webp(tmp_path):
    wav = tmp_path / "t.wav"
    _ff("-f", "lavfi", "-i", "sine=frequency=440:duration=0.5", str(wav))
    assert detect_format(str(wav)) == "wav"


@needs_ffmpeg
@pytest.mark.parametrize("ext", ["mp3", "ogg", "flac"])
def test_audio_convert(tmp_path, ext):
    wav = tmp_path / "t.wav"
    _ff("-f", "lavfi", "-i", "sine=frequency=440:duration=0.5", str(wav))
    out = tmp_path / f"t.{ext}"
    core.convert_file(str(wav), str(out))
    assert out.stat().st_size > 0


@needs_ffmpeg
def test_video_thumbnail(tmp_path):
    mp4 = tmp_path / "v.mp4"
    _ff("-f", "lavfi", "-i", "color=c=blue:s=64x48:d=1", "-pix_fmt", "yuv420p", str(mp4))
    out = tmp_path / "thumb.png"
    core.convert_file(str(mp4), str(out))
    from PIL import Image
    assert Image.open(out).size == (64, 48)


@needs_soffice
def test_docx_pdf_roundtrip(tmp_path):
    docx_mod = pytest.importorskip("docx")
    d = docx_mod.Document()
    d.add_paragraph("Hello Atulya")
    src = tmp_path / "a.docx"
    d.save(src)
    pdf = tmp_path / "a.pdf"
    core.convert_file(str(src), str(pdf))
    assert pdf.read_bytes().startswith(b"%PDF")
    back = tmp_path / "b.docx"
    core.convert_file(str(pdf), str(back))
    assert "Hello Atulya" in " ".join(p.text for p in docx_mod.Document(str(back)).paragraphs)


def test_pdf_to_txt(tmp_path):
    fitz = pytest.importorskip("fitz")
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "Hello PDF")
    pdf = tmp_path / "a.pdf"
    doc.save(str(pdf))
    out = tmp_path / "a.txt"
    core.convert_file(str(pdf), str(out))
    assert "Hello PDF" in out.read_text()
