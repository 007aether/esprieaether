"""Converters that shell out to external tools (LibreOffice, ffmpeg)."""
import os
import shutil
import subprocess
import tempfile

AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".opus"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".avi"}
OFFICE_EXTENSIONS = {".docx", ".odt", ".rtf", ".doc"}


class ToolMissingError(RuntimeError):
    pass


def _find(*names):
    for name in names:
        path = shutil.which(name)
        if path:
            return path
    return None


def _run(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{os.path.basename(cmd[0])} failed: {proc.stderr.strip()[-500:]}")


def libreoffice_convert(input_path, output_path, infilter=None):
    """Convert a document with headless LibreOffice (docx<->pdf, odt->docx, ...)."""
    soffice = _find("soffice", "libreoffice")
    if not soffice:
        raise ToolMissingError("LibreOffice is required for document conversion (install it and ensure 'soffice' is on PATH)")
    target = os.path.splitext(output_path)[1].lstrip(".").lower()
    with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as profile:
        cmd = [soffice, f"-env:UserInstallation=file://{profile}", "--headless"]
        if infilter:
            cmd.append(f"--infilter={infilter}")
        cmd += ["--convert-to", target, "--outdir", tmp, input_path]
        _run(cmd)
        produced = os.path.join(tmp, os.path.splitext(os.path.basename(input_path))[0] + "." + target)
        if not os.path.exists(produced):
            raise RuntimeError("LibreOffice did not produce an output file")
        shutil.move(produced, output_path)


def pdf_to_docx(input_path, output_path):
    """Text-only PDF -> DOCX: one real paragraph per text block (layout is not preserved)."""
    try:
        import fitz
        import docx
    except ImportError:
        raise ToolMissingError("PDF to DOCX needs PyMuPDF and python-docx: pip install PyMuPDF python-docx")
    pdf = fitz.open(input_path)
    document = docx.Document()
    for number, page in enumerate(pdf):
        if number:
            document.add_page_break()
        for block in page.get_text("blocks"):
            text = block[4].strip() if block[6] == 0 else ""
            if text:
                document.add_paragraph(text.replace("\n", " "))
    pdf.close()
    document.save(output_path)


def convert_document(input_path, output_path):
    ext_in = os.path.splitext(input_path.lower())[1]
    ext_out = os.path.splitext(output_path.lower())[1]
    if ext_in == ".pdf" and ext_out == ".docx":
        pdf_to_docx(input_path, output_path)
    else:
        libreoffice_convert(input_path, output_path, "writer_pdf_import" if ext_in == ".pdf" else None)


def _ffmpeg():
    exe = _find("ffmpeg")
    if not exe:
        raise ToolMissingError("ffmpeg is required for audio/video conversion (install it and ensure it is on PATH)")
    return exe


def convert_audio(input_path, output_path, bitrate="192k"):
    cmd = [_ffmpeg(), "-y", "-i", input_path, "-vn"]
    if os.path.splitext(output_path.lower())[1] in (".mp3", ".ogg", ".m4a", ".aac", ".opus"):
        cmd += ["-b:a", bitrate]
    _run(cmd + [output_path])


def video_thumbnail(input_path, output_path, at_seconds=1.0):
    """Extract a single frame as an image. Falls back to the first frame for short clips."""
    ffmpeg = _ffmpeg()
    for t in (at_seconds, 0):
        _run([ffmpeg, "-y", "-ss", str(t), "-i", input_path, "-frames:v", "1", output_path])
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return
    raise RuntimeError("Could not extract a frame from the video")
