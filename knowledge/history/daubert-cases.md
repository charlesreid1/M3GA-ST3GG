# Steganography and Daubert / evidentiary standards

Steganalysis has appeared in US federal court cases since the early
2000s. Its admissibility hinges on Daubert v. Merrell Dow
Pharmaceuticals (1993), which requires expert testimony to rest on
scientifically valid methodology.

## The Daubert factors

Daubert (1993) established a five-factor test for admissibility of
expert scientific testimony:

1. Is the theory testable?
2. Has it been peer-reviewed?
3. What is the known or potential error rate?
4. Are there standards controlling the technique's operation?
5. Is the technique generally accepted in the relevant scientific
   community?

## Application to steganalysis

Chi-square (Westfeld-Pfitzmann 1999), RS analysis (Fridrich 2001),
and SPA (Dumitrescu 2003) have all been used as expert evidence in
US federal cases:

- **Peer-reviewed**: yes, all three are published in international
  refereed venues.
- **Error rate**: quantified in the original papers (false-positive
  rates on clean cover sets, false-negative rates at varying
  embedding rates).
- **Testability**: yes — cover sets exist, results are reproducible.
- **Standards**: less clear. There's no NIST standard for
  steganalysis; tools like `stegdetect`, StegExpose, and Aletheia
  are the de facto references.
- **General acceptance**: yes for chi-square/RS/SPA in the
  steganalysis community; modern ML-based methods are still
  contested.

## Notable cases

Specific court cases involving steg evidence:

- **US v. Doe** (early 2000s) — jsteg detection cited as evidence of
  hidden communication.
- Various child-exploitation cases where steg-encoded content has
  been used to hide evidence within otherwise-benign carrier files.

These are cited via secondary sources; ST3GG's KR does not carry
per-case citations. This is a summary framing, not a legal reference.

## Why this matters for tool builders

If a stego tool's output is going to be scrutinized (in a research
publication, a forensic report, a court proceeding), Daubert-style
questions apply to the *toolchain*, not just the technique:

- Are the tool's detection heuristics documented?
- What is the false-positive rate on clean images?
- Is the tool's source available for adversarial review?

ST3GG's design deliberately makes detection tools inspectable
(source-visible probes, explicit thresholds, per-record error-rate
notes where known). Tier 2's [[detection/*]] READMEs are the
place to record that discipline.

## Sources

- Daubert v. Merrell Dow Pharmaceuticals, 509 U.S. 579 (1993)
- [[fridrich-2001-rs]] — quantified error rates
- [[dumitrescu-2003-spa]] — quantified error rates
- [[westfeld-pfitzmann-1999-chi2]] — original chi-square attack
