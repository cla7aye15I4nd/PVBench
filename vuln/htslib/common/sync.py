#!/usr/bin/env python3

import argparse
import subprocess
from pathlib import Path

import git
import yaml

HTSLIB_REPO_URL = "https://github.com/samtools/htslib.git"
HTSLIB_REPO_PATH = Path(__file__).parent / "htslib"

if not HTSLIB_REPO_PATH.is_dir():
    git.Repo.clone_from(HTSLIB_REPO_URL, HTSLIB_REPO_PATH)

HTSLIB_REPO = git.Repo(HTSLIB_REPO_PATH)

parser = argparse.ArgumentParser(description="Sync htslib repository")
parser.add_argument("commit", type=str, help="Commit hash to sync to")
parser.add_argument("--issue", type=str, help="Issue number to link with the commit")

args = parser.parse_args()

if args.issue:
    id = f"htslib-gh-{args.issue}"
else:
    id = f"htslib-commit-{args.commit[:7]}"

vuln_path = Path(__file__).parent.parent / id
config_yaml = vuln_path / "config.yaml"

if not vuln_path.is_dir():
    vuln_path.mkdir(parents=True, exist_ok=True)

patch_commit = HTSLIB_REPO.commit(args.commit).hexsha
patch_datetime = HTSLIB_REPO.commit(patch_commit).committed_datetime.isoformat()

trigger_commit = HTSLIB_REPO.commit(patch_commit).parents[0].hexsha


config_data = {
    "id": id,
    "project": "htslib",
    "sanitizer": "AddressSanitizer",
    "type": None,
    "binary": None,
    "trigger_commit": trigger_commit,
    "patch": {
        "commit": patch_commit,
        "date": patch_datetime,
    },
    "reference": [
        "https://github.com/samtools/htslib",
        f"https://github.com/samtools/htslib/issues/{args.issue}",
        f"https://github.com/samtools/htslib/commit/{trigger_commit}",
        f"https://github.com/samtools/htslib/commit/{patch_commit}",
    ],
}

modified_files = (
    subprocess.run(
        ["git", "diff", "--name-only", trigger_commit, patch_commit],
        cwd=HTSLIB_REPO_PATH,
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
    elif file_path and "release_docs" not in file_path.lower():
        patch_files.append(file_path)

# Generate patch.diff for non-test files
patch_diff = b""
if patch_files:
    for file_path in patch_files:
        diff = subprocess.run(
            ["git", "diff", trigger_commit, patch_commit, "--binary", "--", file_path],
            cwd=HTSLIB_REPO_PATH,
            capture_output=True,
        ).stdout
        patch_diff += diff

# Generate test.diff for test files
test_diff = b""
if test_files:
    for file_path in test_files:
        diff = subprocess.run(
            ["git", "diff", trigger_commit, patch_commit, "--binary", "--", file_path],
            cwd=HTSLIB_REPO_PATH,
            capture_output=True,
        ).stdout
        test_diff += diff

if len(patch_files) == 0 or len(test_diff) == 0:
    print("[!] Patch format error")

(vuln_path / "patch.diff").write_bytes(patch_diff)
(vuln_path / "test.diff").write_bytes(test_diff)

test_file = test_files[0]
binary = test_file.split("/")[1]
config_data["binary"] = binary

test_case = subprocess.run(
    ["git", "show", f"{patch_commit}:{test_file}"],
    cwd=HTSLIB_REPO_PATH,
    capture_output=True,
).stdout

exp_sh = vuln_path / "exp.sh"
exp_sh.write_text(f"""#!/bin/bash -eu
./build/{binary} $1
""")
exp_sh.chmod(0o755)

build_sh = vuln_path / "build.sh"
build_sh.write_text(f"""#!/bin/bash -eu
mkdir -p build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Debug
make -j32
test -f {binary}
""")
build_sh.chmod(0o755)

input_dir = vuln_path / "input"
if not input_dir.is_dir():
    input_dir.mkdir(parents=True, exist_ok=True)
poc_path = input_dir / "poc.htslib"
poc_path.write_bytes(test_case)

with config_yaml.open("w") as f:
    yaml.dump(config_data, f, sort_keys=False)
