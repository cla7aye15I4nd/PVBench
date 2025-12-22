#!/usr/bin/env python3

from pathlib import Path
import shutil
from git import Repo
import yaml

V8_PATH = Path(__file__).parent / "v8"
VULN_PATH = Path(__file__).parent.parent


def is_valid_regression_test(js_file):
    """Check if a JS file is a valid regression test."""
    name = js_file.stem
    if not name.startswith("regress-"):
        return False
    
    content = js_file.read_text()
    return "assert" in content


def get_single_commit_info(repo, js_file):
    """Get commit information if file has exactly one commit."""
    commits = list(repo.iter_commits(paths=js_file))
    if len(commits) != 1:
        return None
    return commits[0]


def is_commit_valid(commit):
    """Validate commit meets our criteria."""
    # Skip commits before 2020
    if commit.committed_datetime.year < 2020:
        return False
    
    # Skip merge commits
    if len(commit.parents) > 1:
        return False
    
    # Check if exactly 2 files were modified
    if len(commit.stats.files) != 2:
        return False
    
    # Verify exactly one JS file was added
    js_files_added = 0
    for file, diff in commit.stats.files.items():
        if Path(file).name.endswith(".js"):
            if diff["change_type"] != "A":
                return False
            js_files_added += 1
    
    return js_files_added == 1


def create_vulnerability_entry(vuln_id, js_file, commit, parent_commit, repo):
    """Create vulnerability directory and configuration."""
    path = VULN_PATH / vuln_id
    path.mkdir(parents=True, exist_ok=True)
    
    # Create config.yaml
    config_data = {
        "id": vuln_id,
        "name": "v8",
        "sanitizer": "LeakAddressSanitizer",
        "type": None,
        "trigger_commit": parent_commit.hexsha,
        "binary": "d8",
        "patch": {
            "commit": commit.hexsha,
            "date": commit.committed_datetime,
        },
        "reference": [
            "https://chromium.googlesource.com/v8/v8.git",
            f"https://chromium.googlesource.com/v8/v8.git/+/{parent_commit.hexsha}",
            f"https://chromium.googlesource.com/v8/v8.git/+/{commit.hexsha}",
        ],
    }
    
    with (path / "config.yaml").open("w") as f:
        yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
    
    # Copy test file
    input_dir = path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(js_file, input_dir / js_file.name)
    
    # Create patch diff (excluding the test file)
    with (path / "patch.diff").open("w") as f:
        diff = repo.git.diff(parent_commit.hexsha, commit.hexsha, "--", ":(exclude)" + str(js_file))
        f.write(diff)
    
    # Create test diff (only the test file)
    with (path / "test.diff").open("w") as f:
        diff = repo.git.diff(parent_commit.hexsha, commit.hexsha, "--", js_file)
        f.write(diff)


def main():
    """Scan V8 repository for regression tests and create vulnerability entries."""
    repo = Repo(V8_PATH)
    processed_names = set()
    
    test_path = V8_PATH / "test"
    for js_file in test_path.rglob("*.js"):
        if not is_valid_regression_test(js_file):
            continue
        
        name = js_file.stem
        if name in processed_names:
            print(f"Duplicate ID found: {name}")
            continue
        
        commit = get_single_commit_info(repo, js_file)
        if not commit:
            continue
        
        if not is_commit_valid(commit):
            continue
        
        processed_names.add(name)
        parent_commit = commit.parents[0]
        
        # Ensure commit message is string
        message = commit.message
        if isinstance(message, bytes):
            message = message.decode("utf-8")
        
        vuln_id = f"v8-{name}"
        create_vulnerability_entry(vuln_id, js_file, commit, parent_commit, repo)


if __name__ == "__main__":
    main()
