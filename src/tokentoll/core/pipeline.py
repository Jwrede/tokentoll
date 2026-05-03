def run_scan(paths: list[str], output_format: str, calls_per_month: int) -> int:
    raise NotImplementedError("scan command not yet implemented")


def run_diff_command(
    ref: str | None,
    base: str | None,
    head: str | None,
    output_format: str,
    calls_per_month: int,
) -> int:
    raise NotImplementedError("diff command not yet implemented")
