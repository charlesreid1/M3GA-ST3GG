# CTF pattern: prompt injection via steganography

Payload hidden in a text (or image, or emoji) that is *invisible*
to a human user reviewing the message, but *visible* to an LLM
that tokenizes the raw bytes. The 2024–2026 attack wave.

## The pattern

Not a traditional steg CTF category — a class of AI-security
challenges where the solver must:

- Recognize that a benign-looking text or image contains a hidden
  prompt.
- Extract it (or realize what the LLM under test would receive).
- Show how a defender should detect and strip it.

## The techniques

- **[[text-invisible-ink]]** — Unicode tag block (U+E0000..U+E007F).
  ASCII payload maps 1:1 into tag codepoints, invisible to fonts,
  visible to LLM tokenizers. See [[greenberg-2024-tag-injection]].
- **[[emoji-tag-sequence]]** — same idea riding a base emoji (🏴).
- **[[text-zero-width]]** — zero-width Unicode chars carrying a
  bit-encoded prompt.
- **[[compose-text-jailbreak]] / [[compose-unicode-tag-jailbreak]]
  / [[compose-image-jailbreak]]** — ST3GG's composers that stack
  multiple techniques for prompt injection payloads.
- **Image-in-image LSB with prompt payload** — the LLM has vision;
  the prompt hides in the LSB plane; some multimodal models
  read raw pixel data and can be steered by it.

## Solving

1. **Byte-inspect the message**. Run `text_core.detect_unicode_steg`
   or `stegg_text_steg_message`. It catches every text-layer
   invisible-payload technique.
2. **Decode with the corresponding tool** — `stegg_text_decode` with
   the detected method.
3. **Test against a real LLM** (in a sandbox) — the payload should
   read as ASCII to the model.

## Defensive framing

CTFs of this genre are usually authored by defenders looking to
train detection heuristics. The exercise is:

- Given N model inputs, identify which contain hidden prompts.
- Propose a sanitizer / filter.
- Test the sanitizer against the ST3GG composer suite.

## The record

See [[ctf-unicode-tag-jailbreak]] for the CTF-genre record.

## Sources

- [[greenberg-2024-tag-injection]] — the 2024 tag-injection wave
- [[unicode-tag-block]] — Unicode tag block spec
- [[st3gg-field-guide]] — ST3GG's composer integration
