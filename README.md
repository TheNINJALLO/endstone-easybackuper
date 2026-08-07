<!-- endstone-professional-header:start -->
<p align="center">
  <img src="docs/assets/banner.svg" width="100%" alt="Endstone Easy Backuper &mdash; The simplest Python hot backup plugin based on EndStone">
</p>

<p align="center">
  <a href="https://github.com/TheNINJALLO/endstone-easybackuper/actions/workflows/wheel-release.yml"><img alt="Build" src="https://img.shields.io/github/actions/workflow/status/TheNINJALLO/endstone-easybackuper/wheel-release.yml?branch=main&amp;style=for-the-badge&amp;logo=githubactions&amp;logoColor=white&amp;label=Build"></a>
  <a href="https://github.com/TheNINJALLO/endstone-easybackuper/releases/latest"><img alt="Latest release" src="https://img.shields.io/github/v/release/TheNINJALLO/endstone-easybackuper?display_name=tag&amp;style=for-the-badge&amp;label=Release"></a>
</p>

<p align="center">
  <img alt="Endstone 0.11.8" src="https://img.shields.io/badge/Endstone-0.11.8-52b7a8?style=flat-square">
  <img alt="API 0.11" src="https://img.shields.io/badge/API-0.11-63b8ff?style=flat-square">
  <img alt="BDS 1.26.40" src="https://img.shields.io/badge/BDS-1.26.40-8b7dff?style=flat-square">
  <img alt="Python >=3.10" src="https://img.shields.io/badge/Python-%3E=3.10-3776AB?style=flat-square&amp;logo=python&amp;logoColor=white">
</p>

<p align="center">
  <strong>The simplest Python hot backup plugin based on EndStone.</strong>
</p>

<p align="center">
  <a href="#what-it-does">What it does</a> &bull;
  <a href="#how-to-use">How to use</a> &bull;
  <a href="#commands-and-permissions">Commands</a> &bull;
  <a href="#install">Install</a> &bull;
  <a href="https://github.com/TheNINJALLO/endstone-easybackuper/releases">Releases</a>
</p>

## Overview

The simplest Python hot backup plugin based on EndStone. This release is aligned with Endstone 0.11.8 and Minecraft Bedrock Dedicated Server 1.26.40, and is distributed as a Python wheel for direct installation in an Endstone server.

## What it does

- Creates hot world backups by coordinating Bedrock's `save hold`, `save query`, and `save resume` flow.
- Copies a consistent world snapshot and archives it without requiring a full server shutdown.
- Exposes simple initialization, reload, and manual-backup operations for operators and the console.

## How to use

1. Run `/backup init` once if the generated paths need initialization, then inspect the plugin's backup settings.
2. Run `/backup` from the console or as an operator to create a snapshot and wait for the success message before moving the archive.
3. Use `/backup reload` after changing settings and periodically test a restore on a separate server.

## Commands and permissions

| Command / usage | What it does | Access |
|---|---|---|
| `/backup`<br>`/backup <init>`<br>`/backup <reload>` | Create a hot backup (console or OP). | `easybackuper_plugin.command.only_op` |

## Compatibility

| Component | Supported version |
|---|---|
| Endstone | `0.11.8` |
| Endstone API | `0.11` |
| Bedrock Dedicated Server | `1.26.40` |
| Python | `>=3.10` |
| Plugin release | `v0.3.1` |

## Install

Download the wheel from the matching GitHub release:

```bash
gh release download v0.3.1 --repo TheNINJALLO/endstone-easybackuper --pattern "*.whl"
```

Copy the downloaded wheel into the server's `plugins/` directory, remove any older wheel for the same plugin, and restart Endstone.

> [!IMPORTANT]
> Use Endstone `0.11.8` with BDS `1.26.40`. Back up worlds and plugin data before upgrading a production server.

## Configuration and secrets

Runtime databases, logs, local `.env` files, server directories, and root `config.toml` files are excluded from source releases. When an example configuration is provided, copy it locally and keep live tokens, passwords, webhook URLs, and server identifiers out of Git.

## Release automation

Every `v*` tag runs [the wheel release workflow](.github/workflows/wheel-release.yml), builds the package in a clean GitHub runner, stores the wheel as a workflow artifact, and attaches it to the matching GitHub release.
<!-- endstone-professional-header:end -->
