"""
Debug wrapper for surreal-commands-worker.
Run this file in VSCode debugger to debug the worker process.
"""
import sys

# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

# Import commands module to register commands before worker starts
import commands  # noqa: F401

# Simulate: surreal-commands-worker start
sys.argv = ["surreal-commands-worker", "start"]

from surreal_commands.cli.worker import main

main()
