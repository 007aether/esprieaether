import os
import sys
import json
import glob as globmod

import click
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich.panel import Panel

from . import __version__
from .core import (
    convert_file, get_file_info, batch_convert,
    compute_file_hash, split_file, merge_files,
    extract_archive, validate_file,
    search_file, count_stats, show_schema,
    generate_random, diff_files, read_file, write_file, create_file,
)
from .utils import FORMATS, format_size, detect_format

console = Console()


@click.group(invoke_without_command=True)
@click.version_option(__version__)
@click.pass_context
def main(ctx):
    if ctx.invoked_subcommand is None:
        console.print(Panel("[bold cyan]Atulya All File Converter[/bold cyan]"))
        console.print("Cross-platform file reader, writer, creator, and converter.")
        console.print("Run [bold]atulya-convert --help[/bold] for commands.")
        console.print(f"Version {__version__} | 40+ formats supported")
        click.echo(main.get_help(ctx))


@main.command()
@click.argument("input", type=click.Path(exists=True))
@click.option("--encoding", default="utf-8", help="File encoding")
def read(input, encoding):
    data = read_file(input, encoding)
    fmt = data.get("format", "txt")
    if data.get("type") == "data":
        console.print(Syntax(json.dumps(data.get("data", data), indent=2, default=str), "json"))
    elif data.get("type") == "table":
        table = Table(title=f"{os.path.basename(input)} - {data.get('row_count', 0)} rows")
        for h in data.get("headers", []):
            table.add_column(h)
        for row in data.get("rows", [])[:50]:
            table.add_row(*[str(c)[:80] for c in row])
        console.print(table)
        if len(data.get("rows", [])) > 50:
            console.print(f"[dim]... and {len(data['rows']) - 50} more rows[/dim]")
    elif data.get("type") == "image":
        console.print(f"[bold]{os.path.basename(input)}[/bold] - {data.get('width')}x{data.get('height')} {data.get('mode')}")
    elif data.get("type") == "text" or fmt == "txt":
        console.print(data.get("content", ""))
    elif data.get("type") == "archive":
        table = Table(title=f"Contents of {os.path.basename(input)}")
        table.add_column("Name")
        table.add_column("Size")
        for e in data.get("entries", []):
            table.add_row(e["name"], format_size(e.get("size", 0)))
        console.print(table)
    else:
        console.print(json.dumps(data, indent=2, default=str))


@main.command()
@click.argument("input", type=click.Path(exists=True))
@click.argument("output", type=click.Path())
@click.option("-q", "--quality", default=90, type=int, help="Image quality (1-100)")
@click.option("--encoding", default="utf-8")
def write(input, output, quality, encoding):
    data = read_file(input, encoding)
    write_file(data, output, encoding)
    console.print(f"[green]Written:[/] {output}")


@main.command()
@click.argument("filepath", type=click.Path())
@click.option("--template", default=None, help=f"Template name: {', '.join(sorted(FORMATS.keys()))}")
@click.option("--lines", default=10, type=int, help="Lines/rows for generated data")
@click.option("--headers", default=None, help="Comma-separated column headers")
@click.option("--sheet", default="Sheet1", help="Sheet name (for xlsx)")
@click.option("--table", default="items", help="Table name (for sqlite)")
def create(filepath, template, lines, headers, sheet, table):
    kwargs = {"rows": lines, "sheet": sheet, "table": table}
    if headers:
        kwargs["headers"] = [h.strip() for h in headers.split(",")]
    result = create_file(filepath, template, **kwargs)
    console.print(f"[green]Created:[/] {filepath} [dim]({result})[/dim]")


@main.command()
@click.option("-i", "--input", required=True, type=click.Path(exists=True))
@click.option("-o", "--output", required=True, type=click.Path())
@click.option("-q", "--quality", default=90, type=int, help="Image quality (1-100)")
@click.option("--encoding", default="utf-8")
def convert(input, output, quality, encoding):
    result = convert_file(input, output, quality=quality, encoding=encoding)
    console.print(f"[green]Converted:[/] {input} -> {output} [dim]({result})[/dim]")


@main.command()
@click.argument("filepath", type=click.Path(exists=True))
@click.option("--hash", "hash_flag", is_flag=True, help="Show file hashes")
@click.option("--schema", "schema_flag", is_flag=True, help="Show file schema")
@click.option("--stats", "stats_flag", is_flag=True, help="Show file statistics")
@click.option("--all", "all_flag", is_flag=True, help="Show all info")
def info(filepath, hash_flag, schema_flag, stats_flag, all_flag):
    info_dict = get_file_info(filepath)

    if hash_flag or all_flag:
        info_dict["hashes"] = compute_file_hash(filepath)

    if schema_flag or all_flag:
        try:
            info_dict["schema"] = show_schema(filepath)
        except Exception as e:
            info_dict["schema"] = {"error": str(e)}

    if stats_flag or all_flag:
        try:
            info_dict["stats"] = count_stats(filepath)
        except Exception as e:
            info_dict["stats"] = {"error": str(e)}

    table = Table(title=f"File: {os.path.basename(filepath)}")
    table.add_column("Property", style="cyan")
    table.add_column("Value")
    for key, val in info_dict.items():
        if isinstance(val, dict):
            for sk, sv in val.items():
                table.add_row(f"  {sk}", str(sv))
        elif isinstance(val, list):
            table.add_row(key, ", ".join(str(v) for v in val))
        else:
            table.add_row(key, str(val))
    console.print(table)


