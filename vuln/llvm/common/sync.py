#!/usr/bin/env python3

import argparse
import subprocess
from pathlib import Path

import git
import yaml

LLVM_REPO_URL = "https://github.com/llvm/llvm-project.git"
LLVM_REPO_PATH = Path(__file__).parent / "llvm-project"

if not LLVM_REPO_PATH.is_dir():
    git.Repo.clone_from(LLVM_REPO_URL, LLVM_REPO_PATH)

LLVM_REPO = git.Repo(LLVM_REPO_PATH)

parser = argparse.ArgumentParser(description="Sync LLVM repository")
parser.add_argument("commit", type=str, help="Commit hash to sync to")
parser.add_argument("--issue", type=str, help="Issue number to link with the commit", required=True)
parser.add_argument("--binary", type=str, help="Binary to build and test", required=True)
parser.add_argument("--type", type=str, help="Type of the vulnerability", required=False)

args = parser.parse_args()

id = f"llvm-gh-{args.issue}"
vuln_path = Path(__file__).parent.parent / id
config_yaml = vuln_path / "config.yaml"

if not vuln_path.is_dir():
    vuln_path.mkdir(parents=True, exist_ok=True)

patch_commit = LLVM_REPO.commit(args.commit).hexsha
patch_datetime = LLVM_REPO.commit(patch_commit).committed_datetime.isoformat()

trigger_commit = LLVM_REPO.commit(patch_commit).parents[0].hexsha


config_data = {
    "id": id,
    "project": "llvm-project",
    "sanitizer": "LLVMSanitizer",
    "type": args.type,
    "trigger_commit": trigger_commit,
    "binary": args.binary,
    "patch": {
        "commit": patch_commit,
        "date": patch_datetime,
    },
    "reference": [
        "https://github.com/llvm/llvm-project",
        f"https://github.com/llvm/llvm-project/issues/{args.issue}",
        f"https://github.com/llvm/llvm-project/commit/{trigger_commit}",
        f"https://github.com/llvm/llvm-project/commit/{patch_commit}",
    ],
}

with config_yaml.open("w") as f:
    yaml.dump(config_data, f, sort_keys=False)

modified_files = (
    subprocess.run(
        ["git", "diff", "--name-only", trigger_commit, patch_commit],
        cwd=LLVM_REPO_PATH,
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
            ["git", "diff", trigger_commit, patch_commit, "--", file_path],
            cwd=LLVM_REPO_PATH,
            capture_output=True,
        ).stdout
        patch_diff += diff

# Generate test.diff for test files
test_diff = b""
if test_files:
    for file_path in test_files:
        diff = subprocess.run(
            ["git", "diff", trigger_commit, patch_commit, "--", file_path],
            cwd=LLVM_REPO_PATH,
            capture_output=True,
        ).stdout
        test_diff += diff

if len(patch_files) == 0 or len(test_diff) == 0:
    print("[!] Patch format error")

(vuln_path / "patch.diff").write_bytes(patch_diff)
(vuln_path / "test.diff").write_bytes(test_diff)

build_sh = vuln_path / "build.sh"
if not build_sh.is_file():
    build_sh.write_text(
        "#!/bin/bash -eu\n"
        "mkdir -p build && cd build\n"
        "cmake -G Ninja \\\n"
        "\t-DCMAKE_BUILD_TYPE=Debug \\\n"
        '\t-DLLVM_ENABLE_PROJECTS="clang" \\\n'
        '\t-DLLVM_TARGETS_TO_BUILD="X86" \\\n'
        "\t-DLLVM_BUILD_TESTS=OFF \\\n"
        "\t../llvm\n"
        f"ninja -j16 {args.binary}\n"
        f"test -f bin/{args.binary}\n"
    )
    build_sh.chmod(0o755)

exp_sh = vuln_path / "exp.sh"
if not exp_sh.is_file():
    exp_sh.write_text("#!/bin/bash -eu\n")
    exp_sh.chmod(0o755)

test_sh = vuln_path / "test.sh"
with test_sh.open("w") as f:
    lines = build_sh.read_text().splitlines()
    test_sh.write_text(
        "#!/bin/bash -eu\n"
        "mkdir -p build && cd build\n"
        "cmake -G Ninja \\\n"
        "\t-DCMAKE_BUILD_TYPE=Release \\\n"
        f"{lines[4]}\n"
        f"{lines[5]}\n"
        "\t-DLLVM_BUILD_TESTS=ON \\\n"
        "\t-DLLVM_INCLUDE_TESTS=ON \\\n"
        "\t../llvm\n"
        "ninja -j16\n"
        "ninja -j16 check-all\n"
    )
test_sh.chmod(0o755)
