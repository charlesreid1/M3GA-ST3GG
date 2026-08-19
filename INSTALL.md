# Installing M3GA-ST3GG (this fork)

This repository is [`charlesreid1/M3GA-ST3GG`](https://github.com/charlesreid1/M3GA-ST3GG),
a fork of upstream [`elder-plinius/st3gg`](https://github.com/elder-plinius/st3gg).

**This fork is not published to PyPI.** `pip install stegg` pulls the upstream
package, not this one. To use the code in this repo, install it locally from
source in editable mode as shown below.

If you want the upstream release instead, see [Upstream (elder-plinius/st3gg)
via PyPI](#upstream-elder-pliniusst3gg-via-pypi) at the bottom — it's a
different project.

---

## Requirements

- Python 3.10 – 3.12 (declared as `requires-python = ">=3.10,<3.13"`)
- `git`
- A working C toolchain if you enable the `jpeg` extra (`jpeglib` builds a
  native wheel on most platforms; on macOS this is Xcode CLT)

---

## Install from source (this fork)

```bash
git clone git@github.com:charlesreid1/M3GA-ST3GG.git
cd M3GA-ST3GG

# Create a venv in the repo root. The project's convention is a visible
# `venv/`. Do not hide it in `.venv`.
python3 -m venv venv
source venv/bin/activate

# Editable install. MCP is core — no extra needed for the servers.
pip install -e .              # core CLI + MCP servers
pip install -e '.[all]'       # + web UI, crypto, jpeg, pdf, metadata
```

After install, these entry points are on `$PATH` inside the venv:

```
stegg                # main CLI
stegg-web            # NiceGUI web UI  (requires the [web] or [all] extra)
m3gast3gg-mcp        # MCP server; `--transport {stdio,sse,streamable-http}` (default: streamable-http)
m3gast3gg-mcp-stdio  # alias for `m3gast3gg-mcp --transport stdio`
```

`m3gast3gg-mcp` picks its transport from `--transport`:

| Transport         | When to use                                                    | Example                                              |
|-------------------|----------------------------------------------------------------|------------------------------------------------------|
| `stdio`           | Local clients that spawn the server themselves (Claude Desktop, opencode) | `m3gast3gg-mcp --transport stdio`         |
| `sse`             | Legacy MCP web transport (Server-Sent Events) at `/sse`         | `m3gast3gg-mcp --transport sse --port 8765`          |
| `streamable-http` | Modern HTTP transport at `/mcp` (**default**)                   | `m3gast3gg-mcp` or `m3gast3gg-mcp --transport streamable-http` |

Smoke test:

```bash
stegg --help
m3gast3gg-mcp --help
pytest -q -m "not slow"
```

### Optional extras (what each one pulls in)

| Extra       | Adds                                                        |
|-------------|-------------------------------------------------------------|
| `web`       | `nicegui`, `fastapi`, `streamlit` — needed for `stegg-web`  |
| `crypto`    | `cryptography` — enables AES-256-GCM Ghost Mode             |
| `jpeg`      | `jpeglib` — F5 JPEG DCT encode/decode                       |
| `metadata`  | `piexif` — EXIF writing                                     |
| `pdf`       | `pypdf` — PDF authoring                                     |
| `dev`       | `pytest`, `pytest-asyncio` — test suite                     |
| `all`       | everything above except `dev`                               |

---

## Browser-only (no install)

The client-side UI in `web/index.html` runs with zero dependencies:

```bash
open web/index.html      # macOS
xdg-open web/index.html  # Linux
```

Everything runs in the browser. No Python required.

---

## Uninstall

```bash
pip uninstall m3gast3gg
# and delete the venv:
deactivate && rm -rf venv
```

---

## Upstream (`elder-plinius/st3gg`) via PyPI

The upstream project is published to PyPI as `stegg`. **This is a separate
codebase** — if you install it you are not running this fork:

```bash
pip install stegg
pip install 'stegg[all]'
```

Upstream repo: https://github.com/elder-plinius/st3gg

Divergence between this fork and upstream is not tracked here; check `git log`
or the fork's PR history for what's changed.
