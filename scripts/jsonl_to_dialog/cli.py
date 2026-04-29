"""CLI: read a Claude Code SDK transcript (JSONL), write a Markdown dialog.

Usage:
    python -m scripts.jsonl_to_dialog.cli INPUT [-o OUTPUT] [--no-wrap-thinking]
                                                [--truncate N]

If `-o` is omitted, the output path is `INPUT` with `.dialog.md` appended
(e.g. `research-processing.log` -> `research-processing.log.dialog.md`).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .parser import parse_file
from .renderer import RenderOptions, render


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="jsonl_to_dialog",
        description="Transform a Claude Code SDK JSONL transcript into a Markdown dialog.",
    )
    p.add_argument("input", type=Path, help="Path to the input .jsonl / .log file.")
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output Markdown path. Default: <input>.dialog.md",
    )
    p.add_argument(
        "--no-wrap-thinking",
        dest="wrap_thinking",
        action="store_false",
        help="Render assistant 'thinking' blocks verbatim instead of inside <details>.",
    )
    p.add_argument(
        "--truncate",
        type=int,
        default=4000,
        help="Max chars of a tool_result body before truncation marker (default 4000).",
    )
    return p


def _default_output(input_path: Path) -> Path:
    return input_path.with_name(input_path.name + ".dialog.md")


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    input_path: Path = args.input
    if not input_path.exists():
        print(f"error: input not found: {input_path}", file=sys.stderr)
        return 2

    output_path: Path = args.output if args.output is not None else _default_output(input_path)

    events = parse_file(input_path)
    options = RenderOptions(
        wrap_thinking=args.wrap_thinking,
        truncate_chars=args.truncate,
        source_label=input_path.name,
    )
    markdown = render(events, options)
    output_path.write_text(markdown, encoding="utf-8")
    print(
        f"wrote {output_path} ({len(events)} events, {len(markdown):,} chars)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
