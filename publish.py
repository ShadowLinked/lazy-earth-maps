#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lazy Earth & Maps - Release & Publishing Pipeline
==================================================
Builds a release ZIP for QGIS, updates plugins.xml, pushes to Git,
and creates a GitHub Release with downloadable assets.

Usage:
    python publish.py                     # Publish current version from metadata.txt
    python publish.py --version 3.2.1     # Bump version and publish
    python publish.py --dry-run           # Build ZIP and plugins.xml locally without pushing

Author: Lazy by Design (Sheldon Willie)
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

PLUGIN_DIR_NAME = "lazy_earth_maps"
GITHUB_OWNER    = "ShadowLinked"
GITHUB_REPO     = f"{GITHUB_OWNER}/lazy-earth-maps"
ROOT_DIR        = Path(__file__).parent.resolve()
DIST_DIR        = ROOT_DIR / "dist"

# Default token fallback from local environment or stored remote
EXCLUDE_DIRS = {
    "__pycache__",
    ".git",
    "dist",
    ".idea",
    ".vscode",
    ".github",
}

EXCLUDE_FILES = {
    "publish.py",
    "plugins.xml",
    ".gitignore",
    ".token",
    ".DS_Store",
    "Thumbs.db",
    "convert_icons.py",
    "create_png_icons.py",
    "ICON_CONVERSION.md",
}

EXCLUDE_EXTS = {".pyc", ".pyo", ".log"}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def get_token(cli_token: str | None = None) -> str | None:
    """Retrieve GitHub token from CLI arg, environment, local .token file, or git remote."""
    if cli_token:
        return cli_token
    for env in ("GITHUB_TOKEN", "GH_TOKEN"):
        val = os.environ.get(env)
        if val:
            return val.strip()

    # Try local untracked .token file
    token_file = ROOT_DIR / ".token"
    if token_file.exists():
        val = token_file.read_text(encoding="utf-8").strip()
        if val:
            return val

    # Try extracting from git remote URL
    try:
        res = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=str(ROOT_DIR), capture_output=True, text=True
        )
        url = res.stdout.strip()
        m = re.search(r"https://([^@]+)@github\.com/", url)
        if m:
            return m.group(1)
    except Exception:
        pass

    return None


def read_metadata() -> dict:
    meta_path = ROOT_DIR / "metadata.txt"
    if not meta_path.exists():
        raise FileNotFoundError(f"metadata.txt not found at {meta_path}")

    data = {
        "name": "Lazy Earth & Maps",
        "version": "3.2.0",
        "description": "Open QGIS view or layers in Google Maps, Street View and Google Earth.",
        "qgisMinimumVersion": "3.16",
        "author": "Lazy by Design (Sheldon Willie)",
    }

    text = meta_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if "=" in line and not line.startswith("\t") and not line.startswith(" "):
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            if k in data:
                data[k] = v

    return data


def update_metadata_version(new_version: str):
    meta_path = ROOT_DIR / "metadata.txt"
    text = meta_path.read_text(encoding="utf-8")
    updated = re.sub(r"^version\s*=.*$", f"version={new_version}", text, flags=re.MULTILINE)
    meta_path.write_text(updated, encoding="utf-8")
    print(f"[OK] Updated metadata.txt version -> {new_version}")


def read_changelog_for_version(version: str) -> str:
    meta_path = ROOT_DIR / "metadata.txt"
    if not meta_path.exists():
        return f"Release v{version}"
    text = meta_path.read_text(encoding="utf-8")
    m = re.search(r"changelog\s*=\s*\n(.*)", text, re.DOTALL)
    if not m:
        return f"Release v{version}"
    lines = m.group(1).splitlines()
    body_lines = []
    in_block = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(version):
            in_block = True
            body_lines.append(stripped)
            continue
        if in_block:
            if re.match(r"\d+\.\d+", stripped) and not stripped.startswith("-"):
                break
            body_lines.append(stripped)
    return "\n".join(body_lines) if body_lines else f"Release v{version}"


def build_plugin_zip(version: str) -> tuple[Path, Path]:
    """Package the plugin files into dist/lazy_earth_maps.zip with proper inner folder."""
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    versioned_zip = DIST_DIR / f"lazy_earth_maps_v{version}.zip"
    plain_zip     = DIST_DIR / "lazy_earth_maps.zip"

    print(f"\n--- Building Plugin ZIP: {versioned_zip.name} ---")

    for zpath in (versioned_zip, plain_zip):
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(ROOT_DIR):
                rel_root = Path(root).relative_to(ROOT_DIR)

                # Skip excluded directories
                if any(part in EXCLUDE_DIRS for part in rel_root.parts):
                    continue

                dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

                for file in files:
                    rel_file = rel_root / file
                    if file in EXCLUDE_FILES or rel_file.suffix in EXCLUDE_EXTS:
                        continue

                    # In QGIS plugin ZIPs, all files must be inside the plugin folder
                    arcname = Path(PLUGIN_DIR_NAME) / rel_file
                    zf.write(Path(root) / file, str(arcname).replace("\\", "/"))

        size_kb = zpath.stat().st_size / 1024
        print(f"[OK] Created {zpath.name} ({size_kb:.1f} KB)")

    return versioned_zip, plain_zip


