"""Command-line entry points for Lumos Runtime."""

import argparse
from dataclasses import asdict
import json

from .inspection import inspect_host


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lumos-runtime")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("inspect", help="List host-visible device candidates without opening them")
    parser.parse_args(argv)
    print(json.dumps(asdict(inspect_host()), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
