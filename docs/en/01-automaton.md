---
title: "01. What a Finite Automaton Is"
description: "A machine made of nothing but states and transitions. How to read a finite automaton, and the difference between an NFA and a DFA, through one example."
lang: en
---

# 01. What a Finite Automaton Is

![Bob and Alice crossing a brook on stepping stones, a rabbit on the bank](../ja/img/alice-bob-01-automaton.png)

The conversion from a nondeterministic finite automaton (NFA) to a deterministic finite automaton (DFA)
is a basic technique used in regular expressions and in the lexical analysis of compilers, and it is also easy to implement.

In this chapter we pin down what a finite automaton is in the first place,
and prepare one example that we will keep using all the way through the chapters that follow.

## Finite Automata

A finite automaton is a machine made of nothing but **states** and **transitions**.
It reads the input one character at a time, and moves from the state it is in now to the next state according to the character it read.
If it is in a final state when it has finished reading the input, the input is "accepted"; if not, it is "not accepted".

"Finite" means that **the number of states is finite**.
All this machine can remember is "which state am I in now",
and neither how many characters it has read nor what came along the way is left over, beyond the part that has been folded into the distinction between states.

In exchange for being limited in what it can remember, the machine itself fits within a finite size.
If there are 4 states and 2 kinds of symbols, then "from which state, on reading which character, do we go where" has
only 8 possibilities. They can all be written out, and the machine can be run exactly as written.

Put the other way round, it cannot do anything like counting.
Deciding whether `(` and `)` are lined up in the same number — a judgment like that is beyond the reach of a finite automaton.
As long as the states are finite, a number that could grow arbitrarily large cannot be remembered.

Here is how to read the figures.

| Notation | Meaning |
| --- | --- |
| Circle | A state |
| A circle with an arrow entering from the left | The start state |
| A double circle | A final state (accepting state) |
| An arrow, and the symbol beside it | The transition taken when that symbol is read |
| An orange arrow (`ε`) | It can transition without reading input (an ε transition) |

## Example

As the example we will use from here on, we take up the regular expression

```
a(a|b)*bb
```

It is the collection of strings that begin with `a`, continue with some number of `a`s and `b`s, and end with `bb`.
A finite automaton corresponding to this looks, for example, like the following.

![The NFA corresponding to the regular expression a(a\|b)*bb](../ja/img/01-nfa.svg)

Orange is an ε transition. Two ε transitions leave state `1`,
and whether it goes to `2` or to `4` is not determined by the input.
A finite automaton in which **the destination is not settled on a single one** like this
is called a **nondeterministic finite automaton (NFA)**.

What the trouble is when the destination is not settled, and how to fix it, is handled in the chapters ahead.

## The Road Ahead

| Chapter | Contents |
| --- | --- |
| [Chapter 02](02-regex-to-nfa.md) | Build an NFA from the regular expression `a(a\|b)*bb` |
| [Chapter 03](03-nfa-to-dfa.md) | Convert it into a form where the destination is settled on a single one (a DFA) |
| [Chapter 04](04-minimize.md) | Minimize the number of states of the DFA |
| [Chapter 05](05-subset.md) | The implementation part begins here. Decide the range of regular expressions we handle |
| [Chapter 06](06-parse-nfa.md) | Read a pattern and turn it into an NFA |
| [Chapter 07](07-dfa-match.md) | Turn it into a DFA, decide matches, and finish it as a command |