def update_plugins_xml(meta: dict):
    """Generate or update plugins.xml adhering strictly to QGIS repository format."""
    xml_path = ROOT_DIR / "plugins.xml"
    version = meta["version"]
    name_escaped = meta["name"].replace("&", "&amp;")
    desc_escaped = meta["description"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    download_url = f"https://github.com/{GITHUB_REPO}/releases/download/v{version}/lazy_earth_maps.zip"

    xml_content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<plugins>\n'
        f'  <pyqgis_plugin name="{name_escaped}" version="{version}">\n'
        f'    <description>{desc_escaped}</description>\n'
        f'    <version>{version}</version>\n'
        f'    <qgis_minimum_version>{meta["qgisMinimumVersion"]}</qgis_minimum_version>\n'
        f'    <author_name>{meta["author"]}</author_name>\n'
        f'    <download_url>{download_url}</download_url>\n'
        '    <file_name>lazy_earth_maps.zip</file_name>\n'
        '    <experimental>False</experimental>\n'
        '    <deprecated>False</deprecated>\n'
        '  </pyqgis_plugin>\n'
        '</plugins>\n'
    )

    xml_path.write_text(xml_content, encoding="utf-8")
    print(f"[OK] Updated plugins.xml -> v{version}")
    print(f"     Download URL: {download_url}")


# ─────────────────────────────────────────────────────────────────────────────
# GIT & GITHUB RELEASES
# ─────────────────────────────────────────────────────────────────────────────

def ensure_git_repo(token: str):
    """Initialize git repo if needed, ensure origin points to ShadowLinked/lazy-earth-maps."""
    is_git = (ROOT_DIR / ".git").is_dir()
    if not is_git:
        print("\n--- Initializing local git repository ---")
        subprocess.run(["git", "init", "-b", "main"], cwd=str(ROOT_DIR), check=True)

    remote_url = f"https://{token}@github.com/{GITHUB_REPO}.git"

    # Check remote origin
    res = subprocess.run(["git", "remote", "get-url", "origin"], cwd=str(ROOT_DIR), capture_output=True, text=True)
    if res.returncode == 0:
        subprocess.run(["git", "remote", "set-url", "origin", remote_url], cwd=str(ROOT_DIR), check=True)
    else:
        subprocess.run(["git", "remote", "add", "origin", remote_url], cwd=str(ROOT_DIR), check=True)

    print(f"[OK] Git remote origin configured: https://github.com/{GITHUB_REPO}.git")


def git_commit_and_push(version: str):
    """Stage all files, commit, and push main branch to GitHub."""
    print("\n--- Pushing source to GitHub repository ---")
    subprocess.run(["git", "add", "."], cwd=str(ROOT_DIR), check=True)

    status = subprocess.run(["git", "status", "--porcelain"], cwd=str(ROOT_DIR), capture_output=True, text=True)
    if status.stdout.strip():
        subprocess.run(["git", "commit", "-m", f"release: v{version}"], cwd=str(ROOT_DIR), check=True)
        print(f"[OK] Committed release v{version}")
    else:
        print("[INFO] Working tree clean, nothing new to commit")

    res = subprocess.run(["git", "push", "-u", "origin", "main"], cwd=str(ROOT_DIR), capture_output=True, text=True)
    if res.returncode != 0:
        # If rejected due to remote history, pull/rebase and push
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], cwd=str(ROOT_DIR))
        subprocess.run(["git", "push", "-u", "origin", "main"], cwd=str(ROOT_DIR), check=True)
    print(f"[OK] Pushed main branch to https://github.com/{GITHUB_REPO}")


