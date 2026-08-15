# stealth_class

The ST3GG-record taxonomy for **how perceptible a technique is to a
casual reader / viewer**. Distinct from *statistical* stealth (which
is what chi-square / RS / SPA measure) and from *transport* survival.

## The three classes

- **`invisible`** — the stego is not perceptible to a casual human.
  Zero-width chars, variation selectors, invisible-ink tag chars,
  1-bpc LSB in a natural cover, F5 with a small payload.
- **`prose-like`** — the stego looks like normal-shape prose or a
  normal-shape image, but a careful reader could spot it if they
  knew what to look for. Cyrillic homoglyphs, capitalization,
  skintone-modifier bits, PVD in a busy cover.
- **`visibly-perturbed`** — the stego is present *and visible*, but
  the payload is not immediately readable. Mathbold letters, braille
  block, emoji-substitution (🔴/🔵), directional-override runs.

## Usage in the KR

Every technique record carries `stealth_class` in its
`technical_body`. `stegg_search_records` and `stegg_explain_pipeline`
both accept `constraint=<class>` to filter by this axis.

Examples:

```python
stegg_explain_pipeline(
    goal="hide 800B in prose that reads normally",
    carrier="text",
    constraint="prose-like",
    transport="slack_paste",
)
# → text-cyrillic-homoglyph, text-cjk-homoglyph, text-capitalization
```

## The three-axis view

Every stego technique is characterized on three orthogonal axes:

1. **`stealth_class`** — human-perceptual stealth (this file).
2. **Statistical stealth** — chi-square / RS / SPA resistance. Not a
   discrete field; discussed per-technique in [[detection/*]].
3. **Transport survival** — via `survival.json` records per
   (technique, transport) pair.

A technique can be `invisible` (perceptually) but statistically loud
(LSB fires chi-square). A technique can be `visibly-perturbed`
(perceptually) but statistically silent (mathbold has no
LSB-histogram signature at all). They're independent axes.
