# 07. Turning It into a DFA and Deciding Matches

![Bob and Alice running cards through the finished sorting machine, delighted at the result](../ja/img/alice-bob-07-dfa-match.png)

In [Chapter 06](06-parse-nfa.md) we built an NFA from a pattern.
From here we turn the procedures of [Chapter 03](03-nfa-to-dfa.md) and [Chapter 04](04-minimize.md) into code, and
finally join it all up as a command.

## What We Have at the Starting Point

Running through Chapter 06, the data left in our hands is like this.

```python
>>> from automaton.nfa import build
>>> nfa = build("a(a|b)*bb")
>>> nfa.start, nfa.accept
(0, 6)
>>> for s in sorted(nfa.edges):
...     print(s, nfa.label[s], nfa.edges[s])
0 i [('a', 1)]
1 1 [(None, 2), (None, 4)]
2 2 [('a', 3), ('b', 3)]
3 3 [(None, 2), (None, 4)]
4 4 [('b', 5)]
5 5 [('b', 6)]
6 f []
```

What we hold is only 3 things.

| What we hold | Contents |
| --- | --- |
| `edges` | A listing, per state, of "the arrows leaving it". `None` is ε |
| `start` `accept` | The entrance and exit states. Here, `0` and `6` |
| `label` | The names for display. `0` is `i`, `6` is `f` |

This is the output of Chapter 06, and the input of this chapter.
From here, we build the form with no ε — the DFA.

## 3. Turning It into a DFA

The ε closure of [Chapter 03](03-nfa-to-dfa.md), and the union of the destinations by a symbol.
Both are nothing more than the definitions written down as they are.

The function defined under the name `closure` starts from the states passed in its 2nd argument `states`,
collects every state reachable by ε, and puts them into `out`.
`states` is the starting point; sometimes it is a single start state, and sometimes it is the set returned by `move`.
Since `out` starts as `set(states)`, the `states` we passed in remain in the result as they are.

Among that `out`, the ones **whose ε destinations we have not looked at yet** are `todo`.
`todo` is a part of `out`; it is not the unexamined states of the NFA.
Take one out of `todo`, and if its ε destination is one that has come out for the first time,
add it to both `out` and `todo`. `out` is for accumulating the answer, `todo` is for examining further on from there.
Once `todo` becomes empty, there is nowhere left that can be extended.
Calling `closure(nfa, [1])` on the NFA for `a(a|b)*bb` stops in 3 moves.

![How closure works](../ja/img/tool-closure.svg)

Since the same state is never pushed onto `todo` twice, it stops even in the case where **we can come back to the original state by following ε transitions alone**.
Following the ε transitions of `a(a|b)*bb` (`1→2`, `1→4`, `3→2`, `3→4`) does not bring us back to the original, but
once `*` is nested, as in `(a*)*`, it becomes possible to go all the way round by ε alone, as in `1 → 4 → 1`.
Even then, the destination on the 2nd lap is already in `out`, so it is not pushed onto `todo`, and it stops there.

```python
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
```

Both return a `frozenset`. This is Python's **set whose contents cannot be changed**.
An ordinary set (`set`) like `{1, 2, 4}` can have elements added later, but a `frozenset` is fixed once made, and
in exchange for that it **can be used as a dictionary key, or as an element of another set**.

From here on, one state of the DFA becomes a "set of states of the NFA" itself.
Since we carry sets around as states and look up dictionaries like `trans[(set, symbol)]`,
it has to be a set that does not change.

Looked at from the code side, what `closure` is doing is putting things in and taking them out of 2 containers.

![What the loop of closure is doing](../ja/img/tool-closure-code.svg)

`move`, conversely, follows not a single ε and advances by just one symbol's worth.
Whichever state in the set the arrow leaves from, if the symbol matches then its destination is collected.

![How move works](../ja/img/tool-move.svg)

Advancing one step by a symbol and then widening by ε — that is, `closure(move(...))` —
becomes one square of the `from_nfa` that follows.

Steps (1) through (3) of the build procedure become, just as they are, `from_nfa`.
In the same shape as `closure`, a set that has come out for the first time is added to both `states` and `todo`.
`states` is "the listing of the sets that have come out", `todo` is "the sets whose destinations we have not examined yet", and
once `todo` becomes empty, it is over.

```python
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
```

One state of the DFA is a `frozenset` (a set of states of the NFA) itself.
Since a set can be used directly as a key, the transition table is served by a single dictionary, `trans[(set, symbol)]`.
That `accept` and `name` can hold sets directly is for the same reason.
The judgment "has this set already come out?", `nxt not in states`, is merely comparing in order because `states` is a list,
and this one could be written with a set whose contents can be changed.

The departure set is the ε closure of `nfa.start`, and the accepting states are the sets that contain `nfa.accept`.
The former is step (1) of the build procedure of [Chapter 03](03-nfa-to-dfa.md) itself; the latter is Chapter 03's way of deciding that
"a set containing the final state of the NFA is an accepting state", and they show up just as they are
in the first line and in the `accept = ...` line respectively.

