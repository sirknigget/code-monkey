import logging

logger = get_formatted_logger(__name__)


def print_progress_bar(
    progress: int, progress_max: int, prefix: str = "", width: int = 40
) -> None:
    """Print a progress bar to stdout.

    Args:
        progress: Current progress value.
        progress_max: Maximum progress value.
        prefix: Prefix string to print before the bar.
        width: Width of the progress bar in characters.
    """
    if progress_max == 0:
        percent = 0.0
    else:
        percent = (progress / progress_max) * 100

    filled = int(width * progress // progress_max) if progress_max > 0 else 0
    bar = "█" * filled + "░" * (width - filled)

    # Print progress bar with prefix
    print(
        f"\r{prefix} |{bar}| {percent:5.1f}% ({progress}/{progress_max})",
        end="",
        flush=True,
    )

    # Print newline when complete
    if progress == progress_max:
        print()
