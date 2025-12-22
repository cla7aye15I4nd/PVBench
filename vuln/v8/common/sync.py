#!/usr/bin/env python3

import subprocess
from pathlib import Path

import git
import yaml

V8_REPO_URL = "https://chromium.googlesource.com/v8/v8.git"
V8_REPO_PATH = Path(__file__).parent / "v8"

if not V8_REPO_PATH.is_dir():
    git.Repo.clone_from(V8_REPO_URL, V8_REPO_PATH)

V8_REPO = git.Repo(V8_REPO_PATH)  


VULN_DIR = Path(__file__).parent.parent
for vuln_id in VULN_DIR.iterdir():
    if vuln_id.name.startswith("v8-"):
        print(vuln_id.name)
        
        id = vuln_id.name

        vuln_path = Path(__file__).parent.parent / id
        config_yaml = vuln_path / "config.yaml"
        config_data = yaml.load(config_yaml.read_text(), Loader=yaml.FullLoader)

        commit = config_data["patch"]["commit"]
        if not vuln_path.is_dir():
            vuln_path.mkdir(parents=True, exist_ok=True)

        patch_commit = V8_REPO.commit(commit).hexsha
        patch_datetime = V8_REPO.commit(patch_commit).committed_datetime.isoformat()

        trigger_commit = V8_REPO.commit(patch_commit).parents[0].hexsha

        modified_files = (
            subprocess.run(
                ["git", "diff", "--name-only", trigger_commit, patch_commit],
                cwd=V8_REPO_PATH,
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
                    cwd=V8_REPO_PATH,
                    capture_output=True,
                ).stdout
                patch_diff += diff

        # Generate test.diff for test files
        test_diff = b""
        if test_files:
            for file_path in test_files:
                diff = subprocess.run(
                    ["git", "diff", trigger_commit, patch_commit, "--binary", "--", file_path],
                    cwd=V8_REPO_PATH,
                    capture_output=True,
                ).stdout
                test_diff += diff

        if len(patch_files) == 0 or len(test_diff) == 0:
            print("[!] Patch format error")

        (vuln_path / "patch.diff").write_bytes(patch_diff)
        (vuln_path / "test.diff").write_bytes(test_diff)
