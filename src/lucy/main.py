#!/usr/bin/env python3
"""
Lucy — Smart Voice Assistant IoT
Entry point.
"""

from lucy.assistant import Lucy


def main() -> None:
    assistant = Lucy()
    assistant.run_forever()


if __name__ == "__main__":
    main()
