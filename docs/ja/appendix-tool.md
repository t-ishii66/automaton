# 付録. 小さな正規表現ツールを作る

![分かれ道の目印を見て道を選ぶBobとAlice、草むらのウサギ](img/alice-bob-appendix-ll1.png)

[01](01-automaton.md)〜[04](04-minimize.md) で追った手順を順に繋ぐと、
そのまま動くパターンマッチツールになる。ここではそれを実際に作る。

扱えるのは `|`（選択）、`( )`（括弧）、`*`（繰り返し）、そして文字を並べた連接だけ。
`+` も `?` も `.` も文字クラスも無い。それでも正規表現の骨格はこれで揃っている。

## 使う

パターンとテキストを渡すと、一致するかどうかを答える。

```
$ python3 -m automaton 'a(a|b)*bb' abb ab aabb ababb bb
match     'abb'
no match  'ab'
match     'aabb'
match     'ababb'
no match  'bb'
```

テキストを渡さなければ標準入力から読むので、grep のようにも使える。

```
$ printf 'abb\nab\naabb\nxyz\nababb\n' | python3 -m automaton 'a(a|b)*bb'
abb
aabb
ababb
```

## 全体の流れ

![ツールの処理の流れ](img/tool-pipeline.svg)

本編の各章が、そのまま 1 つの部品になっている。

| 段階 | 本編 | ファイル |
| --- | --- | --- |
| 正規表現を読む | （この付録） | `automaton/regex.py` |
| NFA を作る | [02](02-regex-to-nfa.md) | `automaton/nfa.py` |
| DFA にする | [03](03-nfa-to-dfa.md) | `automaton/dfa.py` |
| 状態数を最小化する | [04](04-minimize.md) | `automaton/dfa.py` |
| 一致判定 | [04](04-minimize.md) | `automaton/dfa.py` |
| 繋いでツールにする | （この付録） | `automaton/__main__.py` |

外部ライブラリは使わない。Python の標準ライブラリだけで動く。

## 1. 正規表現を読む

本編では `a(a|b)*bb` の構造を人間が見て取っていたが、
ツールにするならここも機械にやらせる必要がある。

正規表現の演算子には**結合の強さ**があり、強い順に
`*`（繰り返し）、連接、`|`（選択）である。
たとえば `a|bb*` は `a` と `bb*` の選択であって、`(a|b)b*` ではない。

そこで、弱い演算子から順に 4 段階の規則として書き下す。

```
alt  -> cat { '|' cat }      選択      : 連接を | で並べたもの
cat  -> rep { rep }          連接      : 繰り返しを並べたもの
rep  -> atom { '*' }         繰り返し  : 要素に * が付いたもの
atom -> '(' alt ')' | 文字   要素      : 括弧でくくった選択、または 1 文字
```

`->` は「左辺はこういう形をしている」、`{ }` は 0 回以上の繰り返しを表す。
引用符付きの `'|'` `'*'` `'('` は正規表現に現れる文字そのもので、
引用符の無い `|`（`atom` の行）は規則の側の「または」である。

弱い規則が強い規則を呼ぶ形になっているので、上から順に読んでいけば
結合の強さどおりに入れ子が取れる。
`atom` が `alt` に戻っているのは括弧のためで、ここで入れ子が一段深くなる。

そして 4 つの規則が、そのまま 4 つの関数になる。

```python
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
        while self.peek() == "*":
            self.take()
            node = ("star", node)
        return node

    def atom(self):
        c = self.take()
        if c == "(":
            node = self.alt()
            if self.take() != ")":
                raise ValueError("')' expected")
            return node
        if c in "|*)":
            raise ValueError(f"unexpected {c!r}")
        return ("sym", c)
```

`atom` が `alt` を呼び戻すので、関数も再帰する。
この読み方を**再帰的下向き構文解析**という。

結果は入れ子のタプルになる。

```python
>>> from automaton.regex import parse
>>> parse("a(a|b)*bb")
('cat', ('cat', ('cat', ('sym', 'a'), ('star', ('alt', ('sym', 'a'), ('sym', 'b')))), ('sym', 'b')), ('sym', 'b'))
```

## 2. NFA を作る

[02](02-regex-to-nfa.md) の 4 つの規則を、取り出した構造にあてはめる。
`_build(nfa, node, s)` は「すでにある状態 `s` から `node` の分を作り足し、
到達した状態を返す」関数である。
②の連接は「`x` の終わりから `y` を作り足す」だけなので、この形にすると何もしなくてよい。

```python
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
```

③で使う `merge` は、状態 `drop` を状態 `keep` に統合する。
`drop` を指していた遷移をすべて `keep` に付け替えるだけである。

```python
    def merge(self, keep, drop):
        """Fold state `drop` into state `keep`."""
        if keep == drop:
            return
        self.edges[keep].extend(self.edges.pop(drop))
        for s, out in self.edges.items():
            self.edges[s] = [(sym, keep if t == drop else t) for sym, t in out]
```

最後に状態の番号を振り直す。統合で番号に欠番が出るうえ、
本編の図の `1, 2, 3, ...` は機械を通っていく順に振られているので、
初期状態から深さ優先でたどった順に付け直す（`automaton/nfa.py` の `_renumber`）。

```python
>>> from automaton.nfa import build, dump
>>> dump(build("a(a|b)*bb"))
 i -- a --> 1
 1 -- ε --> 2
 1 -- ε --> 4
 2 -- a --> 3
 2 -- b --> 3
 3 -- ε --> 2
 3 -- ε --> 4
 4 -- b --> 5
 5 -- b --> f
```

[02](02-regex-to-nfa.md) で手で組み立てた 9 本と、辺も状態の名前も一致している。

## 3. DFA にする

[03](03-nfa-to-dfa.md) の ε 閉包と、記号による遷移先の合併。
どちらも定義をそのまま書いただけである。

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

## できること・できないこと

| | |
| --- | --- |
| できる | `\|`（選択）、`( )`（括弧）、`*`（繰り返し）、連接 |
| できない | `+` `?` `.` `[ ]` `^` `$`、エスケープ `\`、後方参照 |
| 一致の仕方 | 文字列**全体**が一致するかどうか。部分一致の検索はしない |

`(`、`)`、`|`、`*` 以外の文字はすべて、そのまま 1 文字の記号として扱う。

## 確かめ方

`tests/test_pipeline.py` で次の 3 つを確認している。

- 各段階の結果が、本編の図・表と一致すること（NFA の 9 本、部分集合構成後の 5 状態、最小化後の 4 状態）
- Python の `re` モジュールと同じ判定になること。`a(a|b)*bb` について長さ 7 以下の全文字列で総当たり
- `a`、`ab`、`a*`、`(a|b)*`、`a|bb`、`(ab)*a`、`a(b|c)*d` でも `re` と一致すること

```
$ python3 -m pytest tests -q
```
