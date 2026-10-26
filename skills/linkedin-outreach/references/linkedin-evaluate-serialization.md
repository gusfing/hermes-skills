# `evaluate()` Returns Serialized DOM, Not Live Elements

## Symptom

`element.getAttribute is not a function`, `element.click is not a function`, or `Cannot read properties of undefined (reading 'getAttribute')` when trying to operate on the result of an `evaluate()` call.

## Cause

Camofox's `/evaluate` endpoint serializes the returned JavaScript value to JSON. A DOM element returned from evaluate is serialized to `{}` (an empty object) — it loses all methods and properties. You cannot call `.getAttribute()`, `.click()`, `.focus()`, etc. on the returned value.

## Diagnose

```javascript
// This CRASHES — element is serialized to {}
const element = await evaluate('document.querySelector("button")');
element.getAttribute('href');  // TypeError: element.getAttribute is not a function
element.click();               // TypeError: element.click is not a function

// This WORKS — do everything inside the evaluate expression
await evaluate(`(function() {
  const btn = document.querySelector('button[data-test-action="connect"]');
  if (btn) { btn.click(); return { clicked: true }; }
  return { clicked: false };
})()`);
```

## Fix

Do all DOM operations inside a single `evaluate()` expression. The expression runs in the browser context where DOM elements are live. Return a plain result object (string, boolean, number) — not a DOM element:

```javascript
// CORRECT pattern: click + return result object
const result = await evaluate(`
  (() => {
    const buttons = document.querySelectorAll('button');
    for (const btn of buttons) {
      const text = (btn.innerText || btn.textContent || '').trim();
      if (text === 'Connect' && btn.offsetParent !== null && !btn.disabled) {
        btn.click();
        return { clicked: true, selector: 'button[text=Connect]' };
      }
    }
    return { clicked: false, reason: 'not_found' };
  })()
`);
// result is { clicked: true } or { clicked: false, reason: 'not_found' }
// — a plain object, safe to use
```

## Anti-pattern to avoid

Getting an element from evaluate, then trying to operate on it with a second evaluate call:

```javascript
// WRONG — two round trips, second one fails on serialized element
const btn = await evaluate('document.querySelector("button")');  // returns {}
await evaluate('(function(btn) { btn.click(); })(' + JSON.stringify(btn) + ')');  // crashes
```

## Why this matters for LinkedIn scripts

Connect button, Message button, Send button, Post button, and textarea operations must all be done in a single evaluate expression. The button-finding code must return a result object, not the button element.
