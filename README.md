# Automata — How Regular Expressions Work

[日本語](README-jp.md)

![Bob and Alice greeting you in a nature park, with a squirrel, a rabbit and a small bird](docs/ja/img/alice-bob-cover.png)

Regular expressions are used in every kind of situation.
But when it comes to "what is going on inside", a somewhat specialized theory called automata shows its face.

So here, we narrow regular expressions down to a boldly small subset,
and implement a tool that processes it in the simplest possible form.
What we handle is **only the 4 operations: concatenation, union `|`, repetition `*`, and optional `?`** (plus parentheses for changing precedence).
There is no `+`, no `.`, no character class, no anchor.

In exchange for cutting the notation down, the backbone of a regular expression engine —
**regular expression → NFA → DFA → minimization → match decision** — connects up into a single line, with no detours.

Of these, the first 3 are in fact the very operations that appear in the theoretical definition of a regular expression.
`+`, `[abc]` and `{2,3}` are all no more than shorthand that can be rewritten into these 3.
So although it is a subset, the essence of how a regular expression works can be grasped here.
The 4th one, `?`, is introduced in [Chapter 05](docs/en/05-subset.md).
It doubles as a demonstration that adding just one rule increases the notation we can handle.

![The minimized DFA](docs/ja/img/01-dfa-min.svg)

For example, `a(a|b)*bb` ends up, in the end, as a machine with these 4 states.
The circles are states, and the arrows say "when you read that character, next you go here".
Once we have brought things this far, whether a string matches or not is settled
by **following exactly one arrow for each character read from the beginning**.
There is no trying a candidate and going back.

## Read

| Chapter | Contents |
| --- | --- |
| [01. What a finite automaton is](docs/en/01-automaton.md) | A machine made of nothing but states and transitions. The example `a(a\|b)*bb` and its nondeterministic finite automaton (NFA) |
| [02. Building an NFA from a regular expression](docs/en/02-regex-to-nfa.md) | Assemble an NFA with 4 rules. And then, what is the trouble with the NFA we get |
| [03. Converting an NFA into a DFA](docs/en/03-nfa-to-dfa.md) | Eliminating ε transitions, and subset construction. The definition of a deterministic finite automaton (DFA) |
| [04. Minimizing the number of states](docs/en/04-minimize.md) | Bring together the states that cannot be distinguished, turning 5 states into 4 |
| [05. Deciding which regular expressions we handle](docs/en/05-subset.md) | The implementation part starts here. Make it able to handle anything within the range of just concatenation, `\|`, `( )`, `*` and `?` |
| [06. Reading a pattern and turning it into an NFA](docs/en/06-parse-nfa.md) | Extract the structure of the pattern and apply the 5 rules |
| [07. Turning it into a DFA and deciding matches](docs/en/07-dfa-match.md) | Run subset construction, minimization and the match decision through, and make it a command |

No code appears in Chapters 01 through 04. They stick to showing the theory with figures and hand calculation.
Chapters 05 through 07 are the implementation part, and that is where code appears for the first time.

The intended reader is someone who "can use regular expressions, but does not know what a regular expression engine does internally".

## Run

The tool built in Chapters 05 through 07 runs right now in this repository.
With Python 3.6 or later, no external libraries are needed.

```
$ python3 -m automaton 'a(a|b)*bb' abb ab aabb ababb bb
match     'abb'
no match  'ab'
match     'aabb'
match     'ababb'
no match  'bb'
```

If you do not hand it any text it reads standard input, so it can also be used like grep.

```
$ printf 'abb\nab\naabb\nxyz\nababb\n' | python3 -m automaton 'a(a|b)*bb'
abb
aabb
ababb
```

What it can handle is only `|` (union), `( )` (parentheses), `*` (repetition), `?` (optional), and the concatenation of characters.
There is no `+`, no `.`, no character class, no anchor. The decision is a match of the whole string; it does not search for partial matches.

## Structure

```
automaton/          The implementation. regular expression → NFA → DFA → minimization → match decision
├── regex.py        Read the pattern and extract its structure
├── nfa.py          Assemble the NFA with 5 rules
├── dfa.py          ε closure / subset construction / minimization / match decision
└── __main__.py     The command-line entry point
docs/ja/            The explanation (Japanese). The figures are hand-written SVG
docs/en/            Its English translation. The figures are shared from docs/ja/img/
tests/              Confirm that each stage agrees with the figures and tables of the explanation, and that the decisions match re
```

The tests run with `pytest`.

```
$ python3 -m pytest tests -q
```

They are written with plain `assert`, so in an environment where pytest is not installed you may also run the files directly.
Either way, the same checks run.

```
$ python3 tests/test_pipeline.py
ok test_nfa_matches_the_figure
ok test_subset_construction_matches_the_figure
ok test_minimized_dfa_matches_the_figure
ok test_same_answers_as_the_regex_module
ok test_other_patterns
ok test_patterns_with_an_epsilon_cycle
ok test_bad_patterns_raise_value_error
```


## Credits

- Planning: t-ishii66 (studied physics at university. Systems engineer. Struggling away at English conversation)
- Base document: t-ishii66
- Documentation: Claude Opus 5
- Coding: Claude Opus 5
- Documentation review: t-ishii66
- Code review: t-ishii66
- Illustrations: Codex GPT6
- Version: 1.0.0

