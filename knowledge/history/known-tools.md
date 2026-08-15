# Known tool lineage

A rough chronological map of the tools every stego / steganalysis
person eventually encounters. ST3GG's `external_tools.json`
carries the record-level detail; this file is the narrative.

## The tools, in order

### 1993 — jsteg (Derek Upham)

The first widely-used JPEG steganography tool. LSB replacement over
nonzero DCT AC coefficients. Referenced as the target of the
chi-square attack. See [[image-jsteg]].

### 1998 — jphide / jphs (Allan Latham)

jsteg's successor. Passphrase-selected embedding order over JPEG
DCT coefficients. `stegdetect` was tuned to catch jphide too.

### 1999 — chi-square attack (Westfeld & Pfitzmann)

The first statistical attack. Killed jsteg's plausible deniability
in one paper. See [[detection/chi-square]].

### 2001 — F5 (Andreas Westfeld)

Matrix encoding + shrinkage handling → chi-square-resistant JPEG
steg. The reference technique for a generation of research. See
[[image/f5]].

### 2001 — OutGuess (Niels Provos)

Statistical-preserving JPEG steg — first pass hides, second pass
corrects the DCT histogram. See [[image/outguess]].

### 2001 — RS analysis (Fridrich, Goljan, Du)

Spatial-domain LSB detector with rate estimation. Killed casual
pixel-LSB. See [[detection/rs-analysis]].

### 2002 — stegdetect (Niels Provos)

Signature-scan detector for jsteg, jphide, and F5. Still in use;
the "does this JPEG smell wrong" first-line tool. See
[[tool-stegdetect]].

### 2003 — steghide (Stefan Hetzl)

Combined JPEG/BMP/WAV steg with AES-256 payload encryption and a
graph-matching-based embedding strategy. Enough distinct that no
other tool reads its format — see [[myth-steghide-reads-outguess]].

### 2003 — SPA (Dumitrescu, Wu, Wang)

Sample-pairs analysis, sensitive at sub-1% embedding. See
[[detection/sample-pairs]].

### 2005 — WS (Ker)

Weighted-stego analysis — combines multiple statistical tests. See
[[ker-2005-ws]].

### 2007 — nsF5

F5 without shrinkage handling → simpler, more capacity, defeats
some F5-specific detectors.

### 2010 — HUGO (Pevný, Filler, Bas)

"Highly Undetectable steGO" — first cost-function-driven adaptive
embedding scheme. Set the direction for the next decade.

### 2013 — S-UNIWARD (Holub & Fridrich)

Spatial-domain UNIversal WAvelet Relative Distortion. Modern SOTA
for JPEG-domain stego.

### 2013 — zsteg (Andrey "Zed" Zaikin)

Ruby-based multi-technique PNG steganalysis. `zsteg -a` runs a full
sweep. See [[tool-zsteg]].

### 2015 — StegExpose (Boehm)

Ensemble multi-detector Java tool. `stegexpose <dir>` runs chi²,
RS, sample-pairs on a corpus. See [[tool-stegexpose]].

### 2015 — Aletheia (Daniel Lerch)

Modern ML-based steganalysis toolkit. Deep-learning detectors for
F5, jsteg, S-UNIWARD, and beyond. See [[tool-aletheia]].

### 2019 — Alaska2 (kaggle.com)

Steganalysis-as-Kaggle-competition. Set the modern benchmark for
what "good enough" detection looks like. See
[[alaska2-competition]].

### 2024 — Unicode tag prompt injection

Not a stego tool but a stego-adjacent attack. Riley Goodside and
Joseph Thacker demonstrate tag-block payload injection into LLM
inputs. See [[greenberg-2024-tag-injection]] and
[[text/invisible-ink]]. Vendor mitigations are still landing in
2025-2026.

## Why this list

Each row is a name someone will ask about at some point:
"what's the difference between jsteg and jphide?" — the answer is
"jsteg is 1993, jphide added passphrase permutation in 1998, both
are chi-square-detectable, F5 replaced both." Having this lineage
in narrative form makes those answers fast.

## Sources

- Individual records per row: see `bibliography.json` and
  `external_tools.json` in the KR.
- [[st3gg-field-guide]] — ST3GG-side commentary
