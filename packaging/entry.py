"""Starts modelhub when the single program file is run. The build tools use this as the
program's entry point."""

import multiprocessing

from modelhub.cli import app

if __name__ == "__main__":
    # A packed program is its own "Python": libraries that start helper processes re-run it with
    # Python-only flags. This answers those before the command line sees them.
    multiprocessing.freeze_support()
    app()
