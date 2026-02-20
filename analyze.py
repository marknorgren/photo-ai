# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "openai",
#     "anthropic",
#     "Pillow",
#     "pillow-heif",
#     "tqdm",
# ]
# ///
"""Backward-compatible entry point. See photo_ai/ for the package."""
from photo_ai.__main__ import main

main()
