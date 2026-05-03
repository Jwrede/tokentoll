import argparse
import sys

from tokentoll import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tokentoll",
        description="Catch LLM cost changes in code review.",
    )
    parser.add_argument("--version", action="version", version=f"tokentoll {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    # scan command
    scan_parser = subparsers.add_parser("scan", help="Scan files for LLM API calls and costs")
    scan_parser.add_argument("paths", nargs="*", default=["."], help="Paths to scan")
    scan_parser.add_argument(
        "--format", choices=["table", "json", "markdown"], default="table",
        help="Output format (default: table)",
    )
    scan_parser.add_argument(
        "--calls-per-month", type=int, default=1000,
        help="Assumed monthly call volume per call site (default: 1000)",
    )

    # diff command
    diff_parser = subparsers.add_parser("diff", help="Compare LLM costs between git refs")
    diff_parser.add_argument("ref", nargs="?", default=None, help="Git ref to diff against")
    diff_parser.add_argument("--base", default=None, help="Base git ref")
    diff_parser.add_argument("--head", default=None, help="Head git ref (default: HEAD)")
    diff_parser.add_argument(
        "--format",
        choices=["table", "json", "markdown", "github-comment"],
        default="table",
        help="Output format (default: table)",
    )
    diff_parser.add_argument(
        "--calls-per-month", type=int, default=1000,
        help="Assumed monthly call volume per call site (default: 1000)",
    )

    # update command
    subparsers.add_parser("update", help="Update bundled pricing data from LiteLLM")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    if args.command == "scan":
        from tokentoll.core.pipeline import run_scan
        return run_scan(args.paths, args.format, args.calls_per_month)

    if args.command == "diff":
        from tokentoll.core.pipeline import run_diff_command
        return run_diff_command(
            ref=args.ref,
            base=args.base,
            head=args.head,
            output_format=args.format,
            calls_per_month=args.calls_per_month,
        )

    if args.command == "update":
        from tokentoll.pricing.updater import update_bundled_pricing
        update_bundled_pricing()
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