Until `todo` becomes empty, we take out one set at a time and find the destination for each symbol.
The one taken out is `cur`, and the destination found is `nxt`.

![How from_nfa works](../ja/img/tool-subset.svg)

After going round 5 times `todo` becomes empty, and the sets — 5 of them — are all out. These are the states of the DFA.
Redrawn with circles and arrows, it is the same machine as the one we made by hand in [Chapter 03](03-nfa-to-dfa.md).

![The DFA made by taking the 5 sets that came out as states, just as they are](../ja/img/tool-dfa.svg)

Let us confirm it in the form of a transition table too.
`table` prints its headers in Japanese, the way `automaton/dfa.py`
writes them: `状態` is the state, `a による遷移先` is where `a` leads,
and `なし` means there is no transition.

```python
>>> from automaton.nfa import build
>>> from automaton.dfa import from_nfa, table
>>> table(from_nfa(build("a(a|b)*bb")))
状態        a による遷移先  b による遷移先
i           1,2,4           なし
1,2,4       2,3,4           2,3,4,5
2,3,4       2,3,4           2,3,4,5
2,3,4,5     2,3,4           2,3,4,5,f
2,3,4,5,f*  2,3,4           2,3,4,5,f
```

## 4. Minimizing the Number of States

### First, Shorten the Names

The same thing as rewriting `(1,2,4)` as `1` at the beginning of [Chapter 04](04-minimize.md) is what
`rename` does. Left as sets they are long, and since minimization brings sets together further,
it becomes a "set of sets" and unreadable.

It may look like processing purely for the sake of readability, but it is not.
The `minimize` that comes after joins the names of the states it brings together into a new name, so
it presupposes the very fact that a state's name is a string.
The result of `from_nfa` cannot be passed to `minimize` without going through `rename`.

In the order they came out, the start state is renamed `i`, the accepting state `f`, and the rest `1`, `2`, `3`, ….
If there are 2 or more accepting states, the 2nd one onward become `f2`, `f3`, ….
When the start state is at the same time an accepting state, `i` takes priority and `f` is not attached.
For example, the states of `a?b?` are the 3 states `i`, `f` and `f2`, and `i` itself is also an accepting state.
`a(a|b)*bb` has 1 accepting state, and moreover it is different from the start state, so neither case shows up in the table.

The names are for display, and which states are accepting is held by a separate set called `accept`.
It is not accepting because its name is `f`. The `*` attached in the table is also stamped by looking at
that `accept`, not at the name.

```python
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
```

The remaining lines merely rebuild `states`, `start`, `accept` and `trans` using this correspondence table
(the variable `name`).
The shape of the machine does not change. What changes is only the names.

```python
>>> from automaton.nfa import build
>>> from automaton.dfa import from_nfa, rename, table
>>> table(rename(from_nfa(build("a(a|b)*bb"))))
状態  a による遷移先  b による遷移先
i     1               なし
1     2               3
2     2               3
3     2               f
f*    2               f
```

This is the same as the table presented in [Chapter 04](04-minimize.md).
**From here on, `i`, `1`, `2`, `3` and `f` are the names after this renaming**, and
they have nothing to do with the states of the NFA, so take care.

### Repeating the Splitting


The repeated splitting of [Chapter 04](04-minimize.md).
For each state, we make a pair of "by which symbols can it transition" and "which group does each of those destinations belong to".
In the code we call this the `key`, and use it as the key of a dictionary called `buckets`.
Within the same group, states with the same `key` go into the same list of `buckets`, and
if the `key` differs they are separated into different lists. These lists become, just as they are, the next groups.
Since `buckets` is rebuilt inside `for g in groups:`, even if `key`s match across groups,
groups that have once been separated never merge back together.
Step (2) corresponds to the first half and step (3) to the second half, so in the implementation these 2 are brought together into a single `key`.

```python
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
```

The first line, `groups = ...`, is packed tight, so let us take it apart.
Writing the same thing split over 3 lines gives this.

```
accept = [s for s in dfa.states if s in dfa.accept]       # ['f']
other  = [s for s in dfa.states if s not in dfa.accept]   # ['i', '1', '2', '3']
groups = [g for g in (accept, other) if g]
```

The 1st line is the list collecting the accepting states, the 2nd line is the list collecting the rest, and
this is step (1), "divide into the final states and the rest", itself.
The 3rd line merely lines those 2 up — except that `if g` is attached, and
**an empty list is thrown away**.

The reason it has to be thrown away is that one side can become empty.
In the DFA for `a*`, both of the 2 states are accepting states, so `other` becomes an empty list.
Leaving it as it is would produce a "group that has a number but no contents".

As a result, `groups` becomes **a list of groups**, and one group is a list of state names.
For `a(a|b)*bb`, right after step (1) it looks like this.

```
groups = [['f'], ['i', '1', '2', '3']]
```

