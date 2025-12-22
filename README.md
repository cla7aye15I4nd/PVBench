# PVBench

A comprehensive evaluation benchmark for **Automated Vulnerability Repair** tools.

## Overview

- **Vulnerability Dataset**: Real-world bugs with ground-truth patches, test cases, and PoCs
- **COLD Framework**: Automated evaluation infrastructure for patch validation

## Repository Structure

```
PVBench/
├── PatchAgent/              # LLM-based program repair agent (submodule)
├── San2Patch/               # Sanitizer-to-Patch framework (submodule)
├── pvbench-v8/              # V8 regression test cases (submodule)
├── vuln/                    # Vulnerability dataset (21 projects, 209 vulnerabilities)
├── cold/                    # COLD evaluation framework
├── litellm/                 # LiteLLM proxy for unified LLM API access
├── artifacts/               # Generated evaluation artifacts
├── data/                    # Data directory
└── docker-compose.yaml      # Docker orchestration for evaluation
```

## Vulnerability Dataset

### Per-Vulnerability Structure

Each vulnerability includes:

```
vuln/{project}/{id}/
├── config.yaml            # Metadata (id, project, sanitizer, type, commits, references)
├── patch.diff             # Human-written ground-truth patch
├── patch-rich.diff        # Annotated patch with context
├── test.diff              # Test case changes
├── test-rich.diff         # Annotated test changes
├── test.sh                # Test script for validation
├── report.txt             # Sanitizer report from PoC
└── input/                 # Proof-of-Concept files
    └── poc.{bin|py}       # PoC to trigger vulnerability
```

## Components

### COLD Framework

Evaluation infrastructure (`cold/` directory):

- **Actions**:
  - `check`: Verify vulnerability reproduction and patch validation
  - `gentest`: Generate test cases for vulnerabilities

- **Features**:
  - Concurrent processing with configurable thread pools
  - Patch validation pipeline: build → replay → function test → post-test
  - Multi-model LLM evaluation via LiteLLM proxy

## Configuration

### Vulnerability Config (`config.yaml`)

```yaml
id: CVE-2023-XXXXX
project: cpython
sanitizer: AddressSanitizer
type: heap-buffer-overflow
vulnerable_commit: abc123
fixed_commit: def456
references:
  - https://bugs.python.org/issue12345
```
