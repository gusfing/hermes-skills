# The three-level escape trap when injecting JS from Python

Session 2026-10-03, LinkedIn harvester. Cost: ~15 browser round-trips across
four distinct wrong turns, and a "verified" checker that was green on a broken
file.

## The trap

A regex or escape sequence passed through Python -> JS source -> JS string
literal -> `RegExp` crosses **four** transformations. Every layer eats one
level of backslash.

```
Python raw string  r"\d"     -> stays \d
  (write to a JS string literal)  "\d"  -> becomes  d   <-- lost here
      (RegExp gets)  d
```

Result: `/^(d+[w]*s*(reactions?|...)$/` ->
`Invalid regular expression: Nothing to repeat`.

## What I tried, in order, and why each failed

| attempt | rule applied | outcome |
|---|---|---|
| plain `"""..."""`, single `\d` | Python eats it | `\d` -> `d` in the JS source |
| `r"""..."""` + doubled `\\d` | doubled survives Python | JS saw `\\d` -> `RegExp` got `\` + `d` literal |
| `r"""..."""` + single `\d` | | **correct** for a *regex literal*, wrong for a *string literal* |
| bulk `\\\\` -> `\\` replace | "normalise it" | **stripped all 41 backslashes**, broke the file |

The pivot: stop guessing and **read the actual string value**. One `ast` walk
printing `repr()` of the constant settles in seconds what four edits could not:

```python
for n in ast.walk(ast.parse(open(f).read())):
    if isinstance(n, ast.Assign) and getattr(n.targets[0], 'id', '') == 'SCRAPE_OWN':
        js = n.value.value
        print(repr(js[js.index('const NOISE'):][:400]))   # see the real bytes
```

## The rule that actually holds

**Pick your escape level for where the string ENDS UP, not where it starts.**

- Regex written as a **JS regex literal** (`/^\d+/i`) -> Python `r"""..."""`
  with single backslashes. Nothing else consumes it.
- Regex built from a **JS string literal** (`new RegExp('^\\d+')`) -> the
  string literal is a second consumer, so it needs doubled backslashes on top.
- `\n` is the reverse of `\d`: in a raw string, `'\n'` is backslash-n and JS
  turns it into a newline; `'\\n'` is a literal backslash-n. **The same two
  choices are correct for one construct and wrong for the other.**

Avoid `new RegExp` with escapes entirely when you can: a regex **literal** in JS
has one fewer escape layer. `new RegExp(['a', 'b'].join('|'))` built from
single-quoted simple alternatives avoids the trap for a noise filter, which is
all it was ever for here.

## Adjacent trap in the same file

A `"""` docstring in my own checker terminated early, and a line continuation
with `and` is illegal Python. Both were in the *checker*, not the target — so
the checker itself needed `ast`-level validation before I could trust it.

## The checker did not catch any of this

`node --check` returned **PASS** on the file that threw
`Invalid regular expression`. Syntax was valid; a runtime `new RegExp(...)`
built from mangled bytes was not. See the SKILL.md section
"A parser PASS is not an execution PASS".

**Always confirm the real value before editing escapes again.**