@main.command()
@click.argument("filepath", type=click.Path(exists=True))
@click.option("--algo", default="md5,sha1,sha256", help="Comma-separated hash algorithms")
def hash(filepath, algo):
    algorithms = [a.strip() for a in algo.split(",")]
    result = compute_file_hash(filepath, algorithms)
    table = Table(title=f"Hashes: {os.path.basename(filepath)}")
    table.add_column("Algorithm", style="cyan")
    table.add_column("Hash")
    for algo, hash_val in result.items():
        table.add_row(algo.upper(), hash_val)
    console.print(table)


@main.command()
@click.argument("filepath", type=click.Path(exists=True))
@click.option("-o", "--output", default=None, help="Output directory for parts")
@click.option("--chunk", default=10, type=int, help="Chunk size in MB")
def split(filepath, output, chunk):
    parts = split_file(filepath, chunk, output)
    console.print(f"[green]Split {os.path.basename(filepath)} into {len(parts)} parts[/green]")
    for p in parts:
        size = format_size(os.path.getsize(p))
        console.print(f"  {os.path.basename(p)} [dim]({size})[/dim]")


@main.command()
@click.option("-i", "--input", "input_pattern", required=True, help="Input file pattern (e.g., *.part*)")
@click.option("-o", "--output", required=True, help="Output file path")
def merge(input_pattern, output):
    files = sorted(globmod.glob(input_pattern))
    if not files:
        console.print("[red]No files matched pattern[/red]")
        sys.exit(1)
    result = merge_files(files, output)
    console.print(f"[green]Merged {len(files)} files into[/] {output} [dim]({result})[/dim]")


@main.command()
@click.argument("filepath", type=click.Path(exists=True))
@click.option("-o", "--output-dir", default=None, help="Output directory")
def extract(filepath, output_dir):
    if output_dir is None:
        output_dir = os.path.splitext(os.path.basename(filepath))[0]
    extracted = extract_archive(filepath, output_dir)
    console.print(f"[green]Extracted {len(extracted)} items to[/] {output_dir}/")
    for item in sorted(extracted):
        console.print(f"  {item}")


@main.command()
@click.argument("filepath", type=click.Path(exists=True))
def validate(filepath):
    result = validate_file(filepath)
    if result["valid"]:
        console.print(f"[green]Valid[/] {result['format']} file")
    else:
        console.print(f"[red]Invalid[/] {result['format']} file")
        for issue in result["issues"]:
            console.print(f"  [red]x[/] {issue}")


@main.command()
@click.argument("filepath", type=click.Path(exists=True))
@click.argument("pattern")
@click.option("--encoding", default="utf-8")
@click.option("--context", default=0, type=int, help="Lines of context")
def search(filepath, pattern, encoding, context):
    results = search_file(filepath, pattern, encoding)
    if not results:
        console.print(f"[yellow]No matches for[/] '{pattern}'")
        return
    console.print(f"[green]Found {len(results)} matches[/] in {os.path.basename(filepath)}")
    for r in results[:100]:
        console.print(f"  [cyan]L{r['line']}:[/] {r['text']}")
    if len(results) > 100:
        console.print(f"[dim]... and {len(results) - 100} more matches[/dim]")


@main.command()
@click.argument("filepath", type=click.Path(exists=True))
def stats(filepath):
    result = count_stats(filepath)
    table = Table(title=f"Stats: {os.path.basename(filepath)}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value")
    for key, val in result.items():
        table.add_row(key.replace("_", " ").title(), str(val))
    console.print(table)


@main.command()
@click.argument("filepath", type=click.Path(exists=True))
def schema(filepath):
    result = show_schema(filepath)
    table = Table(title=f"Schema: {os.path.basename(filepath)}")
    table.add_column("Property", style="cyan")
    table.add_column("Value")
    for key, val in result.items():
        if isinstance(val, dict):
            for sk, sv in val.items():
                table.add_row(f"  {sk}", str(sv))
        elif isinstance(val, list):
            table.add_row(key, ", ".join(str(v) for v in val[:20]))
            if len(val) > 20:
                table.add_row("", f"... and {len(val)-20} more")
        else:
            table.add_row(key, str(val))
    console.print(table)


