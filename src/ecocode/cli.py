from __future__ import annotations

import argparse
from typing import Sequence

from ecocode.commands import baseline, profile, profile_repo


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ecocode",
        description="EcoCode CLI - energy-aware engineering toolkit",
    )
    subparsers = parser.add_subparsers(dest="command")

    profile.register(subparsers)
    profile_repo.register(subparsers)
    baseline.register(subparsers)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0

    return int(handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
