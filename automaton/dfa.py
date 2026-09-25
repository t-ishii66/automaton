"""NFA -> DFA -> minimized DFA (see docs/ja/03-nfa-to-dfa.md and docs/ja/04-minimize.md)."""

import unicodedata

from .nfa import EPS


class DFA:
    def __init__(self, states, start, accept, trans, name):
        self.states = states  # in discovery order
        self.start = start
        self.accept = accept  # set of accepting states
        self.trans = trans    # {(state, symbol): state}; missing key = no transition
        self.name = name      # state -> display name


def closure(nfa, states):
    """The epsilon-closure: every state reachable without reading any input."""
    out, todo = set(states), list(states)
    while todo:
        s = todo.pop()
        for sym, t in nfa.edges[s]:
            if sym is EPS and t not in out:
                out.add(t)
                todo.append(t)
    return frozenset(out)


def move(nfa, states, sym):
    """Where `sym` takes us from any of `states`, ignoring epsilon."""
    return frozenset(t for s in states for x, t in nfa.edges[s] if x == sym)


def symbols(nfa):
    return sorted({sym for out in nfa.edges.values() for sym, _ in out if sym is not EPS})


def from_nfa(nfa):
    """Subset construction: one DFA state is a set of NFA states."""
    start = closure(nfa, [nfa.start])
    states, todo, trans = [start], [start], {}
    while todo:
        cur = todo.pop(0)
        for sym in symbols(nfa):
            nxt = closure(nfa, move(nfa, cur, sym))
            if not nxt:
                continue  # no transition on this symbol
            if nxt not in states:
                states.append(nxt)
                todo.append(nxt)
            trans[(cur, sym)] = nxt
    accept = {s for s in states if nfa.accept in s}
    name = {s: ",".join(nfa.label[k] for k in sorted(s)) for s in states}
    return DFA(states, start, accept, trans, name)


def rename(dfa):
    """Replace each set of NFA states by a short name: i, 1, 2, ..., f."""
    name, k, a = {}, 0, 0
    for s in dfa.states:
        if s == dfa.start:
            name[s] = "i"
        elif s in dfa.accept:
            a += 1
            name[s] = "f" if a == 1 else f"f{a}"
        else:
            k += 1
            name[s] = str(k)
    return DFA(
        [name[s] for s in dfa.states],
        name[dfa.start],
        {name[s] for s in dfa.accept},
        {(name[s], sym): name[t] for (s, sym), t in dfa.trans.items()},
        {name[s]: name[s] for s in dfa.states},
    )


def minimize(dfa):
    """Merge states that cannot be told apart, by refining a partition."""
    alphabet = sorted({sym for _, sym in dfa.trans})
    rank = {s: i for i, s in enumerate(dfa.states)}

    # (1) split into the accepting states and the rest
    groups = [g for g in ([s for s in dfa.states if s in dfa.accept],
                          [s for s in dfa.states if s not in dfa.accept]) if g]
    while True:
        where = {s: i for i, g in enumerate(groups) for s in g}
        split = []
        for g in groups:
            buckets = {}
            for s in g:
                # (2) which symbols have a transition at all, and
                # (3) which group each of those transitions leads to
                key = tuple((sym, where[dfa.trans[(s, sym)]])
                            for sym in alphabet if (s, sym) in dfa.trans)
                buckets.setdefault(key, []).append(s)
            split.extend(buckets.values())
        if len(split) == len(groups):  # (4) nothing split any further
            break
        groups = split

    groups.sort(key=lambda g: min(rank[s] for s in g))
    name = {}
    for g in groups:
        for s in g:
            name[s] = ",".join(sorted(g, key=lambda x: rank[x]))
    states = [name[g[0]] for g in groups]
    return DFA(
        states,
        name[dfa.start],
        {name[s] for s in dfa.accept},
        {(name[s], sym): name[t] for (s, sym), t in dfa.trans.items()},
        {s: s for s in states},
    )


def accepts(dfa, text):
    """Does `text` match? Read it once, left to right, with no backtracking."""
    s = dfa.start
    for ch in text:
        if (s, ch) not in dfa.trans:
            return False  # no transition: the answer is already no
        s = dfa.trans[(s, ch)]
    return s in dfa.accept


def _width(s):
    """Display width in a monospace terminal: CJK characters take two columns."""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def table(dfa):
    """Print the transition table; `*` marks an accepting state."""
    alphabet = sorted({sym for _, sym in dfa.trans})
    head = ["状態"] + [f"{sym} による遷移先" for sym in alphabet]
    rows = [[dfa.name[s] + ("*" if s in dfa.accept else "")]
            + [dfa.name[dfa.trans[(s, sym)]] if (s, sym) in dfa.trans else "なし"
               for sym in alphabet]
            for s in dfa.states]
    widths = [max(_width(r[i]) for r in [head] + rows) for i in range(len(head))]
    for r in [head] + rows:
        print("  ".join(c + " " * (w - _width(c)) for c, w in zip(r, widths)).rstrip())
