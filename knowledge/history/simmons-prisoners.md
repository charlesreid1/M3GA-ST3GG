# Simmons 1983 — the Prisoners' Problem

Gustavus Simmons's 1983 paper "The Prisoners' Problem and the
Subliminal Channel" is the canonical problem statement for
steganography. The framing:

> Alice and Bob are prisoners plotting to escape. They communicate
> only through Willie the warden, who reads every message. Willie
> allows communication as long as it appears innocent. If he detects
> a suspicious message, he throws them in solitary and the plot
> fails.
>
> How do Alice and Bob agree on a plan without Willie noticing?

## Why it matters

Simmons's framing separates the two axes of hiding that later
research kept collapsing:

- **Confidentiality**: even if Willie sees the message, he cannot
  read the plan.
- **Undetectability**: Willie does not know a hidden message is
  present at all.

Encryption alone solves confidentiality; steganography solves
undetectability. Both together: encryption of a hidden payload.
The framing dictates that steg must *not* look like ciphertext —
which is exactly why "encryption alone makes steg undetectable" is
false. See [[myth-encryption-hides-steg]].

## The subliminal-channel discovery

Simmons's original paper was NOT about images or text. It was about
finding a covert channel in *digital signature schemes* (specifically,
DSA-style signatures with a random component). The random component,
Simmons showed, could be replaced with a message-carrying value that
still validated as a real signature — a "subliminal channel" hidden
in the signature bytes themselves.

That specific technique inspired later work in "watermarking" random
values in cryptographic protocols. The Prisoners' Problem framing —
Alice, Bob, Willie — became the reference framing for all
subsequent stego work.

## Modern echo

Every modern stego paper's threat model traces back to this framing:

- **Alice** = sender (steg encoder)
- **Bob** = receiver (steg decoder)
- **Willie** = detector (steganalyst)

The "warden's goal" is now formalized as a decision-theoretic problem
(hypothesis testing between "cover only" vs "cover + payload").

## Sources

- [[simmons-1983-prisoners]] — the paper
- [[anderson-petitcolas-1998-survey]] — Anderson & Petitcolas 1998
  survey that popularized Simmons's framing to a broader audience
- [[st3gg-field-guide]] — ST3GG's implicit adoption of the framing
