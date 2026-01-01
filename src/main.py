"""
IDA Pro Plugin Manager - Main Entry Point

A standalone Windows application for managing IDA Pro plugins.
Supports both legacy (IDA < 9.0) and modern (IDA >= 9.0) plugin formats.
"""

import sys


def main() -> int:
    """
    Main application entry point.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        # Import and run GUI
        from src.ui.main_window import main as gui_main

        return gui_main()

    except Exception as e:
        print(f"Failed to start application: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