@main.command()
@click.argument("output", type=click.Path())
@click.option("--lines", default=10, type=int, help="Number of lines/rows")
def random(output, lines):
    result = generate_random(output, lines)
    console.print(f"[green]Generated:[/] {output} [dim]({result})[/dim]")


@main.command()
@click.argument("file_a", type=click.Path(exists=True))
@click.argument("file_b", type=click.Path(exists=True))
def diff(file_a, file_b):
    result = diff_files(file_a, file_b)
    if result["type"] == "text":
        if result["diffs"]:
            console.print(Syntax("\n".join(result["diff"]), "diff"))
        else:
            console.print("[green]Files are identical[/green]")
    else:
        console.print(f"Size A: {result['size_a']}, Size B: {result['size_b']}")
        console.print(f"Same size: {result['same_size']}, Identical: {result['identical']}")


@main.command()
@click.option("-i", "--input-dir", required=True, type=click.Path(exists=True))
@click.option("--pattern", default="*.*", help="File glob pattern")
@click.option("-o", "--output-dir", required=True, type=click.Path())
@click.option("--format", "output_format", required=True, help="Output format (extension)")
@click.option("-q", "--quality", default=90, type=int)
def batch(input_dir, pattern, output_dir, output_format, quality):
    os.makedirs(output_dir, exist_ok=True)
    from rich.progress import Progress
    import glob
    total = len(glob.glob(os.path.join(input_dir, pattern)))
    with Progress(console=console) as bar:
        task = bar.add_task("Converting", total=total)
        results = batch_convert(
            input_dir, pattern, output_dir, output_format, quality=quality,
            progress=lambda done, _total, name: bar.update(task, completed=done, description=name),
        )
    table = Table(title=f"Batch: {pattern} -> .{output_format}")
    table.add_column("File")
    table.add_column("Status")
    table.add_column("Result")
    for name, status, detail in results:
        style = "green" if status == "ok" else "red"
        table.add_row(name, status, str(detail), style=style)
    console.print(table)


@main.command()
@click.argument("filepath", type=click.Path(exists=True))
def detect(filepath):
    fmt = detect_format(filepath)
    from .utils import get_category
    cat = get_category(filepath)
    ext = os.path.splitext(filepath)[1]
    console.print(f"[bold]{os.path.basename(filepath)}[/bold]")
    console.print(f"  Extension: [cyan]{ext}[/cyan]" if ext else "  Extension: [yellow](none)[/yellow]")
    console.print(f"  Detected format: [cyan]{fmt}[/cyan]")
    console.print(f"  Category: [cyan]{cat}[/cyan]")
    console.print(f"  Size: {format_size(os.path.getsize(filepath))}")


@main.command()
@click.option("--host", default="127.0.0.1", help="Host address")
@click.option("--port", default=8080, type=int, help="Port number")
@click.option("--open", "open_browser", is_flag=True, help="Open browser automatically")
def serve(host, port, open_browser):
    from .server import serve as run_server
    if open_browser:
        import webbrowser
        webbrowser.open(f"http://{host}:{port}")
    run_server(host=host, port=port)


@main.command("list")
def list_formats():
    table = Table(title="Supported Formats (40+)")
    table.add_column("Format", style="cyan")
    table.add_column("Extensions")
    table.add_column("Category")
    for fmt, info in sorted(FORMATS.items()):
        table.add_row(fmt, ", ".join(info["ext"]), info["cat"])
    console.print(table)
    console.print("\n[dim]Reader/Writer/Creator/Converter — all in one[/dim]")


@main.command()
@click.option("--check", is_flag=True, help="Check for updates without downloading")
def update(check):
    """Check and install Over-The-Air (OTA) updates from GitHub."""
    from . import __version__
    from .updater import check_for_updates, download_and_apply_update

    console.print(f"[bold cyan]Checking for updates... (Current version: v{__version__})[/bold cyan]")
    info = check_for_updates(__version__)
    if not info:
        console.print("[green]You are running the latest version of Atulya File Converter.[/green]")
        return

    console.print(f"[bold green]New update available: {info['latest_version']}[/bold green]")
    if info.get("release_name"):
        console.print(f"Release: {info['release_name']}")
    if info.get("asset_name"):
        console.print(f"Asset: {info['asset_name']} ({format_size(info.get('asset_size', 0))})")

    if check:
        return

    if not info.get("download_url"):
        console.print(f"[yellow]No direct installer found for this platform. Please visit: {info['html_url']}[/yellow]")
        return

    if click.confirm("Do you want to download and install this update now?", default=True):
        with Progress() as bar:
            task = bar.add_task("Downloading update...", total=100)
            def update_progress(percent):
                bar.update(task, completed=percent)
            success, msg = download_and_apply_update(info["download_url"], info["asset_name"], callback=update_progress)
            if success:
                console.print(f"[bold green]{msg}[/bold green]")
            else:
                console.print(f"[bold red]{msg}[/bold red]")

