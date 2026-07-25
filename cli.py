#!/usr/bin/env python3
"""
STEGOSAURUS WRECKS - Command Line Interface
🦕 The most epic steg tool of all time 🦕

Usage:
    stegg encode -i image.png -t "secret message" -o output.png
    stegg decode -i encoded.png
    stegg analyze image.png
    stegg inject --help
"""

import json
import os
import sys
import time
import typer
from pathlib import Path
from typing import Optional, List, Tuple
from enum import Enum

import numpy as np

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.syntax import Syntax
from rich.text import Text
from rich.columns import Columns
from rich.live import Live
from rich.align import Align
from rich import box

from PIL import Image

# Import our modules
from img_core import (
    encode, decode, create_config, calculate_capacity, analyze_image,
    detect_encoding, CHANNEL_PRESETS, EncodingStrategy,
    dct_encode, dct_decode, dct_capacity, DCT_STRENGTHS,
    f5_encode, f5_decode, f5_capacity, f5_capacity_bytes,
    inject_text_chunk, inject_itxt_chunk, inject_private_chunk,
    read_png_chunks, extract_text_chunks, inject_metadata_pil,
)
from analysis_tools import execute_action, list_available_tools
try:
    from specter import (
        specter_lsb_encode, specter_lsb_decode,
        specter_dct_encode, specter_dct_decode,
        parse_pattern, pattern_from_password,
        SPECTER_DCT_REDUNDANCY, SPECTER_DCT_STRENGTH,
    )
except Exception:
    specter_lsb_encode = specter_lsb_decode = None  # type: ignore[assignment]
    specter_dct_encode = specter_dct_decode = None  # type: ignore[assignment]
    parse_pattern = pattern_from_password = None  # type: ignore[assignment]
    SPECTER_DCT_REDUNDANCY = 5
    SPECTER_DCT_STRENGTH = 50
try:
    from crypto import encrypt, decrypt, get_available_methods, crypto_status
except Exception:
    # Gracefully handle broken cryptography library (e.g., broken system install)
    encrypt = decrypt = None
    def get_available_methods(): return ["none", "xor"]
    def crypto_status(): return "⚠ crypto module unavailable (install cryptography package)"
from jailbreak_core import (
    generate_injection_filename, get_filename_template_names as get_template_names,
    get_jailbreak_template, get_jailbreak_names,
    compose_image_jailbreak, detect_full_injection_package,
)
from transforms_core import zalgo_text, leetspeak
from ascii_art import (
    BANNER, BANNER_SMALL, STEGOSAURUS_ASCII_SIMPLE, STEGOSAURUS_SMALL,
    STATUS, FOOTER, TAGLINES, section_header, channel_bar, COLORS
)
from matryoshka_core import (
    MatryoshkaConfig, encode_nested, decode_nested, capacity_for,
    plan_nesting, is_image_data, DecodeLayer, LayerReport,
)

# ---------------------------------------------------------------------------
# JSON output helpers (for --json mode — agent/subprocess consumption)
# ---------------------------------------------------------------------------


class _NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.bool_,)): return bool(obj)
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        return super().default(obj)


def _out_json(obj):
    """Emit a JSON result to stdout and exit cleanly."""
    print(json.dumps(obj, cls=_NumpyEncoder))
    raise typer.Exit(0)


def _try_decode_utf8(data: bytes) -> str | None:
    """Return UTF-8 decoded text, or None if binary."""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


# Initialize
console = Console()
app = typer.Typer(
    name="stegg",
    help="🦕 STEGOSAURUS WRECKS - Ultimate Steganography Suite",
    add_completion=False,
    rich_markup_mode="rich",
)


class ChannelPreset(str, Enum):
    """Channel preset options"""
    R = "R"
    G = "G"
    B = "B"
    A = "A"
    RG = "RG"
    RB = "RB"
    RA = "RA"
    GB = "GB"
    GA = "GA"
    BA = "BA"
    RGB = "RGB"
    RGA = "RGA"
    RBA = "RBA"
    GBA = "GBA"
    RGBA = "RGBA"


class Strategy(str, Enum):
    """Encoding strategy options"""
    interleaved = "interleaved"
    sequential = "sequential"
    spread = "spread"
    randomized = "randomized"


def print_banner(small: bool = False):
    """Print the epic banner"""
    if small:
        console.print(BANNER_SMALL)
    else:
        console.print(BANNER)
    console.print()


def print_stego():
    """Print the stegosaurus"""
    console.print(STEGOSAURUS_ASCII_SIMPLE)


def success(msg: str):
    console.print(f"{STATUS['success']} [green]{msg}[/green]")


def error(msg: str):
    console.print(f"{STATUS['error']} [red]{msg}[/red]")


def warning(msg: str):
    console.print(f"{STATUS['warning']} [yellow]{msg}[/yellow]")


def info(msg: str):
    console.print(f"{STATUS['info']} [cyan]{msg}[/cyan]")


# ============== MAIN COMMAND ==============

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    json_mode: bool = typer.Option(False, "--json", help="Output JSON to stdout (for agent/script consumption)"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output (suppress banner/spinners/footer)"),
):
    """
    🦕 STEGOSAURUS WRECKS - Ultimate Steganography Suite

    Hide data in images using LSB steganography with style.
    """
    ctx.ensure_object(dict)
    ctx.obj["json_mode"] = json_mode
    ctx.obj["quiet"] = quiet or json_mode  # --json implies --quiet
    if ctx.invoked_subcommand is None:
        print_banner()
        print_stego()
        console.print(f"\n[dim]Run [green]stegg --help[/green] for usage information[/dim]")
        console.print(FOOTER)


# ============== ENCODE COMMAND ==============