The 0th is the group of accepting states, the 1st is the group of the rest.
These get split apart, and each single group that remains at the end becomes, just as it is, a single state.

`where` is the dictionary for looking up, from a state name, **the number of the group that state is currently in** —
that is, which position of `groups` it is in.
Right after step (1), its contents look like this.

```
where = {'f': 0, 'i': 1, '1': 1, '2': 1, '3': 1}
```

It means that only `f` is in group 0, and all the rest are in group 1.

The `key` is made using these numbers. State `3` goes to `2` by `a` and to `f` by `b`, so
looking up `where['2']` and `where['f']`, its `key` becomes `(('a', 1), ('b', 0))`.
State `1` goes to `2` by `a` and to `3` by `b`, and both are in group 1, so `(('a', 1), ('b', 1))`.
**Since the `key`s differ, `1` and `3` are separated into different groups.**

State `i` has no destination by `b`, so its `key` becomes `(('a', 1),)`, with only 1 element.
This is the part corresponding to step (2), "split by the kinds of transitions".

If the groups get separated, the contents of `where` change too. The 2nd time it becomes

```
where = {'f': 0, 'i': 1, '1': 2, '2': 2, '3': 3}
```

and the `key`s get rebuilt too. That is why it is necessary to repeat until no splitting occurs.

Following how it actually finishes in 2 rounds gives this.

![How minimize works](../ja/img/tool-minimize.svg)

On the 1st round 2 groups became 4 groups, and on the 2nd round the number of groups did not change, so it stops.
Since "by which symbols can we go" is in the `key`, `i`, which has no destination by `b`,
is separated automatically on the first round. What corresponds to step (2) of [Chapter 04](04-minimize.md)
takes effect not as separate processing, but as part of the `key`.

Taking the 4 groups that remain as states, just as they are, gives this.

![The DFA brought together into 4 states](../ja/img/tool-dfa-min.svg)

Let us confirm it in the form of a transition table too.

```python
>>> from automaton.nfa import build
>>> from automaton.dfa import from_nfa, rename, minimize, table
>>> table(minimize(rename(from_nfa(build("a(a|b)*bb")))))
状態  a による遷移先  b による遷移先
i     1,2             なし
1,2   1,2             3
3     1,2             f
f*    1,2             f
```

## 5. Deciding a Match

It is nothing more than looking up the transition table one character at a time.

```python
def accepts(dfa, text):
    """Does `text` match? Read it once, left to right, with no backtracking."""
    s = dfa.start
    for ch in text:
        if (s, ch) not in dfa.trans:
            return False  # no transition: the answer is already no
        s = dfa.trans[(s, ch)]
    return s in dfa.accept
```

There is neither searching nor backtracking. It finishes in time proportional to the input length.

![How accepts works](../ja/img/tool-accepts.svg)

The variable `s` is rewritten exactly once per character.
It is the same route we followed by hand in [Chapter 04](04-minimize.md).

## 6. Joining It Up into a Tool

All that is left is to call 1 through 5 in order.

```python
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
```

The assembly of the pattern happens only once at the start, and after that, however many lines come, it is only looking up the table.

## Running It Through

Any pattern within the range decided in [Chapter 05](05-subset.md) passes through the same route.

```
$ python3 -m automaton 'a(a|b)*bb' ababb
match     'ababb'
$ python3 -m automaton '(ab)*c' ababc
match     'ababc'
$ python3 -m automaton 'a|bb' bb
match     'bb'
```

The `?` added in [Chapter 05](05-subset.md) is the same.
It matches whether the `u` is there or not, and does not match if 2 of them follow.

```
$ python3 -m automaton 'colou?r' color colour colouur
match     'color'
match     'colour'
no match  'colouur'
```

That it works correctly is confirmed in `tests/test_pipeline.py`.

- That the result of each stage agrees with the figures and tables of the main part (the 9 arrows of the NFA, the 5 states after subset construction, the 4 states after minimization)
- That for a number of patterns, exhaustively enumerating short strings gives the same decision as Python's `re`

```
$ python3 -m pytest tests -q
```

If pytest is not installed, running the file directly runs the same checks.

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

---

With this, we have taken one full look at how a regular expression works.
In [Chapter 01](01-automaton.md) we wrote that "if the machine settles the destination on exactly one, it is enough to trace the input once",
and the path for mechanically building that machine from a regular expression has, up to here, all been joined together.

The regular expression engines we use day to day are also doing something close to this internally.
Depending on the implementation, however, some do not build a DFA and instead follow the NFA while backtracking.
That is the "try one, and if it fails, the other" approach we saw in [Chapter 02](02-regex-to-nfa.md).
That one can handle features that a DFA cannot express, such as back references, but in exchange
it can become extremely slow depending on how things are written.
Turning it into a DFA means that does not happen — that was the meaning of what we did in [Chapter 03](03-nfa-to-dfa.md) and
[Chapter 04](04-minimize.md).
