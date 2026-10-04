# MUJIN HelpDesk — IT Troubleshooting Tool

IT troubleshooting knowledge base for **Debian 13**, **Windows 11**, and **macOS**.

## Overview

MUJIN HelpDesk is a comprehensive IT support tool designed to help IT support engineers quickly diagnose and resolve technical issues across different operating systems. The tool provides:

- **Fast search** across all troubleshooting articles
- **Copy-paste diagnostic commands** for system investigation  
- **FreshService-ready ticket templates** for efficient reporting
- **Both CLI and web interfaces** for different support workflows

## Key Features

### 🔍 Fast Search
- Search by symptom, title, keywords, or cause
- Filter by operating system (Debian/Windows/macOS)
- View full articles with symptoms, causes, diagnosis steps, and resolution

### 🖥️ Copy-Paste Diagnostics
- Pre-written commands for system investigation
- Safe to run (read-only or targeted fixes)
- Formatted for FreshService ticket pasting

### 📋 FreshService Integration
- Generate ticket templates with all necessary information
- Include environment details, collected diagnostics, and next steps
- Ready to paste into FreshService tickets

### 🌐 Web Dashboard
- Browse articles by OS and category
- Live search functionality
- Ticket template generator
- Responsive design for desktop and mobile

## Usage

### CLI Commands

```bash
# Show help
mhd

# List articles by OS
mhd list debian
mhd list windows
mhd list mac

# Search for articles
mhd search "apt lock"
mhd search "RDP connection" --os windows

# Show full article
mhd show deb-apt-lock

# Show articles in a specific category
mhd cat debian packages

# Generate diagnostic commands
mhd diag "apt lock"

# Generate FreshService ticket template
mhd ticket debian --symptom "apt update failed"

# Show source links
mhd sources deb-apt-lock

# Show configuration
mhd config

# Start web dashboard
mhd web
```

### Web Dashboard

Start the web dashboard:

```bash
python mhd.py web
```

Open your browser to http://localhost:5000

## Knowledge Base Structure

The tool includes **50+ articles** organized by operating system and category:

### Debian 13 (30 articles)
- **Packages**: apt/dpkg issues, GPG errors, held packages
- **Systemd**: service management, boot issues, networking
- **Permissions**: sudo, user groups, file permissions
- **Networking**: DNS, proxy, SSH, static IP
- **Storage**: disk full, LVM, fstab mounts

### Windows 11 (20 articles)
- **RDP/Remote**: connection issues, black screen, printer redirection
- **Network/Wi-Fi**: no internet, adapter issues, IP conflicts, VPN
- **Printers/Peripherals**: driver issues, spooler problems, network printers
- **Software**: winget/MS store install, legacy MSI, AV blocking
- **Accounts/Login**: locked out, admin access, domain join

### macOS (0 articles)
*(Planned for future releases)*

Each article includes:
- **Symptoms** users report
- **Causes** analysis
- **Diagnosis** steps to investigate
- **Resolution** steps to fix
- **Commands** to copy-paste
- **Sources** for authoritative documentation

## Development

### Requirements

```bash
pip install -r requirements.txt
```

### Testing

The tool includes basic testing infrastructure:

```bash
# Run basic tests
pytest tests/
```

### Adding New Articles

Add new articles by creating YAML files in the `knowledge/` directory:

```
knowledge/
└── <os>/
    └── <category>.yaml
```

Each article should follow this schema:

```yaml
- id: <unique-id>
  title: "Descriptive title"
  os: debian|windows|mac
  category: <category-name>
  severity: common|moderate|severe
  keywords: [keyword1, keyword2]
  symptoms:
    - "Symptom 1"
    - "Symptom 2"
  causes:
    - "Cause 1"
    - "Cause 2"
  diagnosis:
    - "Step 1"
    - "Step 2"
  resolution:
    - "Fix 1"
    - "Fix 2"
  commands:
    - "Command 1"
    - "Command 2"
  sources:
    - {name: "Source name", url: "https://..."}
  related: [other-article-id]
```

## License

This tool is provided as-is for internal MUJIN IT support use. Future enhancements and community contributions are welcome.

## Support

For issues or enhancements, contact MUJIN IT Support team.

## Quick Start

1. **Install dependencies:** `pip install -r requirements.txt`
2. **Test the tool:** `python mhd.py list debian` (or any command from help)
3. **Start web dashboard:** `python mhd.py web` (optional, for browsing)

The tool is ready for immediate use in MUJIN IT support workflows!