# Embedded JS in Python strings: three levels eat your backslashes

Measured 2026-10-04 in `/home/opc/kawaki-outreach/li_own_harvest.py`. Cost: five
patch iterations, one abandoned file, and a **false PASS from my own checker**.

## The three levels

A regex written in Python source, sent as JS source, evaluated into `RegExp`:

```
Python source   '\\d'   ->  Python string  \d   ->  JS literal '\d'  ->  RegExp  \d   OK
Python source   '\d'    ->  Python string  \d   ->  JS literal '\d'  ->  RegExp  d   WRONG
```

Level 1 is Python's own escape processing. Level 2 is the JS string literal
`'\d'`, which **also** consumes the backslash. Level 3 is `RegExp`, which needs
the backslash back. Two consumers, one backslash.

Requirement per token:

| token | in Python source | why |
|---|---|---|
| `\d`, `\w`, `\/`, `\b` | `'\\d'` | consumed twice, RegExp needs it |
| `\n` in JS string data | `'\\n'` | must survive as JS `\n`, become a real newline at eval |
| comment text | plain | a `\n` in a comment becomes a real newline and breaks the JS |

**Do not reach for `r"""`.** A raw string sends `\\d` through untouched, so JS
receives `'\\d'`, the literal holds `\\d`, and `RegExp` compiles `\\d` as a
literal backslash followed by `d` — matching nothing, silently. The failure
observed was `/https?:\\/\\//` (SyntaxError) and before that
`/^(d+[w]*s*...` — "Nothing to repeat".

**Do not do a blanket `\\\\ -> \\` sweep either.** It silently fixes regexes
while breaking the tokens that needed doubles. This was my mistake: I removed
all 41 double escapes in one pass, which was exactly backwards for regexes.

Rule of thumb: **regex escapes double; JS string escapes that must survive
parsing double; everything else single.** Decide per token, then verify.

## The guard that lied

`node --check` parses. It does **not** execute. `new RegExp(badPattern)` is a
runtime construction, so:

```javascript
new RegExp('^(d+[w]*s*(foo)$/i')   // syntactically valid JS, throws at runtime
```

`node --check` returns **0**. A checker built on `--check` PASSes a file that
throws the instant it runs.

Fix — evaluate, don't parse:

```bash
node -e "new RegExp(<pattern>)" || echo BAD
```

Extract the pattern from the Python constant via `ast`, `JSON.stringify` it into
a JS harness, and actually construct the RegExp.

## Verify the value, not the source

Do not eyeball `repr()` of the Python string and reason about JS. Print what
the *JS* will receive:

```python
import ast, json
for n in ast.walk(ast.parse(src)):
    if isinstance(n, ast.Assign) and any(getattr(t,'id','')=='SCRAPE' for t in n.targets):
        print(json.dumps(n.value.value[i:i+200]))   # json.dumps == JS sees this
```

`json.dumps` is the same escaping JS string literals use, so the printout *is*
the JS source. A `/^(d+[w]*s*` in that output is the bug, visible.

## Own bugs in the checker itself

Two, both worth expecting:

1. Slicing `SCRAPE = ` off the constant **swallowed the opening quote**, so a
   good file reported a false SyntaxError. Slice by `ast` node, not by string.
2. A `"""` inside the checker's own docstring terminated it early.

A guard that cannot fail is not a guard; neither is one that fails on correct
code. Test both directions: inject a known-bad pattern and confirm it FAILS.

## Prefer no escaping at all

Where the pattern is simple enough, build it so backslashes never appear:

```javascript
new RegExp('^(' + ['Feed post','Suggested','notification'].join('|') + ')+')
```

Or drive from CSS selectors instead of regex. Each removed escape is one level
that can disagree.

## Debugging order that worked

1. Print `json.dumps(python_string_value)` — see the JS JS will get
2. `node --check` the extracted JS — catches quoting, not regex validity
3. `node -e "new RegExp(...)"` — catches the class `--check` misses
4. Only then edit the Python source