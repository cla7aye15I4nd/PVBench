#!/usr/bin/env python3

import argparse
import subprocess
from pathlib import Path

import git
import yaml

LIBTIFF_REPO_URL = "https://gitlab.com/libtiff/libtiff.git"
LIBTIFF_REPO_PATH = Path(__file__).parent / "libtiff"

if not LIBTIFF_REPO_PATH.is_dir():
    git.Repo.clone_from(LIBTIFF_REPO_URL, LIBTIFF_REPO_PATH)

LIBTIFF_REPO = git.Repo(LIBTIFF_REPO_PATH)  

parser = argparse.ArgumentParser(description="Sync LIBTIFF repository")
parser.add_argument("commit", type=str, help="Commit hash to sync to")
parser.add_argument("--issue", type=str, help="Issue number to link with the commit", required=True)

args = parser.parse_args()

id = f"tif-gh-{args.issue}"
vuln_path = Path(__file__).parent.parent / id
config_yaml = vuln_path / "config.yaml"

if not vuln_path.is_dir():
    vuln_path.mkdir(parents=True, exist_ok=True)

patch_commit = LIBTIFF_REPO.commit(args.commit).hexsha
patch_datetime = LIBTIFF_REPO.commit(patch_commit).committed_datetime.isoformat()

trigger_commit = LIBTIFF_REPO.commit(patch_commit).parents[0].hexsha


config_data = {
    "id": id,
    "project": "libtiff",
    "sanitizer": "AddressSanitizer",
    "type": None,
    "trigger_commit": trigger_commit,    
    "patch": {
        "commit": patch_commit,
        "date": patch_datetime,
    },
    "reference": [
        "https://gitlab.com/libtiff/libtiff",
        f"https://gitlab.com/libtiff/libtiff/-/merge_requests/{args.issue}",
        f"https://gitlab.com/libtiff/libtiff/-/commit/{trigger_commit}",
        f"https://gitlab.com/libtiff/libtiff/-/commit/{patch_commit}",
    ],
}

with config_yaml.open("w") as f:
    yaml.dump(config_data, f, sort_keys=False)

modified_files = (
    subprocess.run(
        ["git", "diff", "--name-only", trigger_commit, patch_commit],
        cwd=LIBTIFF_REPO_PATH,
        capture_output=True,
        text=True,
    )
    .stdout.strip()
    .split("\n")
)

# Separate files into test and patch categories
test_files = []
patch_files = []

for file_path in modified_files:
    if file_path and "test" in file_path.lower():
        test_files.append(file_path)
    elif file_path:
        patch_files.append(file_path)

# Generate patch.diff for non-test files
patch_diff = b""
if patch_files:
    for file_path in patch_files:
        diff = subprocess.run(
            ["git", "diff", trigger_commit, patch_commit, "--binary", "--", file_path],
            cwd=LIBTIFF_REPO_PATH,
            capture_output=True,
        ).stdout
        patch_diff += diff

# Generate test.diff for test files
test_diff = b""
if test_files:
    for file_path in test_files:
        diff = subprocess.run(
            ["git", "diff", trigger_commit, patch_commit, "--binary", "--", file_path],
            cwd=LIBTIFF_REPO_PATH,
            capture_output=True,
        ).stdout
        test_diff += diff

if len(patch_files) == 0 or len(test_diff) == 0:
    print("[!] Patch format error")

(vuln_path / "patch.diff").write_bytes(patch_diff)
(vuln_path / "test.diff").write_bytes(test_diff)

input_dir = vuln_path / "input"
if not input_dir.is_dir():
    input_dir.mkdir(parents=True, exist_ok=True)

exp_sh = vuln_path / "exp.sh"
exp_sh.write_text(f"""#!/bin/bash
""")
exp_sh.chmod(0o755)
