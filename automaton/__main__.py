"""Command line entry point (see docs/ja/07-dfa-match.md).

    python3 -m automaton <pattern> [text ...]

With texts, report whether each one matches. Without, read lines from
standard input and print the ones that match, the way grep does.
"""

import sys

from .dfa import accepts, from_nfa, minimize, rename
from .nfa import build

USAGE = "usage: python3 -m automaton <pattern> [text ...]"


def main(argv):
    if len(argv) < 2:
        print(USAGE, file=sys.stderr)
        return 2
    pattern, texts = argv[1], argv[2:]
    try:
        dfa = minimize(rename(from_nfa(build(pattern))))
    except ValueError as err:
        print(f"bad pattern {pattern!r}: {err}", file=sys.stderr)
        return 2

    if texts:
        for text in texts:
            print(f"{'match   ' if accepts(dfa, text) else 'no match'}  {text!r}")
        return 0

    for line in sys.stdin:
        line = line.rstrip("\n")
        if accepts(dfa, line):
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
