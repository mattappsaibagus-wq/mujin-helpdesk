# ITSS PRO TOOL

IT troubleshooting console and knowledge base for **Debian 13**, **Windows 11**, and **macOS**.

Built for IT support engineers working FreshService tickets. Search a bundled
offline knowledge base of troubleshooting articles, pull the diagnosis and the
commands to run on the affected machine, and generate a FreshService ticket
block you can paste straight in — all from a single tool with a **CLI** and a
password-protected **web console**.

## Highlights

- 🔍 **Fast search** across 50+ articles by symptom, title, keyword, or OS
- 🖥️ **Guided diagnostics** — print-only commands to run on the affected machine (never auto-executed)
- 📋 **FreshService ticket templates** — draft a ticket and **save** it to come back to
- 🌐 **Web console** — modern UI, OS panels, live search, gated by a shared password
- ⚙️ **CLI** for terminal-first support work

## Web console

Run it, then open http://localhost:8000 and sign in with the shared access code.

```bash
python mhd.py web
# or
python -m helpdesk.web.run
```

### Configuration (environment variables)

| Variable | Purpose | Default |
|----------|---------|---------|
| `ITSS_PASS` | Shared access code for the web console | `itss-pro-tool` |
| `SECRET_KEY` | Signs session cookies (use a long random value) | dev key |
| `PORT` | HTTP port | `8000` |
| `DEBUG` | `1`/`true` enables Flask debug mode | off |

See `.env.example`. Always set `ITSS_PASS` and `SECRET_KEY` before deploying.

### What's behind the login

- **Console** — search box, per-OS stat strip, and Debian / Windows / macOS panels.
- **Browse** — every article for one OS, grouped by category.
- **Article** — symptoms, causes, diagnosis, resolution, copy-paste commands, sources, related.
- **New ticket** — pick OS + symptom → generates a FreshService block → **Save** it.
- **Saved tickets** — your drafts, with copy and delete.

## CLI

```bash
python mhd.py                    # overview + help
python mhd.py list <os>          # articles for a system (debian/windows/mac)
python mhd.py search "apt lock"  # fuzzy search (add --os windows to filter)
python mhd.py show deb-apt-lock  # full article
python mhd.py cat <os> <cat>     # articles in one category
python mhd.py diag "apt lock"    # print-only diagnostic commands
python mhd.py ticket <os>        # FreshService ticket template
python mhd.py sources <id>       # reference links
python mhd.py web                # start the web console
```

## Knowledge base

Structured YAML articles under `knowledge/<os>/<category>.yaml`. Each article
carries symptoms, causes, diagnosis steps, resolution, runnable commands, and
authoritative source links — the same data powers both the CLI and the web app.

Add a new article by dropping a YAML entry into the right OS/category file; it
appears in search, browse, and the ticket generator with no code changes.

Article schema:

```yaml
- id: deb-apt-lock
  title: "E: Unable to acquire the dpkg frontend lock"
  os: debian                 # debian | windows | mac
  category: packages
  severity: common           # common | moderate | severe
  keywords: [apt, dpkg, lock, install]
  symptoms: ["apt says it cannot get the lock"]
  causes: ["another apt is running"], ["previous command interrupted"]
  diagnosis: ["pgrep -a apt"], ["ls -l /var/lib/dpkg/lock-frontend"]
  resolution: ["sudo dpkg --configure -a"]
  commands: ["pgrep -a apt", "sudo apt-get update"]
  sources:
    - {name: "Debian Wiki", url: "https://wiki.debian.org/DpkgLock"}
  related: [deb-apt-install-fail]
```

## Development

```bash
pip install -r requirements.txt   # Flask + PyYAML
pytest tests/                     # run the test suite
```

## License

Provided as-is for internal IT support use.