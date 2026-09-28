# 07. DFA にして判定する

![完成した仕分け機にカードを通し、結果を喜ぶBobとAlice](img/alice-bob-07-dfa-match.png)

[06](06-parse-nfa.md) でパターンから NFA を作った。
ここからは [03](03-nfa-to-dfa.md)、[04](04-minimize.md) の手順をコードにして、
最後にコマンドとして繋ぐ。

## 3. DFA にする

[03](03-nfa-to-dfa.md) の ε 閉包と、記号による遷移先の合併。
どちらも定義をそのまま書いただけである。

`closure` という名前で定義した関数は、第 2 引数 `states` に渡された状態から始めて、
ε で行ける状態を全部集め、`out` に入れていく。
`states` は出発点で、初期状態 1 つのこともあれば、`move` が返した集合のこともある。
`out` は `set(states)` で始めるので、渡した `states` はそのまま結果に残る。

その `out` のうち、**まだ ε の先を見ていないもの**が `todo` である。
`todo` は `out` の一部であって、NFA の未調査の状態ではない。
取り出しては ε の先を `out` に足し、`todo` が空になったら、もう伸ばせる先が無い。
`a(a|b)*bb` の NFA で `closure(nfa, [1])` を呼ぶと、3 手で止まる。

![closure の動き](img/tool-closure.svg)

同じ状態を二度 `todo` に積まないので、ε が輪になっていても止まる。
`a(a|b)*bb` の ε 遷移（`1→2` `1→4` `3→2` `3→4`）に輪は無いが、
`(a*)*` のように `*` が入れ子になると ε だけの輪ができる。
そのときも、2 周目の行き先は `out` にもう入っているので `todo` に積まれず、そこで止まる。

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

コードの側から見ると、`closure` がやっているのは 2 つの入れ物の出し入れである。

![closure のループが何をしているか](img/tool-closure-code.svg)

`move` は逆に、ε を 1 本も辿らず、記号 1 つ分だけ進む。
集合の中のどの状態から出ている矢印でも、記号が一致すればその行き先を集める。

![move の動き](img/tool-move.svg)

記号で 1 歩進んでから ε で広げる、つまり `closure(move(...))` が、
次の `from_nfa` の 1 マスになる。

作成手順の (1)〜(3) がそのまま `from_nfa` になる。
未処理の集合を `todo` に積んでおき、空になったら終わり、というだけである。

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

DFA の状態は `frozenset`（NFA の状態の集合）で表す。
集合そのものを辞書のキーにできるので、
「もう出てきた集合かどうか」の判定が `in` で済む。

出発集合は `nfa.start` の ε 閉包、受理状態は `nfa.accept` を含む集合。
[03](03-nfa-to-dfa.md) の 2 つの決まりが、最初の行と `accept = ...` の行に
そのまま出ている。

`todo` が空になるまで、集合を 1 つ取り出しては記号ごとに行き先を求める。
その様子が次の表である。

![from_nfa の動き](img/tool-subset.svg)

5 回回ったところで `todo` が空になり、集合は 5 つ出揃った。これが DFA の状態である。
丸と矢印で描き直すと、[03](03-nfa-to-dfa.md) で手で作ったものと同じ機械になる。

![出揃った 5 つの集合を、そのまま状態にした DFA](img/tool-dfa.svg)

遷移表の形でも確かめておく。

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

## 4. 状態数を最小化する

[04](04-minimize.md) の分割の繰り返し。
各状態について「どの記号で遷移できるか」と「その遷移先がどの集合に属するか」を
組にした鍵を作り、鍵が違えば別の集合に分ける。
手順の (2) が前半、(3) が後半にあたるので、実装ではこの 2 つを 1 つの鍵にまとめている。

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

`where` は「その状態が今どの集合にいるか」の対応表である。
集合が分かれると `where` が変わり、それによってさらに別の集合が分かれることがある。
だから分割が起きなくなるまで繰り返す。

実際に 2 回で終わる様子を追うと、こうなる。

![minimize の動き](img/tool-minimize.svg)

第 1 回で 2 組が 4 組になり、第 2 回は組の数が変わらなかったので終了する。
鍵に「どの記号で行けるか」が入っているので、`b` の行き先を持たない `i` は
最初の回で自動的に分かれる。[04](04-minimize.md) の手順 (2) にあたるものが、
別の処理ではなく鍵の一部として効いている。

残った 4 つの組を、そのまま状態にするとこうなる。

![まとめ終わって 4 状態になった DFA](img/tool-dfa-min.svg)

遷移表の形でも確かめておく。

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

## 5. 一致判定

遷移表を 1 文字ずつ引くだけである。

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

探索も後戻りもない。入力長に比例した時間で終わる。

![accepts の動き](img/tool-accepts.svg)

変数 `s` が 1 文字ごとに 1 回だけ書き換わる。
[04](04-minimize.md) で手で追ったのと同じ経路である。

## 6. 繋いでツールにする

あとは 1〜5 を順に呼ぶだけである。

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

パターンの組み立ては最初の 1 回だけで、あとは何行来ても表を引くだけである。

## 通して動かす

[05](05-subset.md) で決めた範囲のパターンなら、どれでも同じ経路を通る。

```
$ python3 -m automaton 'a(a|b)*bb' ababb
match     'ababb'
$ python3 -m automaton '(ab)*c' ababc
match     'ababc'
$ python3 -m automaton 'a|bb' bb
match     'bb'
```

正しく動いていることは `tests/test_pipeline.py` で確かめている。

- 各段階の結果が本編の図・表と一致すること（NFA の 9 本、部分集合構成後の 5 状態、最小化後の 4 状態）
- いくつかのパターンについて、短い文字列を総当たりして Python の `re` と同じ判定になること

```
$ python3 -m pytest tests -q
```

---

これで、正規表現がどう動くのかを一通り見たことになる。
[01](01-automaton.md) で「行き先がただ 1 つに決まる機械なら、入力を 1 回なぞるだけでよい」
と書いたが、その機械を正規表現から機械的に作る道筋が、ここまでで全部つながった。

普段使っている正規表現エンジンも、内部でこれに近いことをしている。
ただし実装によっては DFA を作らず、NFA を後戻りしながら辿る。
[02](02-regex-to-nfa.md) で見た「試して駄目ならもう片方」の方式である。
そちらは後方参照のような DFA では表せない機能を扱える代わりに、
書き方によっては極端に遅くなることがある。
DFA にしてしまえばそれが起きない——というのが、[03](03-nfa-to-dfa.md) と
[04](04-minimize.md) でやったことの意味だった。
