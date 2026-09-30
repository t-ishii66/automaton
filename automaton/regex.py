"""Regular expression parser (see docs/ja/02-regex-to-nfa.md).

Recursive descent over this grammar -- the same style as the LL(1) appendix:

    alt  -> cat { '|' cat }
    cat  -> rep { rep }
    rep  -> atom { '*' | '?' }
    atom -> '(' alt ')' | CHAR

The result is an AST of nested tuples:
    ('sym', c) ('cat', x, y) ('alt', x, y) ('star', x) ('opt', x)
"""


class _Parser:
    def __init__(self, pattern):
        self.s = pattern
        self.i = 0

    def peek(self):
        return self.s[self.i] if self.i < len(self.s) else None

    def take(self):
        c = self.peek()
        if c is None:
            raise ValueError("unexpected end of pattern")
        self.i += 1
        return c

    def alt(self):
        node = self.cat()
        while self.peek() == "|":
            self.take()
            node = ("alt", node, self.cat())
        return node

    def cat(self):
        node = self.rep()
        while self.peek() not in (None, "|", ")"):
            node = ("cat", node, self.rep())
        return node

    def rep(self):
        node = self.atom()
        while self.peek() in ("*", "?"):
            node = ("star" if self.take() == "*" else "opt", node)
        return node

    def atom(self):
        c = self.take()
        if c == "(":
            node = self.alt()
            if self.peek() != ")":
                raise ValueError("')' expected")
            self.take()
            return node
        if c in "|*?)":
            raise ValueError(f"unexpected {c!r}")
        return ("sym", c)


def parse(pattern):
    """Parse `pattern` into an AST."""
    p = _Parser(pattern)
    node = p.alt()
    if p.peek() is not None:
        raise ValueError(f"unexpected {p.peek()!r} at position {p.i}")
    return node
