"""Regular expression -> NFA, by Thompson's construction (see docs/ja/02-regex-to-nfa.md)."""

from .regex import parse

EPS = None  # an epsilon transition: taken without reading any input


class NFA:
    def __init__(self):
        self.n = 0        # number of states handed out so far
        self.edges = {}   # state -> [(symbol or EPS, state)], in construction order
        self.start = None
        self.accept = None
        self.label = {}   # state -> display name

    def state(self):
        """Add a fresh state and return it."""
        s = self.n
        self.n += 1
        self.edges[s] = []
        return s

    def add(self, s, sym, t):
        self.edges[s].append((sym, t))

    def merge(self, keep, drop):
        """Fold state `drop` into state `keep`."""
        if keep == drop:
            return
        self.edges[keep].extend(self.edges.pop(drop))
        for s, out in self.edges.items():
            self.edges[s] = [(sym, keep if t == drop else t) for sym, t in out]


def _build(nfa, node, s):
    """Extend `nfa` from state `s` so that it accepts `node`; return the state reached."""
    kind = node[0]
    if kind == "sym":
        t = nfa.state()
        nfa.add(s, node[1], t)
        return t
    if kind == "cat":
        return _build(nfa, node[2], _build(nfa, node[1], s))
    if kind == "alt":
        left = _build(nfa, node[1], s)
        right = _build(nfa, node[2], s)
        nfa.merge(left, right)  # both branches end in the same state
        return left
    if kind == "opt":
        end = _build(nfa, node[1], s)
        nfa.add(s, EPS, end)     # skip the body entirely
        return end
    if kind == "star":
        body = nfa.state()
        nfa.add(s, EPS, body)
        end = _build(nfa, node[1], body)
        out = nfa.state()
        nfa.add(s, EPS, out)     # skip the body entirely
        nfa.add(end, EPS, body)  # go round again
        nfa.add(end, EPS, out)   # leave the loop
        return out
    raise ValueError(f"unknown node {kind!r}")


def _renumber(nfa):
    """Renumber states in depth-first order and label them i, 1, 2, ..., f.

    Construction order has gaps (merge drops states), and the numbering in the
    diagrams follows the path through the machine, so walk it depth-first.
    """
    order, seen = [], set()

    def visit(s):
        seen.add(s)
        order.append(s)
        for _, t in nfa.edges[s]:
            if t not in seen:
                visit(t)

    visit(nfa.start)
    idx = {s: i for i, s in enumerate(order)}

    out = NFA()
    out.n = len(order)
    out.edges = {idx[s]: [(sym, idx[t]) for sym, t in nfa.edges[s]] for s in order}
    out.start, out.accept = idx[nfa.start], idx[nfa.accept]
    k = 0
    for s in range(out.n):
        if s == out.start:
            out.label[s] = "i"
        elif s == out.accept:
            out.label[s] = "f"
        else:
            k += 1
            out.label[s] = str(k)
    return out


def build(pattern):
    """Build the NFA for the regular expression `pattern`."""
    nfa = NFA()
    nfa.start = nfa.state()
    nfa.accept = _build(nfa, parse(pattern), nfa.start)
    return _renumber(nfa)


def dump(nfa):
    """Print every transition, one per line."""
    for s in sorted(nfa.edges):
        for sym, t in nfa.edges[s]:
            print(f"{nfa.label[s]:>2} -- {sym or 'ε'} --> {nfa.label[t]}")