@app.command()
def encode_cmd(
    ctx: typer.Context,
    input_image: Path = typer.Option(..., "--input", "-i", help="Input carrier image"),
    output: Path = typer.Option(None, "--output", "-o", help="Output image path"),
    text: Optional[str] = typer.Option(None, "--text", "-t", help="Text to encode"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="File to encode"),
    channels: ChannelPreset = typer.Option(ChannelPreset.RGB, "--channels", "-c", help="Channel preset"),
    bits: int = typer.Option(1, "--bits", "-b", help="Bits per channel (1-8)", min=1, max=8),
    strategy: Strategy = typer.Option(Strategy.interleaved, "--strategy", "-s", help="Encoding strategy"),
    seed: Optional[int] = typer.Option(None, "--seed", help="Random seed (for randomized strategy)"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Encryption password"),
    no_compress: bool = typer.Option(False, "--no-compress", help="Disable compression"),
    inject_filename: bool = typer.Option(False, "--inject-name", "-j", help="Use injection filename"),
    template: Optional[str] = typer.Option(None, "--template", help="Jailbreak template to encode"),
):
    """
    🔐 Encode data into an image (v3.0 - with CRC32 checksum & auto-detection)

    Examples:
        stegg encode -i photo.png -t "secret message" -o hidden.png
        stegg encode -i photo.png -f secret.txt -c RGBA -b 2 -p mypassword
        stegg encode -i photo.png --template pliny_classic -j
        stegg encode -i photo.png -t "spread out" -s spread
        stegg encode -i photo.png -t "random order" -s randomized --seed 12345
    """
    json_mode = ctx.obj.get("json_mode", False)
    quiet = ctx.obj.get("quiet", False)

    if not quiet:
        print_banner(small=True)

    # Validate input
    if not input_image.exists():
        error(f"Input image not found: {input_image}")
        raise typer.Exit(1)

    if not text and not file and not template:
        error("Must provide --text, --file, or --template")
        raise typer.Exit(1)

    # Load payload
    if template:
        payload = get_jailbreak_template(template).encode('utf-8')
    elif file:
        if not file.exists():
            error(f"File not found: {file}")
            raise typer.Exit(1)
        payload = file.read_bytes()
    else:
        payload = text.encode('utf-8')

    # Generate output filename
    if output is None:
        if inject_filename:
            output = Path(generate_injection_filename("chatgpt_decoder", channels.value))
        else:
            output = Path(f"steg_{input_image.stem}.png")

    # Load image
    try:
        image = Image.open(input_image)
    except Exception as e:
        error(f"Failed to load image: {e}")
        raise typer.Exit(1)

    # Create config
    config = create_config(
        channels=channels.value,
        bits=bits,
        compress=not no_compress,
        strategy=strategy.value,
        seed=seed,
    )

    # Check capacity
    capacity = calculate_capacity(image, config)
    if len(payload) > capacity['usable_bytes']:
        error(f"Payload too large! {len(payload):,} bytes > {capacity['usable_bytes']:,} available")
        raise typer.Exit(1)

    if not quiet and not json_mode:
        info(f"Loaded image: [cyan]{input_image}[/cyan] ({image.width}x{image.height})")
        if template:
            info(f"Using template: [cyan]{template}[/cyan]")
        elif file:
            info(f"Loaded file: [cyan]{file}[/cyan] ({len(payload):,} bytes)")
        console.print(Panel(
            f"[cyan]Capacity:[/cyan] {capacity['human']}\n"
            f"[cyan]Channels:[/cyan] {channel_bar(channels.value)}\n"
            f"[cyan]Bits/Channel:[/cyan] {bits}\n"
            f"[cyan]Strategy:[/cyan] {strategy.value}\n"
            f"[cyan]Payload:[/cyan] {len(payload):,} bytes",
            title="[green]Configuration[/green]",
            border_style="green",
        ))

    # Encrypt if password provided
    encrypted = False
    if password:
        if json_mode:
            payload = encrypt(payload, password)
            encrypted = True
        else:
            with console.status("[cyan]Encrypting payload...[/cyan]", spinner="dots"):
                payload = encrypt(payload, password)
            success("Payload encrypted")
            encrypted = True

    # Encode
    try:
        if json_mode:
            result = encode(image, payload, config, str(output))
        else:
            with Progress(
                SpinnerColumn(style="green"),
                TextColumn("[green]Encoding...[/green]"),
                BarColumn(complete_style="green", finished_style="bright_green"),
                TaskProgressColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("Encoding", total=100)
                for i in range(0, 100, 10):
                    progress.update(task, completed=i)
                    time.sleep(0.05)
                result = encode(image, payload, config, str(output))
                progress.update(task, completed=100)
    except Exception as e:
        error(f"Encoding failed: {e}")
        raise typer.Exit(1)

    # Output
    out_size = output.stat().st_size

    if json_mode:
        _out_json({
            "status": "ok",
            "output": str(output),
            "output_bytes": out_size,
            "payload_bytes": len(payload),
            "capacity": capacity["human"],
            "capacity_bytes": capacity["usable_bytes"],
            "encrypted": encrypted,
            "config": {
                "channels": channels.value,
                "bits_per_channel": bits,
                "strategy": strategy.value,
                "compress": not no_compress,
            },
            "carrier": {"width": image.width, "height": image.height, "mode": image.mode},
        })

    console.print()
    success(f"Data encoded successfully!")

    result_panel = Panel(
        f"[green]Output:[/green] {output}\n"
        f"[green]Size:[/green] {out_size:,} bytes\n"
        f"[green]Payload:[/green] {len(payload):,} bytes\n"
        f"[green]Encrypted:[/green] {'Yes' if password else 'No'}",
        title=f"{STATUS['dino']} [green]Encoding Complete[/green]",
        border_style="green",
        box=box.DOUBLE,
    )
    console.print(result_panel)

    if not quiet:
        console.print(f"\n{FOOTER}")


# ============== DECODE COMMAND ==============

@app.command()
def decode_cmd(
    ctx: typer.Context,
    input_image: Path = typer.Option(..., "--input", "-i", help="Encoded image to decode"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file for binary data"),
    auto_detect: bool = typer.Option(True, "--auto/--no-auto", "-a", help="Auto-detect encoding config from header"),
    channels: ChannelPreset = typer.Option(ChannelPreset.RGB, "--channels", "-c", help="Channel preset (if not auto)"),
    bits: int = typer.Option(1, "--bits", "-b", help="Bits per channel (if not auto)", min=1, max=8),
    strategy: Strategy = typer.Option(Strategy.interleaved, "--strategy", "-s", help="Strategy (if not auto)"),
    seed: Optional[int] = typer.Option(None, "--seed", help="Random seed (if not auto)"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Decryption password"),
    no_verify: bool = typer.Option(False, "--no-verify", help="Skip CRC32 checksum verification"),
    raw: bool = typer.Option(False, "--raw", help="Output raw bytes (hex)"),
):
    """
    🔓 Decode data from an image (v3.0 - with auto-detection & checksum verification)

    Examples:
        stegg decode -i hidden.png                     # Auto-detect config
        stegg decode -i hidden.png --no-auto -c RGBA   # Manual config
        stegg decode -i hidden.png -p mypassword       # With decryption
        stegg decode -i hidden.png -o extracted.bin    # Save to file
    """
    json_mode = ctx.obj.get("json_mode", False)
    quiet = ctx.obj.get("quiet", False)

    if not quiet:
        print_banner(small=True)

    if not input_image.exists():
        error(f"Image not found: {input_image}")
        raise typer.Exit(1)

    # Load image
    try:
        image = Image.open(input_image)
    except Exception as e:
        error(f"Failed to load image: {e}")
        raise typer.Exit(1)

    if not json_mode:
        info(f"Loaded image: [cyan]{input_image}[/cyan] ({image.width}x{image.height})")

    # Auto-detect or use manual config
    config = None
    detected = False
    detection = None
    if auto_detect:
        detection = detect_encoding(image)
        if detection:
            detected = True
            if not quiet and not json_mode:
                success(f"Detected STEG v3 encoding!")
                console.print(Panel(
                    f"[cyan]Channels:[/cyan] {', '.join(detection['config']['channels'])}\n"
                    f"[cyan]Bits/Channel:[/cyan] {detection['config']['bits_per_channel']}\n"
                    f"[cyan]Strategy:[/cyan] {detection['config']['strategy']}\n"
                    f"[cyan]Compressed:[/cyan] {detection['config']['compression']}\n"
                    f"[cyan]Payload Size:[/cyan] {detection['payload_length']:,} bytes\n"
                    f"[cyan]Original Size:[/cyan] {detection['original_length']:,} bytes",
                    title="[green]Detected Configuration[/green]",
                    border_style="green",
                ))
            config = None
        else:
            if not json_mode:
                warning("No STEG header detected, using manual config")
            config = create_config(
                channels=channels.value, bits=bits,
                strategy=strategy.value, seed=seed,
            )
    else:
        config = create_config(
            channels=channels.value, bits=bits,
            strategy=strategy.value, seed=seed,
        )
        if not quiet and not json_mode:
            console.print(Panel(
                f"[cyan]Channels:[/cyan] {channel_bar(channels.value)}\n"
                f"[cyan]Bits/Channel:[/cyan] {bits}\n"
                f"[cyan]Strategy:[/cyan] {strategy.value}",
                title="[cyan]Manual Configuration[/cyan]",
                border_style="cyan",
            ))

    # Decode
    try:
        if json_mode:
            data = decode(image, config, verify_checksum=not no_verify)
        else:
            with console.status("[cyan]Decoding...[/cyan]", spinner="dots"):
                data = decode(image, config, verify_checksum=not no_verify)
    except Exception as e:
        error(f"Decoding failed: {e}")
        raise typer.Exit(1)

    # Decrypt if password
    if password:
        try:
            if json_mode:
                data = decrypt(data, password)
            else:
                with console.status("[cyan]Decrypting...[/cyan]", spinner="dots"):
                    data = decrypt(data, password)
                success("Data decrypted")
        except Exception as e:
            error(f"Decryption failed: {e}")
            raise typer.Exit(1)

    # JSON output
    if json_mode:
        result = {
            "status": "ok",
            "payload_bytes": len(data),
            "auto_detected": detected,
        }
        if detection:
            result["detected_config"] = {
                "channels": detection["config"]["channels"],
                "bits_per_channel": detection["config"]["bits_per_channel"],
                "strategy": detection["config"]["strategy"],
                "compression": detection["config"]["compression"],
            }
        if output:
            output.write_bytes(data)
            result["output"] = str(output)
        if raw:
            result["hex"] = data.hex()
        text = _try_decode_utf8(data)
        if text is not None:
            result["text"] = text
        else:
            result["hex_preview"] = data[:512].hex()
        _out_json(result)

    success(f"Extracted {len(data):,} bytes")

    # Output
    if output:
        output.write_bytes(data)
        success(f"Saved to: {output}")
    elif raw:
        console.print(Panel(
            data.hex(),
            title="[cyan]Raw Data (hex)[/cyan]",
            border_style="cyan",
        ))
    else:
        try:
            text_data = data.decode('utf-8')
            console.print(Panel(
                text_data,
                title=f"{STATUS['decode']} [cyan]Decoded Message[/cyan]",
                border_style="cyan",
                box=box.DOUBLE,
            ))
        except UnicodeDecodeError:
            warning("Data is not valid UTF-8, showing hex preview:")
            console.print(Panel(
                data[:500].hex() + ("..." if len(data) > 500 else ""),
                title="[yellow]Binary Data (hex preview)[/yellow]",
                border_style="yellow",
            ))

    if not quiet:
        console.print(f"\n{FOOTER}")


# ============== ANALYZE COMMAND ==============

@app.command()
def analyze(
    ctx: typer.Context,
    input_image: Path = typer.Argument(..., help="Image to analyze"),
    full: bool = typer.Option(False, "--full", "-f", help="Full analysis with all channels"),
    recursive: bool = typer.Option(False, "--recursive", "-r", "--matryoshka",
                                   help="Recursively scan for Matryoshka nested stego"),
):
    """
    🔍 Analyze an image for steganographic content

    Examples:
        stegg analyze photo.png
        stegg analyze suspicious.png --full
    """
    json_mode = ctx.obj.get("json_mode", False)
    quiet = ctx.obj.get("quiet", False)

    if not quiet and not json_mode:
        print_banner(small=True)

    if not input_image.exists():
        error(f"Image not found: {input_image}")
        raise typer.Exit(1)

    try:
        image = Image.open(input_image)
    except Exception as e:
        error(f"Failed to load image: {e}")
        raise typer.Exit(1)

    with console.status("[cyan]Analyzing image...[/cyan]", spinner="dots"):
        analysis = analyze_image(image)

    # JSON output
    if json_mode:
        channels_json = {}
        max_ind = 0.0
        for ch, d in analysis["channels"].items():
            lsb = d["lsb_ratio"]
            ind = d.get("chi_square_indicator", 0.0)
            max_ind = max(max_ind, ind)
            channels_json[ch] = {
                "mean": round(d["mean"], 2),
                "std": round(d["std"], 2),
                "lsb_zeros_pct": round(lsb["zeros"] * 100, 1),
                "lsb_ones_pct": round(lsb["ones"] * 100, 1),
                "chi_sq_indicator": round(ind, 4),
                "anomaly": "HIGH" if ind > 0.3 else ("slight" if ind > 0.1 else "normal"),
            }
        verdict = ("HIGH PROBABILITY" if max_ind > 0.3
                   else "Possible" if max_ind > 0.1
                   else "No indicators")
        _out_json({
            "status": "ok",
            "dimensions": analysis["dimensions"],
            "mode": analysis["mode"],
            "pixels": analysis["total_pixels"],
            "channels": channels_json,
            "capacity": analysis["capacity_by_config"],
            "verdict": verdict,
        })

    # Image info
    info_table = Table(show_header=False, box=box.SIMPLE)
    info_table.add_column("Property", style="cyan")
    info_table.add_column("Value", style="white")
    info_table.add_row("File", str(input_image))
    info_table.add_row("Dimensions", f"{analysis['dimensions']['width']} x {analysis['dimensions']['height']}")
    info_table.add_row("Total Pixels", f"{analysis['total_pixels']:,}")
    info_table.add_row("Mode", analysis['mode'])
    info_table.add_row("Format", str(analysis['format']))

    console.print(Panel(info_table, title="[green]Image Information[/green]", border_style="green"))

    # Channel analysis
    channel_table = Table(box=box.ROUNDED)
    channel_table.add_column("Channel", style="bold")
    channel_table.add_column("Mean", justify="right")
    channel_table.add_column("Std Dev", justify="right")
    channel_table.add_column("LSB 0s", justify="right")
    channel_table.add_column("LSB 1s", justify="right")
    channel_table.add_column("Anomaly", justify="center")

    for ch_name, ch_data in analysis['channels'].items():
        lsb = ch_data['lsb_ratio']
        indicator = ch_data['chi_square_indicator']

        if indicator < 0.1:
            anomaly = "[green]✓ Normal[/green]"
        elif indicator < 0.3:
            anomaly = "[yellow]⚠ Slight[/yellow]"
        else:
            anomaly = "[red]⚠ HIGH[/red]"

        color = {"R": "red", "G": "green", "B": "blue", "A": "white"}[ch_name]
        channel_table.add_row(
            f"[{color}]█ {ch_name}[/{color}]",
            f"{ch_data['mean']:.1f}",
            f"{ch_data['std']:.1f}",
            f"{lsb['zeros']*100:.1f}%",
            f"{lsb['ones']*100:.1f}%",
            anomaly,
        )

    console.print(Panel(channel_table, title="[cyan]Channel Analysis[/cyan]", border_style="cyan"))

    # Capacity table
    cap_table = Table(box=box.SIMPLE)
    cap_table.add_column("Config", style="cyan")
    cap_table.add_column("Capacity", style="green", justify="right")

    for config_name, capacity in analysis['capacity_by_config'].items():
        cap_table.add_row(config_name, capacity)

    console.print(Panel(cap_table, title="[magenta]Capacity Estimates[/magenta]", border_style="magenta"))

    # Verdict
    max_indicator = max(
        ch['chi_square_indicator']
        for ch in analysis['channels'].values()
    )

    if max_indicator > 0.3:
        verdict = Panel(
            "[red bold]⚠ HIGH PROBABILITY OF HIDDEN DATA ⚠[/red bold]\n\n"
            "LSB distribution shows significant anomaly.\n"
            "This image likely contains steganographic content.",
            title="[red]Verdict[/red]",
            border_style="red",
            box=box.DOUBLE,
        )
    elif max_indicator > 0.1:
        verdict = Panel(
            "[yellow]⚠ Possible hidden data[/yellow]\n\n"
            "LSB distribution shows slight anomaly.\n"
            "Could be natural variation or light steganography.",
            title="[yellow]Verdict[/yellow]",
            border_style="yellow",
        )
    else:
        verdict = Panel(
            "[green]✓ No obvious steganographic indicators[/green]\n\n"
            "LSB distribution appears natural.\n"
            "Does not mean data isn't hidden - could use encryption or advanced techniques.",
            title="[green]Verdict[/green]",
            border_style="green",
        )

    console.print(verdict)

    # Recursive / Matryoshka scan
    if recursive:
        console.print()
        _run_recursive_scan(input_image)

    console.print(f"\n{FOOTER}")


def _run_recursive_scan(image_path: Path):
    """Run smart_scan_recursive on an image and print results."""
    try:
        from analysis_tools import smart_scan_recursive
    except ImportError:
        warning("analysis_tools.smart_scan_recursive not available")
        return

    with console.status("[magenta]🪆 Recursive Matryoshka scan...[/magenta]", spinner="dots"):
        result = smart_scan_recursive(image_path.read_bytes())

    if result.get("error"):
        warning(f"Recursive scan failed: {result['error']}")
        return

    if not result.get("is_matryoshka"):
        info("🪆 No nested stego layers detected")
        return

    depth = result["nested_depth"]
    count = result["layers_found"]

    table = Table(
        title=f"🪆 Matryoshka Scan — {count} layers, max depth {depth}",
        box=box.ROUNDED,
    )
    table.add_column("Depth", style="cyan", justify="right")
    table.add_column("Type", style="magenta")
    table.add_column("Size", style="green", justify="right")
    table.add_column("Preview", style="white")

    for layer in result["layers"]:
        preview = layer["preview"][:80] if layer["preview"] else ""
        table.add_row(
            str(layer["depth"]),
            layer["type"],
            f"{layer['data_size']:,} B" if layer["data_size"] else "",
            preview,
        )

    console.print(table)


# ============== INJECT COMMAND ==============

inject_app = typer.Typer(help="💉 Prompt injection tools")
app.add_typer(inject_app, name="inject")


@inject_app.command("filename")
def inject_filename(
    template: str = typer.Option("chatgpt_decoder", "--template", "-t", help="Filename template"),
    channels: str = typer.Option("RGB", "--channels", "-c", help="Channel string"),
    count: int = typer.Option(1, "--count", "-n", help="Number of filenames to generate"),
):
    """
    Generate prompt injection filenames

    Templates: chatgpt_decoder, claude_decoder, gemini_decoder, universal_decoder,
               system_override, roleplay_trigger, dev_mode, subtle, custom
    """
    print_banner(small=True)
    console.print(section_header("Injection Filename Generator"))
    console.print()

    for i in range(count):
        filename = generate_injection_filename(template, channels)
        console.print(f"  [green]{filename}[/green]")

    console.print(f"\n{FOOTER}")


@inject_app.command("templates")
def inject_templates():
    """List available jailbreak templates"""
    print_banner(small=True)
    console.print(section_header("Jailbreak Templates"))
    console.print()

    for name in get_jailbreak_names():
        template = get_jailbreak_template(name)
        preview = template[:80].replace('\n', ' ') + "..." if len(template) > 80 else template.replace('\n', ' ')
        console.print(f"  [cyan]{name}[/cyan]")
        console.print(f"    [dim]{preview}[/dim]")
        console.print()

    console.print(f"\n{FOOTER}")


@inject_app.command("show")
def inject_show(template: str = typer.Argument(..., help="Template name")):
    """Show full content of a jailbreak template"""
    print_banner(small=True)

    content = get_jailbreak_template(template)
    if content:
        console.print(Panel(
            content,
            title=f"[cyan]{template}[/cyan]",
            border_style="cyan",
        ))
    else:
        error(f"Template not found: {template}")

    console.print(f"\n{FOOTER}")


@inject_app.command("compose")
def inject_compose(
    carrier: Path = typer.Option(..., "--carrier", "-i", help="Carrier image path"),
    template: str = typer.Option("pliny_classic", "--template", "-t", help="Jailbreak template"),
    channels: str = typer.Option("RGB", "--channels", "-c", help="LSB channel preset"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output PNG path"),
    filename_template: str = typer.Option("chatgpt_decoder", "--filename-template", help="Injection filename template"),
    encrypt: bool = typer.Option(False, "--encrypt", help="AES-256-GCM encrypt the payload"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Encryption password"),
):
    """Compose a full multi-vector jailbreak package (LSB + metadata + filename)"""
    print_banner(small=True)
    console.print(section_header("Jailbreak Compose"))
    console.print()

    from PIL import Image as _Image

    img = _Image.open(carrier)
    payload = compose_image_jailbreak(
        template, img,
        channels=channels,
        filename_template=filename_template,
        encrypt=encrypt,
        password=password,
    )

    out_path = output or Path(payload.filename)
    out_path.write_bytes(payload.image_bytes)

    success(f"Wrote stego image: [cyan]{out_path}[/cyan]")
    info(f"Filename template: [cyan]{payload.filename}[/cyan]")
    info(f"Technique: [cyan]{payload.technique_summary}[/cyan]")
    console.print(f"\n{FOOTER}")


@inject_app.command("detect")
def inject_detect(
    target: Path = typer.Option(..., "--target", "-i", help="Image or text file to scan"),
    full: bool = typer.Option(False, "--full", help="Full-spectrum scan across all vectors"),
):
    """Scan a file for jailbreak / prompt-injection indicators"""
    print_banner(small=True)
    console.print(section_header("Jailbreak Detect"))
    console.print()

    suffix = target.suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".bmp", ".gif"}:
        result = detect_full_injection_package(image_path=str(target))
    else:
        result = detect_full_injection_package(text_path=str(target))

    severity = result.get("severity", "clean")
    color = {"clean": "green", "low": "yellow", "medium": "orange3", "high": "red"}.get(severity, "white")
    console.print(f"  Severity: [{color}]{severity.upper()}[/{color}]")
    console.print(f"  Detected: {result.get('detected')}")
    console.print(f"  Hits: {result.get('hit_count', 0)}")
    console.print(f"  Techniques: {', '.join(result.get('techniques', [])) or '(none)'}")

    if full:
        import json as _json
        console.print("\n[dim]Vectors:[/dim]")
        console.print(_json.dumps(result.get("vectors", {}), indent=2, default=str))

    console.print(f"\n{FOOTER}")


@inject_app.command("zalgo")
def inject_zalgo(
    text: str = typer.Argument(..., help="Text to convert"),
    intensity: int = typer.Option(3, "--intensity", "-i", help="Zalgo intensity (1-5)"),
):
    """Convert text to Zalgo (glitchy) text"""
    result = zalgo_text(text, intensity)
    console.print(Panel(result, title="[magenta]Zalgo Text[/magenta]", border_style="magenta"))


@inject_app.command("leet")
def inject_leet(
    text: str = typer.Argument(..., help="Text to convert"),
    intensity: int = typer.Option(2, "--intensity", "-i", help="Leet intensity (1-3)"),
):
    """Convert text to leetspeak"""
    result = leetspeak(text, intensity)
    console.print(Panel(result, title="[green]Leetspeak[/green]", border_style="green"))


@inject_app.command("chunk")
def inject_chunk(
    ctx: typer.Context,
    input_image: Path = typer.Option(..., "--input", "-i", help="Input PNG image"),
    output: Path = typer.Option(..., "--output", "-o", help="Output PNG path"),
    chunk_type: str = typer.Option("tEXt", "--type", help="Chunk type: tEXt, zTXt, iTXt, or a 4-char private type"),
    keyword: str = typer.Option("Comment", "--keyword", "-k", help="Chunk keyword"),
    text: str = typer.Option(..., "--text", "-t", help="Text to inject"),
    compressed: bool = typer.Option(False, "--compressed", help="Use zTXt (compressed)"),
):
    """💉 Inject a PNG text or private chunk."""
    json_mode = ctx.obj.get("json_mode", False)

    p = Path(input_image)
    if not p.exists():
        error(f"Image not found: {p}")
        raise typer.Exit(1)
    raw = p.read_bytes()

    ct = chunk_type
    if ct == "iTXt":
        modified = inject_itxt_chunk(raw, keyword, text)
    elif len(ct) == 4 and ct not in ("tEXt", "zTXt", "iTXt"):
        modified = inject_private_chunk(raw, ct, text.encode("utf-8"))
    else:
        modified = inject_text_chunk(raw, keyword, text, compressed=compressed)

    Path(output).write_bytes(modified)

    if json_mode:
        _out_json({"status": "ok", "output": str(output), "chunk_type": ct, "keyword": keyword, "bytes": len(text)})

    success(f"Injected {len(text)} bytes as {ct} chunk → {output}")


@inject_app.command("exif")
def inject_exif(
    ctx: typer.Context,
    input_image: Path = typer.Option(..., "--input", "-i", help="Input image"),
    output: Path = typer.Option(..., "--output", "-o", help="Output image path"),
    comment: str = typer.Option("", "--comment", help="Comment field"),
    author: str = typer.Option("", "--author", help="Author field"),
    description: str = typer.Option("", "--description", help="Description field"),
    title: str = typer.Option("", "--title", help="Title field"),
    custom_fields: str = typer.Option("", "--custom-fields", help="JSON object of additional key/value pairs"),
):
    """💉 Inject EXIF/tEXt metadata into an image via PIL PngInfo."""
    json_mode = ctx.obj.get("json_mode", False)

    p = Path(input_image)
    if not p.exists():
        error(f"Image not found: {p}")
        raise typer.Exit(1)

    meta: dict[str, str] = {}
    if comment: meta["Comment"] = comment
    if author: meta["Author"] = author
    if description: meta["Description"] = description
    if title: meta["Title"] = title
    if custom_fields:
        import json as _json
        try:
            meta.update(_json.loads(custom_fields))
        except _json.JSONDecodeError:
            error("--custom-fields must be valid JSON")
            raise typer.Exit(1)

    if not meta:
        error("Provide at least one metadata field")
        raise typer.Exit(1)

    image = Image.open(p)
    _, png_bytes = inject_metadata_pil(image, meta)
    Path(output).write_bytes(png_bytes)

    if json_mode:
        _out_json({"status": "ok", "output": str(output), "fields": list(meta.keys())})

    success(f"Injected {len(meta)} metadata field(s) → {output}")


# ============== DCT COMMANDS ==============

class DctRobustness(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


dct_app = typer.Typer(help="🎛  DCT steganography: frequency-domain (JPEG-survivable)")
app.add_typer(dct_app, name="dct")


@dct_app.command("encode")
def dct_encode_cmd(
    ctx: typer.Context,
    input_image: Path = typer.Option(..., "--input", "-i", help="Input carrier image"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output PNG path"),
    text: Optional[str] = typer.Option(None, "--text", "-t", help="Text to encode"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="File to encode"),
    robustness: DctRobustness = typer.Option(DctRobustness.medium, "--robustness", "-r", help="low / medium / high"),
    block_size: int = typer.Option(8, "--block-size", help="DCT block size (default 8)"),
):
    """🎛  Embed data via DCT (survives JPEG-style recompression at medium/high)."""
    json_mode = ctx.obj.get("json_mode", False)
    quiet = ctx.obj.get("quiet", False)

    if not quiet and not json_mode:
        print_banner(small=True)
    if not input_image.exists():
        error(f"Input image not found: {input_image}")
        raise typer.Exit(1)
    if not text and not file:
        error("Must provide --text or --file")
        raise typer.Exit(1)

    payload = file.read_bytes() if file else text.encode("utf-8")
    if output is None:
        output = Path(f"steg_dct_{input_image.stem}.png")

    try:
        image = Image.open(input_image)
    except Exception as e:
        error(f"Failed to load image: {e}")
        raise typer.Exit(1)

    cap = dct_capacity(image, block_size=block_size)
    if not quiet and not json_mode:
        console.print(Panel(
            f"[cyan]Capacity:[/cyan] {cap['human']}\n"
            f"[cyan]Block size:[/cyan] {block_size}\n"
            f"[cyan]Robustness:[/cyan] {robustness.value} (strength={DCT_STRENGTHS[robustness.value]})\n"
            f"[cyan]Payload:[/cyan] {len(payload):,} bytes",
            title="[green]DCT Configuration[/green]",
            border_style="green",
        ))

    if len(payload) > cap["usable_bytes"]:
        error(f"Payload too large! {len(payload):,} bytes > {cap['usable_bytes']:,} available")
        raise typer.Exit(1)

    try:
        dct_encode(image, payload, robustness=robustness.value, block_size=block_size, output_path=str(output))
    except Exception as e:
        error(f"DCT encoding failed: {e}")
        raise typer.Exit(1)

    if json_mode:
        _out_json({
            "status": "ok",
            "output": str(output),
            "output_bytes": output.stat().st_size,
            "payload_bytes": len(payload),
            "capacity": cap["human"],
            "capacity_bytes": cap["usable_bytes"],
            "config": {"method": "DCT", "robustness": robustness.value, "block_size": block_size},
        })

    success(f"DCT-encoded {len(payload):,} bytes → {output}")
    if not quiet:
        console.print(f"\n{FOOTER}")


@dct_app.command("decode")
def dct_decode_cmd(
    ctx: typer.Context,
    input_image: Path = typer.Option(..., "--input", "-i", help="DCT-encoded image"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Write recovered bytes here"),
    block_size: int = typer.Option(8, "--block-size", help="DCT block size (default 8)"),
    raw: bool = typer.Option(False, "--raw", help="Output raw bytes (hex)"),
):
    """🔎 Recover a payload previously hidden with `stegg dct encode`."""
    json_mode = ctx.obj.get("json_mode", False)
    quiet = ctx.obj.get("quiet", False)

    if not quiet and not json_mode:
        print_banner(small=True)
    if not input_image.exists():
        error(f"Image not found: {input_image}")
        raise typer.Exit(1)

    try:
        image = Image.open(input_image)
    except Exception as e:
        error(f"Failed to load image: {e}")
        raise typer.Exit(1)

    try:
        data = dct_decode(image, block_size=block_size)
    except Exception as e:
        error(f"DCT decoding failed: {e}")
        raise typer.Exit(1)

    if json_mode:
        result = {"status": "ok", "payload_bytes": len(data)}
        if output:
            output.write_bytes(data)
            result["output"] = str(output)
        if raw:
            result["hex"] = data.hex()
        text = _try_decode_utf8(data)
        if text is not None:
            result["text"] = text
        else:
            result["hex_preview"] = data[:512].hex()
        _out_json(result)

    success(f"Extracted {len(data):,} bytes via DCT")

    if output:
        output.write_bytes(data)
        success(f"Saved to: {output}")
    elif raw:
        console.print(Panel(data.hex(), title="[cyan]Raw Data (hex)[/cyan]", border_style="cyan"))
    else:
        try:
            console.print(Panel(data.decode("utf-8"), title=f"{STATUS['decode']} [cyan]Decoded Message[/cyan]",
                                border_style="cyan", box=box.DOUBLE))
        except UnicodeDecodeError:
            warning("Data is not valid UTF-8, showing hex preview:")
            console.print(Panel(data[:500].hex() + ("..." if len(data) > 500 else ""),
                                title="[yellow]Binary Data (hex preview)[/yellow]", border_style="yellow"))

    if not quiet:
        console.print(f"\n{FOOTER}")


@dct_app.command("capacity")
def dct_capacity_cmd(
    input_image: Path = typer.Option(..., "--input", "-i", help="Image to measure"),
    block_size: int = typer.Option(8, "--block-size", help="DCT block size (default 8)"),
):
    """📏 Report how many payload bytes fit under DCT."""
    if not input_image.exists():
        error(f"Image not found: {input_image}")
        raise typer.Exit(1)
    image = Image.open(input_image)
    cap = dct_capacity(image, block_size=block_size)
    table = Table(show_header=False, box=box.SIMPLE)
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    for k, v in cap.items():
        table.add_row(k, str(v))
    console.print(Panel(table, title="[cyan]DCT capacity[/cyan]", border_style="cyan"))


# ============== DCT: F5 COMMANDS ==============

_JPEG_MAGIC = b"\xff\xd8\xff"

f5_app = typer.Typer(help="🎛  F5: JPEG DCT coefficient steganography (Westfeld 2001)")
dct_app.add_typer(f5_app, name="f5")


def _check_jpeg(path: Path) -> bytes:
    """Read *path*, verify it starts with JPEG magic, return the bytes."""
    if not path.exists():
        error(f"Input file not found: {path}")
        raise typer.Exit(1)
    data = path.read_bytes()
    if data[:3] != _JPEG_MAGIC:
        error(f"Not a JPEG file (magic bytes missing): {path}")
        raise typer.Exit(1)
    return data


@f5_app.command("encode")
def f5_encode_cmd(
    ctx: typer.Context,
    input_image: Path = typer.Option(..., "--input", "-i", help="Input JPEG carrier image"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output JPEG path"),
    text: Optional[str] = typer.Option(None, "--text", "-t", help="Text to encode"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="File to encode"),
    password: str = typer.Option(..., "--password", "-p", help="Password for the F5 keystream"),
):
    """🎛  Embed data into JPEG DCT coefficients via the F5 algorithm."""
    json_mode = ctx.obj.get("json_mode", False)
    quiet = ctx.obj.get("quiet", False)

    if not quiet and not json_mode:
        print_banner(small=True)
    if not text and not file:
        error("Must provide --text or --file")
        raise typer.Exit(1)

    payload = file.read_bytes() if file else text.encode("utf-8")
    jpeg_bytes = _check_jpeg(input_image)

    if output is None:
        output = Path(f"steg_f5_{input_image.stem}.jpg")

    cap = f5_capacity_bytes(jpeg_bytes)
    if not quiet and not json_mode:
        info = f5_capacity(jpeg_bytes)
        console.print(Panel(
            f"[cyan]Capacity:[/cyan] {cap:,} bytes\n"
            f"[cyan]Coefficients:[/cyan] {info['coeff_total']:,} total\n"
            f"[cyan]Payload:[/cyan] {len(payload):,} bytes",
            title="[green]F5 Configuration[/green]",
            border_style="green",
        ))

    if len(payload) > cap:
        error(f"Payload too large! {len(payload):,} bytes > {cap:,} available")
        raise typer.Exit(1)

    try:
        result = f5_encode(jpeg_bytes, payload, password=password)
    except Exception as e:
        error(f"F5 encoding failed: {e}")
        raise typer.Exit(1)

    output.write_bytes(result)

    if json_mode:
        _out_json({
            "status": "ok",
            "output": str(output),
            "output_bytes": len(result),
            "payload_bytes": len(payload),
            "capacity_bytes": cap,
            "config": {"method": "F5"},
        })

    success(f"F5-encoded {len(payload):,} bytes → {output}")
    if not quiet:
        console.print(f"\n{FOOTER}")


@f5_app.command("decode")
def f5_decode_cmd(
    ctx: typer.Context,
    input_image: Path = typer.Option(..., "--input", "-i", help="F5-encoded JPEG"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Write recovered bytes here"),
    password: str = typer.Option(..., "--password", "-p", help="Password used at encode time"),
    raw: bool = typer.Option(False, "--raw", help="Output raw bytes (hex)"),
):
    """🔎 Recover a payload previously hidden with `stegg dct f5 encode`."""
    json_mode = ctx.obj.get("json_mode", False)
    quiet = ctx.obj.get("quiet", False)

    if not quiet and not json_mode:
        print_banner(small=True)

    jpeg_bytes = _check_jpeg(input_image)

    try:
        data = f5_decode(jpeg_bytes, password=password)
    except Exception as e:
        error(f"F5 decoding failed: {e}")
        raise typer.Exit(1)

    if json_mode:
        result = {"status": "ok", "payload_bytes": len(data)}
        if output:
            output.write_bytes(data)
            result["output"] = str(output)
        if raw:
            result["hex"] = data.hex()
        text = _try_decode_utf8(data)
        if text is not None:
            result["text"] = text
        else:
            result["hex_preview"] = data[:512].hex()
        _out_json(result)

    success(f"Extracted {len(data):,} bytes via F5")

    if output:
        output.write_bytes(data)
        success(f"Saved to: {output}")
    elif raw:
        console.print(Panel(data.hex(), title="[cyan]Raw Data (hex)[/cyan]", border_style="cyan"))
    else:
        try:
            console.print(Panel(data.decode("utf-8"), title=f"{STATUS['decode']} [cyan]Decoded Message[/cyan]",
                                border_style="cyan", box=box.DOUBLE))
        except UnicodeDecodeError:
            warning("Data is not valid UTF-8, showing hex preview:")
            console.print(Panel(data[:500].hex() + ("..." if len(data) > 500 else ""),
                                title="[yellow]Binary Data (hex preview)[/yellow]", border_style="yellow"))

    if not quiet:
        console.print(f"\n{FOOTER}")


@f5_app.command("capacity")
def f5_capacity_cmd(
    input_image: Path = typer.Option(..., "--input", "-i", help="JPEG to measure"),
):
    """📏 Report how many payload bytes fit under F5 DCT embedding."""
    jpeg_bytes = _check_jpeg(input_image)
    cap = f5_capacity(jpeg_bytes)

    # Build a readable table: key info first, then per-k capacity.
    table = Table(show_header=False, box=box.SIMPLE)
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Total coefficients", f"{cap['coeff_total']:,}")
    table.add_row("Large coefficients", f"{cap['coeff_large']:,}")
    table.add_row("±1 coefficients", f"{cap['coeff_one']:,}")
    table.add_row("Zero coefficients", f"{cap['coeff_zero']:,}")
    table.add_row("k=1 capacity", f"{cap['capacity'][1]:,} bytes")
    table.add_row("Max capacity (auto-k)", f"{f5_capacity_bytes(jpeg_bytes):,} bytes")
    console.print(Panel(table, title="[cyan]F5 capacity[/cyan]", border_style="cyan"))


# ============== TEXT STEG COMMANDS ==============

import text_core

text_app = typer.Typer(help="🔤 Text steganography: hide/reveal in plain text")
app.add_typer(text_app, name="text")


def _read_cover_or_stego(path_or_dash: str) -> str:
    """Read UTF-8 text from a path, or from stdin if '-'."""
    if path_or_dash == "-":
        return sys.stdin.read()
    return Path(path_or_dash).read_text(encoding="utf-8")


@text_app.command("encode")
def text_encode_cmd(
    method: str = typer.Option(..., "--method", "-m", help=f"One of: {', '.join(text_core.METHODS)}"),
    cover: str = typer.Option(..., "--cover", "-c", help="Cover text file path (or '-' for stdin)"),
    secret: str = typer.Option(..., "--secret", "-s", help="Secret string to hide"),
    output: Optional[Path] = typer.Option(None, "--out", "-o", help="Output path (stdout if omitted)"),
):
    """Hide a secret string in a cover text via a classic text-steg method."""
    if method not in text_core.METHODS:
        error(f"unknown method '{method}'. Try one of: {', '.join(text_core.METHODS)}")
        raise typer.Exit(1)
    try:
        cover_text = _read_cover_or_stego(cover)
    except Exception as e:
        error(f"failed to read cover: {e}")
        raise typer.Exit(1)
    try:
        stego = text_core.encode(cover_text, secret, method)
    except text_core.TextStegCapacityError as e:
        error(str(e))
        raise typer.Exit(1)

    if output is None:
        sys.stdout.write(stego)
    else:
        output.write_text(stego, encoding="utf-8")
        success(f"wrote {len(stego)} chars ({len(stego.encode('utf-8'))} bytes) to {output}")


@text_app.command("decode")
def text_decode_cmd(
    method: str = typer.Option(..., "--method", "-m", help=f"One of: {', '.join(text_core.METHODS)}"),
    stego: str = typer.Option(..., "--stego", "-i", help="Stego text file path (or '-' for stdin)"),
):
    """Recover a hidden secret from a stego text."""
    if method not in text_core.METHODS:
        error(f"unknown method '{method}'. Try one of: {', '.join(text_core.METHODS)}")
        raise typer.Exit(1)
    try:
        stego_text = _read_cover_or_stego(stego)
    except Exception as e:
        error(f"failed to read stego: {e}")
        raise typer.Exit(1)
    recovered = text_core.decode(stego_text, method)
    sys.stdout.write(recovered)
    if recovered and not recovered.endswith("\n"):
        sys.stdout.write("\n")


@text_app.command("capacity")
def text_capacity_cmd(
    method: str = typer.Option(..., "--method", "-m", help=f"One of: {', '.join(text_core.METHODS)}"),
    cover: str = typer.Option(..., "--cover", "-c", help="Cover text file path (or '-' for stdin)"),
):
    """Report how many payload bytes a cover can carry under a method."""
    if method not in text_core.METHODS:
        error(f"unknown method '{method}'. Try one of: {', '.join(text_core.METHODS)}")
        raise typer.Exit(1)
    try:
        cover_text = _read_cover_or_stego(cover)
    except Exception as e:
        error(f"failed to read cover: {e}")
        raise typer.Exit(1)
    rep = text_core.capacity(cover_text, method)
    table = Table(show_header=False, box=box.SIMPLE)
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    for k, v in rep.items():
        table.add_row(k, str(v))
    console.print(Panel(table, title=f"[cyan]capacity: {method}[/cyan]", border_style="cyan"))


# ============== 🪆 MATRYOSHKA COMMANDS ==============

# ---------------------------------------------------------------------------
# 🪆 MATRYOSHKA COMMANDS
#
# Naming note: the matryoshka verbs are *embed* and *extract*, not *encode*
# and *decode*.  The distinction is intentional:
#
#   encode  = single-pass LSB/DCT/F5 stego into ONE carrier
#   embed   = nested multi-layer stego — each layer's carrier becomes the
#             next layer's payload.  You're embedding a payload inside
#             multiple carriers, not just encoding it once.
#   extract = the inverse — recursively peel layers until you reach the
#             innermost payload.
#
# In the matryoshka model, every layer IS an encode step, but the composite
# action is an *embedding* across a carrier stack.
# ---------------------------------------------------------------------------

matryoshka_app = typer.Typer(
    name="matryoshka",
    help="🪆 Matryoshka nested-image steganography (Russian nesting dolls)",
    rich_markup_mode="rich",
)
app.add_typer(matryoshka_app)


def _load_carriers(paths: List[Path]) -> List[Tuple[Image.Image, str]]:
    """Load carrier images from paths. Returns innermost-first list."""
    carriers = []
    for p in paths:
        if not p.exists():
            error(f"Carrier image not found: {p}")
            raise typer.Exit(1)
        img = Image.open(p).convert("RGBA")
        carriers.append((img, p.name))
    # CLI accepts outermost-first; reverse to innermost-first
    carriers.reverse()
    return carriers


def _print_layer_tree(layers: List[DecodeLayer], indent: int = 0):
    """Pretty-print a nested decode layer tree."""
    prefix = "  " * indent
    for layer in layers:
        type_icon = {
            "steg_header": "📦",
            "nested_image": "🪆",
            "nested_image_raw": "🪆",
            "file": "📁",
            "text": "📝",
            "binary": "⚫",
            "no_data_found": "❌",
            "max_depth_reached": "⚠️",
            "error": "💥",
        }.get(layer.type, "❓")

        name_part = f" [{layer.filename}]" if layer.filename else ""
        size_part = f" ({layer.data_size:,} B)" if layer.data_size else ""
        print(f"{prefix}{type_icon} L{layer.depth} [{layer.type}]{name_part}{size_part}")
        if layer.preview and layer.type not in ("nested_image", "nested_image_raw"):
            preview_short = layer.preview[:120].replace("\n", " ")
            print(f"{prefix}   {preview_short}")
        if layer.nested:
            _print_layer_tree(layer.nested, indent + 1)


@matryoshka_app.command()
def embed(
    payload_path: Path = typer.Option(
        ..., "--payload", "-p", help="File to hide (innermost secret)"
    ),
    carriers: List[Path] = typer.Option(
        ..., "--carrier", "-c", help="Carrier image (outermost first; repeatable)"
    ),
    output: Path = typer.Option(
        None, "--output", "-o", help="Output image path"
    ),
    password: Optional[str] = typer.Option(
        None, "--password", "-w", help="Encryption password (innermost layer only)"
    ),
    channels: str = typer.Option(
        "RGBA", "--channels", help="Channel preset (R, G, B, A, RGB, RGBA, etc.)"
    ),
    bits: int = typer.Option(
        2, "--bits", "-b", help="Bits per channel (1-8)", min=1, max=8
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print capacity plan only, do not embed"
    ),
):
    """
    🪆 Embed a payload into a stack of carrier images (nested LSB encoding).

    Carriers are specified outermost-first (matching the mental model) and
    reversed internally to innermost-first for the encoding engine.

    Examples:
        stegg matryoshka embed -p secret.txt -c inner.png -c outer.png -o nested.png
        stegg matryoshka embed -p data.bin -c a.png -c b.png -c c.png --dry-run
    """
    if not carriers:
        error("At least one --carrier is required")
        raise typer.Exit(1)

    if not payload_path.exists():
        error(f"Payload file not found: {payload_path}")
        raise typer.Exit(1)

    payload = payload_path.read_bytes()
    info(f"Payload: {payload_path} ({len(payload):,} bytes)")

    carrier_tuples = _load_carriers(carriers)
    info(f"Carriers: {len(carrier_tuples)} layers (outermost-first on CLI)")

    config = MatryoshkaConfig(
        channels=channels, bits=bits, password=password,
        max_depth=max(len(carrier_tuples), 11),
    )

    if dry_run:
        info("Dry-run mode — capacity plan only")
        plan = plan_nesting(len(payload), carrier_tuples, config, mode="estimate")
        _print_plan(plan)
        return

    try:
        result_img, reports = encode_nested(payload, carrier_tuples, config)
    except ValueError as exc:
        error(str(exc))
        raise typer.Exit(1)

    if output is None:
        output = Path("matryoshka_encoded.png")

    result_img.save(output, format="PNG")
    success(f"Encoded {len(reports)} layers → {output}")
    _print_plan(reports)


def _print_plan(reports: List[LayerReport]):
    """Print a capacity plan / layer report table."""
    table = Table(title="🪆 Layer Plan", box=box.ROUNDED)
    table.add_column("Layer", style="cyan", justify="right")
    table.add_column("Carrier", style="magenta")
    table.add_column("Capacity", style="green", justify="right")
    table.add_column("Payload", style="yellow", justify="right")
    table.add_column("Fits", justify="center")
    table.add_column("Output", style="blue", justify="right")

    for r in reports:
        fits_icon = "✅" if r.fits else "❌"
        output_str = _format_size_cli(r.output_size) if isinstance(r.output_size, int) else str(r.output_size)
        table.add_row(
            str(r.layer),
            r.carrier_name,
            _format_size_cli(r.capacity),
            _format_size_cli(r.payload_size),
            fits_icon,
            output_str,
        )
    console.print(table)


def _format_size_cli(size_bytes: int | str) -> str:
    """Format bytes for CLI display."""
    if isinstance(size_bytes, str):
        return size_bytes
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


@matryoshka_app.command()
def extract(
    image: Path = typer.Argument(..., help="Image to recursively extract layers from"),
    password: Optional[str] = typer.Option(
        None, "--password", "-w", help="Decryption password"
    ),
    max_depth: int = typer.Option(
        11, "--max-depth", "-d", help="Maximum recursion depth (1-11)", min=1, max=11
    ),
    extract_dir: Optional[Path] = typer.Option(
        None, "--extract-dir", "-e", help="Write each layer's raw data to files"
    ),
):
    """
    🪆 Recursively extract layers from a Matryoshka-encoded image.

    Prints a depth-indented tree of discovered layers.  Use --extract-dir
    to write each layer's raw data to disk.

    Examples:
        stegg matryoshka extract nested.png
        stegg matryoshka extract nested.png -d 5 -e ./layers/
    """
    if not image.exists():
        error(f"Image not found: {image}")
        raise typer.Exit(1)

    img = Image.open(image).convert("RGBA")
    info(f"Decoding: {image} ({img.size[0]}x{img.size[1]})")

    config = MatryoshkaConfig(max_depth=max_depth, password=password)
    layers = decode_nested(img, config)

    if not layers:
        warning("No layers found")
        return

    print(f"\n🪆  Matryoshka decode — {image.name}")
    _print_layer_tree(layers)

    # Extract files if requested
    if extract_dir:
        extract_dir.mkdir(parents=True, exist_ok=True)
        _extract_layers(layers, extract_dir)


def _extract_layers(layers: List[DecodeLayer], out_dir: Path, prefix: str = ""):
    """Write DecodeLayer raw_data to disk."""
    for layer in layers:
        if layer.raw_data:
            name = layer.filename or f"layer{layer.depth}.bin"
            fname = f"{prefix}{name}"
            out_path = out_dir / fname
            out_path.write_bytes(layer.raw_data)
            info(f"  Extracted: {out_path}")
        if layer.nested:
            _extract_layers(layer.nested, out_dir, f"{prefix}L{layer.depth}_")


@matryoshka_app.command()
def plan(
    payload_size: int = typer.Argument(..., help="Size of innermost payload in bytes"),
    carriers: List[Path] = typer.Option(
        ..., "--carrier", "-c", help="Carrier image (outermost first; repeatable)"
    ),
    channels: str = typer.Option(
        "RGBA", "--channels", help="Channel preset"
    ),
    bits: int = typer.Option(
        2, "--bits", "-b", help="Bits per channel (1-8)", min=1, max=8
    ),
    exact: bool = typer.Option(
        False, "--exact", help="Actually encode to measure exact PNG sizes (slow)"
    ),
):
    """
    📐 Plan a Matryoshka nesting without encoding.

    Walks the carrier stack and predicts whether each layer has enough
    capacity for the expected payload (original data for innermost,
    serialised PNG for intermediate layers).

    Examples:
        stegg matryoshka plan 4096 -c a.png -c b.png -c c.png
        stegg matryoshka plan 1024 -c a.png -c b.png --exact
    """
    if not carriers:
        error("At least one --carrier is required")
        raise typer.Exit(1)

    carrier_tuples = _load_carriers(carriers)
    config = MatryoshkaConfig(channels=channels, bits=bits)

    mode = "exact" if exact else "estimate"
    info(f"Planning {len(carrier_tuples)} layers for {payload_size:,}B payload (mode={mode})")

    reports = plan_nesting(payload_size, carrier_tuples, config, mode=mode)
    _print_plan(reports)

    all_fit = all(r.fits for r in reports)
    if all_fit:
        success("All layers fit! ✓")
    else:
        first_bad = next(r for r in reports if not r.fits)
        error(f"Overflow at layer {first_bad.layer} ({first_bad.carrier_name}): "
              f"need {first_bad.payload_size:,}B, have {first_bad.capacity:,}B")


# ============== INFO COMMAND ==============

@app.command()
def info_cmd():
    """
    ℹ️ Show system information and capabilities
    """
    print_banner(small=True)
    print_stego()

    # Crypto status
    crypto = crypto_status()
    crypto_table = Table(show_header=False, box=box.SIMPLE)
    crypto_table.add_column("Property", style="cyan")
    crypto_table.add_column("Value")

    if crypto['cryptography_available']:
        crypto_table.add_row("AES Encryption", "[green]✓ Available[/green]")
    else:
        crypto_table.add_row("AES Encryption", "[yellow]✗ Not installed[/yellow]")

    crypto_table.add_row("Available Methods", ", ".join(crypto['available_methods']))
    crypto_table.add_row("Recommended", crypto['recommended'])

    console.print(Panel(crypto_table, title="[green]Cryptography[/green]", border_style="green"))

    # Channels
    channel_list = " • ".join(CHANNEL_PRESETS.keys())
    console.print(Panel(
        f"[cyan]{channel_list}[/cyan]",
        title="[cyan]Channel Presets[/cyan]",
        border_style="cyan",
    ))

    # Version info
    console.print(Panel(
        "[green]STEGOSAURUS WRECKS[/green] v2.0\n"
        "[dim]Ultimate Steganography Suite[/dim]\n\n"
        f"{TAGLINES[0]}",
        title="[magenta]About[/magenta]",
        border_style="magenta",
    ))

    console.print(f"\n{FOOTER}")


# ============== CHUNKS COMMAND ==============


@app.command("chunks")
def chunks_cmd(
    ctx: typer.Context,
    image: Path = typer.Argument(..., help="PNG image to read chunks from"),
):
    """📦 Read all PNG chunks (type, length, text content for text chunks)."""
    json_mode = ctx.obj.get("json_mode", False)

    p = Path(image)
    if not p.exists():
        error(f"Image not found: {p}")
        raise typer.Exit(1)
    raw = p.read_bytes()
    chunks = read_png_chunks(raw)
    text = extract_text_chunks(raw)

    if json_mode:
        _out_json({
            "chunks": [{"type": c.get("type", "?"), "size": c.get("length", 0)} for c in chunks],
            "text": text,
            "total": len(chunks),
        })

    table = Table(title=f"📦 PNG Chunks — {image.name}", box=box.ROUNDED)
    table.add_column("Type", style="cyan")
    table.add_column("Length", style="green", justify="right")
    table.add_column("Content Preview", style="white")
    for c in chunks:
        ct = c.get("type", "?")
        length = c.get("length", 0)
        preview = ""
        raw_data = c.get("data")
        if ct in ("tEXt", "iTXt", "zTXt") and isinstance(raw_data, (bytes, bytearray)):
            try:
                preview = raw_data.decode("utf-8", errors="replace")[:80]
            except Exception:
                preview = raw_data[:32].hex()
        table.add_row(ct, f"{length:,}", preview)
    console.print(table)

    if text:
        console.print(Panel(
            "\n".join(f"[cyan]{k}:[/cyan] {v[:120]}" for k, v in text.items()),
            title="[green]Text Chunks[/green]",
            border_style="green",
        ))


# ============== ANALYSIS TOOL COMMANDS ==============


@app.command("analysis-tool")
def analysis_tool_cmd(
    ctx: typer.Context,
    image: Path = typer.Argument(..., help="File to analyze"),
    action: str = typer.Argument(..., help="Analysis action name (use list-tools to see available)"),
):
    """🔬 Run a specific analysis function on a file."""
    json_mode = ctx.obj.get("json_mode", False)

    p = Path(image)
    if not p.exists():
        error(f"File not found: {p}")
        raise typer.Exit(1)

    result = execute_action(action, p.read_bytes())
    if json_mode:
        if hasattr(result, "to_dict"):
            _out_json(result.to_dict())
        else:
            _out_json({"result": str(result)})

    if hasattr(result, "to_dict"):
        import json as _json
        console.print(Panel(
            _json.dumps(result.to_dict(), indent=2, default=str),
            title=f"[cyan]analysis-tool {action}[/cyan]",
            border_style="cyan",
        ))
    else:
        console.print(Panel(
            str(result),
            title=f"[cyan]analysis-tool {action}[/cyan]",
            border_style="cyan",
        ))


@app.command("list-tools")
def list_tools_cmd(ctx: typer.Context):
    """📋 List all available analysis tool actions."""
    json_mode = ctx.obj.get("json_mode", False)
    tools = list_available_tools()

    if json_mode:
        _out_json({"tools": tools, "count": len(tools)})

    table = Table(title="🔬 Available Analysis Tools", box=box.ROUNDED)
    table.add_column("Tool", style="cyan")
    for t in tools:
        table.add_row(t)
    console.print(table)
    info(f"{len(tools)} tools available")


# ============== DETECT COMMAND ==============


@app.command("detect")
def detect_cmd(
    ctx: typer.Context,
    image: Path = typer.Argument(..., help="Image to check for ST3GG encoding"),
):
    """🔍 Quick ST3GG v3 header detection check."""
    json_mode = ctx.obj.get("json_mode", False)

    if not image.exists():
        error(f"Image not found: {image}")
        raise typer.Exit(1)

    img = Image.open(image)
    det = detect_encoding(img)

    if json_mode:
        _out_json({"detected": bool(det), "config": det} if det else {"detected": False})

    if det:
        success(f"Detected: {det['config']['channels']}, {det['config']['bits_per_channel']} bits/ch, "
                f"{det['config']['strategy']}, payload={det['payload_length']}B")
    else:
        info("No ST3GG encoding header detected")


# ============== CAPACITY COMMAND ==============


@app.command("capacity")
def capacity_cmd(
    ctx: typer.Context,
    image: Path = typer.Argument(..., help="Image to measure"),
    channels: ChannelPreset = typer.Option(ChannelPreset.RGB, "--channels", "-c", help="Channel preset"),
    bits: int = typer.Option(1, "--bits", "-b", help="Bits per channel (1-8)", min=1, max=8),
):
    """📏 Report LSB payload capacity for an image."""
    json_mode = ctx.obj.get("json_mode", False)

    if not image.exists():
        error(f"Image not found: {image}")
        raise typer.Exit(1)

    img = Image.open(image)
    config = create_config(channels=channels.value, bits=bits)
    cap = calculate_capacity(img, config)

    if json_mode:
        _out_json({
            "usable_bytes": cap["usable_bytes"],
            "human": cap["human"],
            "pixels": img.width * img.height,
            "config": {"channels": channels.value, "bits_per_channel": bits},
        })

    table = Table(show_header=False, box=box.SIMPLE)
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Dimensions", f"{img.width} x {img.height}")
    table.add_row("Pixels", f"{img.width * img.height:,}")
    table.add_row("Channels", channels.value)
    table.add_row("Bits/channel", str(bits))
    table.add_row("Usable bytes", f"{cap['usable_bytes']:,}")
    table.add_row("Capacity", cap["human"])
    console.print(Panel(table, title="[cyan]LSB Capacity[/cyan]", border_style="cyan"))


# ============== SPECTER CHANNEL CIPHER ==============

specter_app = typer.Typer(help="🔄 SPECTER channel-cipher steganography (cross-channel hopping)")
app.add_typer(specter_app, name="specter")


@specter_app.command("encode")
def specter_encode_cmd(
    input_image: Path = typer.Option(..., "--input", "-i", help="Input carrier image"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output image path"),
    text: Optional[str] = typer.Option(None, "--text", "-t", help="Text to encode"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="File to encode"),
    pattern: Optional[str] = typer.Option(None, "--pattern", help="Manual pattern like R1-G2-B1"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Password-derived pattern"),
    embed_mode: str = typer.Option("lsb", "--mode", "-m", help="Embedding mode: lsb or dct"),
    encrypt: bool = typer.Option(False, "--encrypt/--no-encrypt", help="XOR-encrypt the payload"),
    ghost: bool = typer.Option(False, "--ghost", help="Enable Ghost Mode (AES-256-GCM + scramble + noise)"),
    density: int = typer.Option(100, "--density", "-d", help="Embedding density 1-100"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output"),
):
    """🔄 Embed data using SPECTER channel-hopping cipher.

    Examples:
        stegg specter encode -i photo.png -t "secret" --pattern R1-G2-B1 -o out.png
        stegg specter encode -i photo.png -t "secret" --password mypass -o out.png
        stegg specter encode -i photo.png -t "secret" --password mypass --ghost -o ghost.png
        stegg specter encode -i photo.png -t "secret" --pattern R1-G2-B1 --mode dct -o dct.png
    """
    if not quiet:
        print_banner(small=True)

    if not input_image.exists():
        error(f"Input image not found: {input_image}")
        raise typer.Exit(1)

    if not text and not file:
        error("Must provide --text or --file")
        raise typer.Exit(1)

    if not pattern and not password:
        error("Must provide --pattern or --password")
        raise typer.Exit(1)

    if embed_mode not in ("lsb", "dct"):
        error("--mode must be 'lsb' or 'dct'")
        raise typer.Exit(1)

    if ghost and embed_mode != "lsb":
        error("Ghost Mode is only available with --mode lsb")
        raise typer.Exit(1)

    if ghost and not password:
        error("Ghost Mode requires --password")
        raise typer.Exit(1)

    payload = file.read_bytes() if file else text.encode("utf-8")

    # Resolve pattern
    if pattern:
        steps = parse_pattern(pattern)
        if steps is None:
            error(f"Invalid pattern: {pattern}")
            raise typer.Exit(1)
        cipher_key = pattern
    else:
        steps = pattern_from_password(password)
        cipher_key = password

    try:
        image = Image.open(input_image)
    except Exception as e:
        error(f"Failed to load image: {e}")
        raise typer.Exit(1)

    if output is None:
        suffix = "_ghost" if ghost else "_specter"
        output = Path(f"steg{suffix}_{input_image.stem}.png")

    if not quiet:
        step_names = " → ".join(s.name for s in steps)
        console.print(Panel(
            f"[cyan]Mode:[/cyan] {embed_mode.upper()}\n"
            f"[cyan]Pattern:[/cyan] {step_names}\n"
            f"[cyan]Steps:[/cyan] {len(steps)}\n"
            f"[cyan]Payload:[/cyan] {len(payload):,} bytes\n"
            f"[cyan]Encrypt:[/cyan] {'Ghost (AES-256-GCM)' if ghost else 'XOR' if encrypt else 'None'}\n"
            f"[cyan]Density:[/cyan] {density}%",
            title="[green]SPECTER Configuration[/green]",
            border_style="green",
        ))

    try:
        if embed_mode == "dct":
            specter_dct_encode(
                image, payload, steps,
                encrypt=encrypt, key=cipher_key if encrypt else "",
                output_path=str(output),
            )
        else:
            specter_lsb_encode(
                image, payload, steps,
                encrypt=encrypt and not ghost,
                key=password or "",
                density=density,
                ghost=ghost,
                output_path=str(output),
            )
    except Exception as e:
        error(f"SPECTER encoding failed: {e}")
        raise typer.Exit(1)

    success(f"SPECTER-encoded {len(payload):,} bytes → {output}")
    if not quiet:
        console.print(f"\n{FOOTER}")


@specter_app.command("decode")
def specter_decode_cmd(
    input_image: Path = typer.Option(..., "--input", "-i", help="SPECTER-encoded image"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Write recovered bytes here"),
    cipher_key: str = typer.Option(..., "--key", "-k", help="Pattern or password used for encoding"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Decryption password (for Ghost Mode)"),
    raw: bool = typer.Option(False, "--raw", help="Output raw bytes (hex)"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output"),
):
    """🔎 Recover data hidden with `stegg specter encode`.

    Examples:
        stegg specter decode -i hidden.png --key R1-G2-B1
        stegg specter decode -i hidden.png --key mypassword
        stegg specter decode -i ghost.png --key mypassword --password mypassword
    """
    if not quiet:
        print_banner(small=True)

    if not input_image.exists():
        error(f"Image not found: {input_image}")
        raise typer.Exit(1)

    try:
        image = Image.open(input_image)
    except Exception as e:
        error(f"Failed to load image: {e}")
        raise typer.Exit(1)

    # Try to resolve the cipher key as a pattern first, then as password
    steps = parse_pattern(cipher_key)
    if steps is None:
        steps = pattern_from_password(cipher_key)

    decrypt_key = password or cipher_key

    # Try LSB decode first, fall back to DCT
    data = None
    mode_used = None

    try:
        data = specter_lsb_decode(image, steps, key=decrypt_key)
        mode_used = "LSB"
        if not quiet:
            info("Detected SPECTER LSB encoding")
    except ValueError:
        pass

    if data is None:
        try:
            data = specter_dct_decode(image, steps, key=decrypt_key)
            mode_used = "DCT"
            if not quiet:
                info("Detected SPECTER DCT encoding")
        except ValueError:
            pass

    if data is None:
        error("No SPECTER data found. Verify --key matches the encoding pattern/password.")
        raise typer.Exit(1)

    success(f"Extracted {len(data):,} bytes via SPECTER ({mode_used})")

    if output:
        output.write_bytes(data)
        success(f"Saved to: {output}")
    elif raw:
        console.print(Panel(data.hex(), title="[cyan]Raw Data (hex)[/cyan]", border_style="cyan"))
    else:
        try:
            console.print(Panel(data.decode("utf-8"), title=f"{STATUS['decode']} [cyan]Decoded Message[/cyan]",
                                border_style="cyan", box=box.DOUBLE))
        except UnicodeDecodeError:
            warning("Data is not valid UTF-8, showing hex preview:")
            console.print(Panel(data[:500].hex() + ("..." if len(data) > 500 else ""),
                                title="[yellow]Binary Data (hex preview)[/yellow]", border_style="yellow"))

    if not quiet:
        console.print(f"\n{FOOTER}")


# Entry point
def main_cli():
    """Main entry point"""
    app()


if __name__ == "__main__":
    main_cli()