def publish_github_release(version: str, versioned_zip: Path, plain_zip: Path, token: str) -> bool:
    """Create GitHub Release via REST API and upload ZIP assets."""
    tag = f"v{version}"
    title = f"Lazy Earth & Maps v{version}"
    body = read_changelog_for_version(version)
    api = "https://api.github.com"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "LazyEarthMaps-ReleasePipeline",
    }

    print(f"\n--- Publishing GitHub Release {tag} to {GITHUB_REPO} ---")

    # 1. Create Release
    payload = json.dumps({
        "tag_name": tag,
        "target_commitish": "main",
        "name": title,
        "body": body,
        "draft": False,
        "prerelease": False,
    }).encode("utf-8")

    try:
        req = urllib.request.Request(f"{api}/repos/{GITHUB_REPO}/releases", data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req) as resp:
            release = json.loads(resp.read())
        upload_url = release["upload_url"].replace("{?name,label}", "")
        print(f"[OK] Created release: {release['html_url']}")
    except urllib.error.HTTPError as e:
        body_err = e.read().decode()
        if e.code == 422 or "already_exists" in body_err:
            print(f"[INFO] Release {tag} already exists, fetching existing release...")
            req_get = urllib.request.Request(f"{api}/repos/{GITHUB_REPO}/releases/tags/{tag}", headers=headers)
            with urllib.request.urlopen(req_get) as resp2:
                release = json.loads(resp2.read())
            upload_url = release["upload_url"].replace("{?name,label}", "")

            # Update release notes
            patch_data = json.dumps({"body": body, "name": title}).encode("utf-8")
            patch_req = urllib.request.Request(
                f"{api}/repos/{GITHUB_REPO}/releases/{release['id']}",
                data=patch_data, headers=headers, method="PATCH"
            )
            with urllib.request.urlopen(patch_req) as pr:
                json.loads(pr.read())
            print("[OK] Updated release notes on existing release")
        else:
            print(f"[FAIL] Failed to create release: {e.code} - {body_err}")
            return False

    # 2. Upload Assets
    def _upload_asset(asset_name: str, asset_path: Path):
        for existing in release.get("assets", []):
            if existing["name"] == asset_name:
                del_req = urllib.request.Request(
                    f"{api}/repos/{GITHUB_REPO}/releases/assets/{existing['id']}",
                    headers=headers, method="DELETE"
                )
                try:
                    urllib.request.urlopen(del_req)
                    print(f"[OK] Deleted old asset: {asset_name}")
                except Exception:
                    pass
                break

        data = asset_path.read_bytes()
        up_headers = dict(headers)
        up_headers["Content-Type"] = "application/zip"
        up_headers["Content-Length"] = str(len(data))
        upload_target = f"{upload_url}?name={asset_name}"
        up_req = urllib.request.Request(upload_target, data=data, headers=up_headers, method="POST")
        with urllib.request.urlopen(up_req) as up_resp:
            asset_info = json.loads(up_resp.read())
        print(f"[OK] Uploaded asset: {asset_info['browser_download_url']}")

    _upload_asset(plain_zip.name, plain_zip)
    _upload_asset(versioned_zip.name, versioned_zip)

    return True


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Build and publish Lazy Earth & Maps QGIS plugin.")
    parser.add_argument("--version", "-v", default=None, help="New version string (e.g. 3.2.1)")
    parser.add_argument("--dry-run", action="store_true", help="Build ZIP and XML locally without pushing to GitHub")
    parser.add_argument("--skip-git", action="store_true", help="Skip git push, only build release assets")
    parser.add_argument("--token", default=None, help="GitHub Personal Access Token")
    args = parser.parse_args()

    print("=" * 65)
    print("      LAZY EARTH & MAPS - RELEASE & PUBLISHING PIPELINE")
    print("=" * 65)

    if args.version:
        update_metadata_version(args.version)

    meta = read_metadata()
    version = meta["version"]
    print(f"Plugin:   {meta['name']} (v{version})")
    print(f"Target:   https://github.com/{GITHUB_REPO}")

    # 1. Update plugins.xml
    update_plugins_xml(meta)

    # 2. Package ZIPs
    versioned_zip, plain_zip = build_plugin_zip(version)

    if args.dry_run:
        print("\n[DRY RUN] Complete! Files generated locally in dist/ and plugins.xml.")
        return

    # 3. GitHub Token
    token = get_token(args.token)
    if not token:
        print("\n[FAIL] No GitHub token found. Set GITHUB_TOKEN environment variable or pass --token.")
        sys.exit(1)

    # 4. Git Commit & Push
    if not args.skip_git:
        ensure_git_repo(token)
        git_commit_and_push(version)

    # 5. Create GitHub Release & Upload Assets
    success = publish_github_release(version, versioned_zip, plain_zip, token)

    if success:
        print("\n" + "=" * 65)
        print("                 SUCCESSFULLY PUBLISHED!")
        print("=" * 65)
        print(f"📦 GitHub Release:    https://github.com/{GITHUB_REPO}/releases/tag/v{version}")
        print(f"⬇️ Direct Download:   https://github.com/{GITHUB_REPO}/releases/download/v{version}/lazy_earth_maps.zip")
        print(f"🌐 QGIS Repo XML URL: https://raw.githubusercontent.com/{GITHUB_REPO}/main/plugins.xml")
        print("=" * 65)


if __name__ == "__main__":
    main()
