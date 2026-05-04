
# debh - Debian Package Snapshot Manager

**Git-like version control for your Debian system.**

<p>
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT" />
  </a>
  <a href="https://www.debian.org/">
    <img src="https://img.shields.io/badge/Built%20for-Debian-red?logo=debian&logoColor=white" alt="Built for Debian" />
  </a>
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python 3.11+" />
  </a>
</p>

---

## The Problem

Every Debian user has been there:

```bash
sudo apt upgrade
# → Something breaks
# → Hours of debugging with no easy way back
```

**debh** gives you the safety net you always wished for.

## Features

- **Snapshot** — Capture your complete package state instantly
- **Restore** — Roll back to any previous state safely
- **Diff** — Compare snapshots and see exactly what changed
- **List / Show** — Browse and inspect all your snapshots
- Dry-run support for safe testing
- Lightweight and fast

## Quick Start

```bash
# 1. Save your current working state
sudo debh snapshot before-upgrade

# 2. Do risky operations
sudo apt update && sudo apt dist-upgrade

# 3. Something broke? Roll back instantly
sudo debh restore before-upgrade
```

## Installation

### From Source (Recommended)

```bash
git clone https://github.com/Abdev314/debh.git
cd debh

# Create virtual environment
python3 -m venv env
source env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install debh system-wide
sudo ln -sf $(pwd)/cmd/debh/main.py /usr/local/bin/debh
sudo chmod +x /usr/local/bin/debh
```

### Requirements

- Debian 11 (Bullseye) or newer
- Python 3.11+
- Root/sudo access (required for restore)

## Commands

| Command          | Description                        | Example                        |
|------------------|------------------------------------|--------------------------------|
| `snapshot`       | Create a new snapshot              | `debh snapshot before-nginx`   |
| `list`           | List all snapshots                 | `debh list --verbose`          |
| `diff`           | Compare two snapshots              | `debh diff clean broken`       |
| `restore`        | Restore a snapshot                 | `debh restore before-nginx`    |
| `show`           | Show details of a snapshot         | `debh show my-snapshot`        |
| `rm`             | Delete a snapshot                  | `debh rm old-snapshot`         |
| `info`           | Show debh information              | `debh info`                    |

**Tip:** Use `--dry-run` with restore to preview changes.

## Examples

### Before a major upgrade

```bash
debh snapshot stable-working
sudo apt dist-upgrade -y

# If issues arise:
debh restore stable-working
```

### After installing experimental packages

```bash
debh snapshot clean
sudo apt install build-essential docker.io postgresql-15

# Want to go back later?
debh restore clean
```

### See what changed

```bash
debh diff before after
```

**Sample output:**

```
📊 Comparing snapshots:
   'before' (2026-05-03 20:53:18)
   'after'  (2026-05-03 20:55:22)

Total packages: 3619 → 3641

➕ Added (22):
   + docker.io = 20.10.24
   + postgresql = 15.3-1
   ...

```

## How It Works

debh stores snapshots in `/var/lib/debh/snapshots/` as simple JSON files containing package names and versions.

When restoring, it intelligently uses `apt install --allow-downgrades` to bring your system back to the exact saved state.



## Project Structure

```bash
debh/
├── cmd/debh/main.py          # CLI entrypoint
├── internal/
│   ├── debian/               # apt/dpkg integration
│   └── snapshot/             # core snapshot logic
├── pkg/models/               # Data models
└── /var/lib/debh/snapshots/  # Storage location
```

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

## License

[MIT License](LICENSE) — Free to use, modify, and distribute.




