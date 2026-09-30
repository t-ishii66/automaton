"""The pipeline must reproduce the figures and tables in the two source PDFs."""

import re
import sys
from itertools import product
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from automaton.nfa import build
from automaton.dfa import accepts, from_nfa, minimize, rename

PATTERN = "a(a|b)*bb"


def edges(nfa):
    return [(nfa.label[s], sym or "ε", nfa.label[t])
            for s in sorted(nfa.edges) for sym, t in nfa.edges[s]]


def rows(dfa):
    return {dfa.name[s]: {sym: dfa.name[t] for (x, sym), t in dfa.trans.items() if x == s}
            for s in dfa.states}


def test_nfa_matches_the_figure():
    assert edges(build(PATTERN)) == [
        ("i", "a", "1"),
        ("1", "ε", "2"), ("1", "ε", "4"),
        ("2", "a", "3"), ("2", "b", "3"),
        ("3", "ε", "2"), ("3", "ε", "4"),
        ("4", "b", "5"),
        ("5", "b", "f"),
    ]


def test_subset_construction_matches_the_figure():
    dfa = from_nfa(build(PATTERN))
    assert rows(dfa) == {
        "i":         {"a": "1,2,4"},
        "1,2,4":     {"a": "2,3,4", "b": "2,3,4,5"},
        "2,3,4":     {"a": "2,3,4", "b": "2,3,4,5"},
        "2,3,4,5":   {"a": "2,3,4", "b": "2,3,4,5,f"},
        "2,3,4,5,f": {"a": "2,3,4", "b": "2,3,4,5,f"},
    }
    assert {dfa.name[s] for s in dfa.accept} == {"2,3,4,5,f"}


def test_minimized_dfa_matches_the_figure():
    dfa = minimize(rename(from_nfa(build(PATTERN))))
    assert rows(dfa) == {
        "i":   {"a": "1,2"},
        "1,2": {"a": "1,2", "b": "3"},
        "3":   {"a": "1,2", "b": "f"},
        "f":   {"a": "1,2", "b": "f"},
    }
    assert dfa.accept == {"f"}


def test_same_answers_as_the_regex_module():
    dfa = minimize(rename(from_nfa(build(PATTERN))))
    for n in range(8):
        for text in ("".join(t) for t in product("ab", repeat=n)):
            assert accepts(dfa, text) == bool(re.fullmatch(PATTERN, text)), text


def test_other_patterns():
    for pattern in ["a", "ab", "a*", "(a|b)*", "a|bb", "(ab)*a", "a(b|c)*d",
                    "a?", "ab?", "a?b?", "(ab)?", "(a|b)?c", "a?a?a?", "(a?b)*"]:
        dfa = minimize(rename(from_nfa(build(pattern))))
        for n in range(6):
            for text in ("".join(t) for t in product("abcd", repeat=n)):
                assert accepts(dfa, text) == bool(re.fullmatch(pattern, text)), (pattern, text)


def test_patterns_with_an_epsilon_cycle():
    # A repetition whose body accepts the empty word builds an epsilon cycle
    # (see docs/ja/03-nfa-to-dfa.md): `closure` has to stop walking it. `re`
    # rejects "a**" as a multiple repeat, so each pattern is paired with an
    # equivalent one that `re` does accept.
    for pattern, reference in [("a**", "(?:a*)*"),
                               ("a?*", "(?:a?)*"),
                               ("(a?)*", "(?:a?)*"),
                               ("(a*)*", "(?:a*)*"),
                               ("(a?b?)*", "(?:a?b?)*"),
                               ("((a|b)?)*", "(?:(?:a|b)?)*")]:
        dfa = minimize(rename(from_nfa(build(pattern))))
        for n in range(6):
            for text in ("".join(t) for t in product("ab", repeat=n)):
                assert accepts(dfa, text) == bool(re.fullmatch(reference, text)), (pattern, text)


def test_bad_patterns_raise_value_error():
    # docs/ja/05-subset.md promises the empty pattern and the empty group are
    # not accepted. The exception type is part of the API: __main__ catches
    # ValueError and nothing else, so anything else escapes as a traceback.
    for pattern in ["", "(", "(a", ")", "a)", "*a", "?a", "a|", "|a", "()", "(a|)"]:
        try:
            build(pattern)
        except ValueError:
            continue
        raise AssertionError(pattern)


if __name__ == "__main__":
    # Run the tests without pytest: call every test_* function defined above,
    # in the order they appear. A failing assert stops the run with a traceback.
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
