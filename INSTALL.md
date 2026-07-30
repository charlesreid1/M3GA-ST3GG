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

- Python 3.10+ (the repo's `vp/` venv is built against 3.10; `pyproject.toml`
  declares `>=3.9`, but the shipped venv is 3.10 and CI runs against 3.10+)
- `git`
- A working C toolchain if you enable the `jpeg` extra (`jpeglib` builds a
  native wheel on most platforms; on macOS this is Xcode CLT)

---

## Install from source (this fork)

```bash
git clone git@github.com:charlesreid1/M3GA-ST3GG.git
cd M3GA-ST3GG

# Create a venv in the repo root. The project's convention is a visible
# `venv/` (or the pre-existing `vp/`). Do not hide it in `.venv`.
python3 -m venv venv
source venv/bin/activate

# Editable install so local edits take effect without reinstalling.
pip install -e .              # core CLI only
pip install -e '.[mcp]'       # + MCP server (HTTP + stdio)
pip install -e '.[all]'       # everything: web UI, crypto, MCP, jpeg, pdf, metadata
```

After install, these entry points are on `$PATH` inside the venv:

```
stegg              # main CLI
stegg-web          # NiceGUI web UI  (requires the [web] or [all] extra)
stegg-mcp          # MCP server, HTTP transport   (requires [mcp] or [all])
stegg-mcp-stdio    # MCP server, stdio transport  (requires [mcp] or [all])
```

Smoke test:

```bash
stegg --help
pytest -q -m "not slow"
```

### If you add a new top-level module

`pyproject.toml` pins the list of top-level modules under
`[tool.setuptools] py-modules = [...]`. Adding a new top-level `.py` module
requires editing that list **and** rerunning `pip install -e .` — editable
mode does not auto-discover new modules.

### Optional extras (what each one pulls in)

| Extra       | Adds                                             |
|-------------|--------------------------------------------------|
| `web`       | `nicegui`, `fastapi` — needed for `stegg-web`    |
| `web-legacy`| `streamlit` — legacy Streamlit UI                |
| `crypto`    | `cryptography` — enables AES-256-GCM Ghost Mode  |
| `mcp`       | `mcp`, `uvicorn`, `starlette` — MCP server       |
| `jpeg`      | `jpeglib` — F5 JPEG DCT encode/decode            |
| `metadata`  | `piexif` — EXIF writing                          |
| `pdf`       | `pypdf` — PDF authoring                          |
| `all`       | everything above                                 |

---

## Browser-only (no install)

The client-side UI in `index.html` runs with zero dependencies:

```bash
open index.html      # macOS
xdg-open index.html  # Linux
```

Everything runs in the browser. No Python required.

---

## Uninstall

```bash
pip uninstall stegg
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
