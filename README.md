<div align="center">

# PVBench

### Patch Validation in Automated Vulnerability Repair

[![Dataset](https://img.shields.io/badge/Dataset-209_Vulnerabilities-green.svg)](#dataset-overview)
[![Projects](https://img.shields.io/badge/Projects-20-orange.svg)](#supported-projects)

*A comprehensive benchmark for evaluating patch validation methods in Automated Vulnerability Repair (AVR) systems*

[Key Findings](#-key-findings) | [Dataset](#-dataset-overview) | [Methodology](#-methodology) | [Results](#-experimental-results) | [Getting Started](#-getting-started)

</div>

---

## Abstract

Automated Vulnerability Repair (AVR) systems, particularly those leveraging large language models (LLMs), have demonstrated promising results in addressing security vulnerabilities. However, their evaluation reliability depends on the accuracy of the patch validation method.

Current AVR research relies predominantly on **test suite-based validation**, which assumes patch correctness when generated patches pass existing functional tests and mitigate proof-of-concept (PoC) exploits. This approach often captures incomplete functional requirements, potentially leading to **overestimated performance metrics**.

We propose using **PoC+ tests**—functional tests covering PoC-related code—as a more rigorous validation approach. Through evaluation of three state-of-the-art AVR systems, we demonstrate that:

> **Over 40% of patches validated as correct by basic tests fail under PoC+ testing, revealing substantial overestimation in current AVR evaluation methodologies.**

---

## Key Findings

<table>
<tr>
<td width="50%">

### The Problem

```
Traditional Validation Pipeline:
┌─────────────────┐
│  Generated      │
│  Patch          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  PoC + Basic    │──► Pass? ──► "Correct" ✗
│  Test Suite     │
└─────────────────┘
```

</td>
<td width="50%">

### Our Solution

```
PoC+ Validation Pipeline:
┌─────────────────┐
│  Generated      │
│  Patch          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  PoC + Basic    │
│  Test Suite     │
└────────┬────────┘
         │ Pass?
         ▼
┌─────────────────┐
│  PoC+ Tests     │──► Pass? ──► Correct ✓
│  (Enhanced)     │
└─────────────────┘
```

</td>
</tr>
</table>

### Key Statistics

| Metric | Value |
|--------|-------|
| False Discovery Rate (FDR) | **~42%** |
| Patches passing basic tests | 47.1% |
| Patches passing PoC+ tests | 27.1% |
| Semantic equivalence with developer patches | **>70%** |

---

## Dataset Overview

**PVBench** comprises **209 real-world vulnerabilities** from **20 open-source C/C++ projects**, each with basic tests and PoC+ tests.

### Project Statistics

| Project | LoC | # Cases | # Test | Project | LoC | # Cases | # Test |
|---------|-----|---------|----------|---------|-----|---------|----------|
| PHP | 1,390.2K | 43 | 18.7K | Vim | 564.2K | 11 | 5.2K |
| CPython | 745.9K | 33 | 48.6K | HDF5 | 1,334.4K | 8 | 0.6K |
| LLVM | 8,980.4K | 26 | 128.7K | Exiv2 | 93.5K | 7 | 0.3K |
| V8 | 6,225.6K | 24 | 53.7K | Wabt | 514.9K | 5 | 1.1K |
| libxml2 | 200.4K | 19 | 3.3K | Hermes | 590.0K | 4 | 2.3K |
| ICU | 1,241.5K | 15 | 2.0K | PcapPlusPlus | 160.0K | 3 | 0.3K |
| QuickJS | 78.8K | 2 | 79.7K | libtiff | 109.0K | 1 | 0.2K |
| mruby | 152.4K | 2 | 1.7K | JasPer | 5.5K | 1 | 0.2K |
| jq | 4.7K | 2 | 0.9K | simdjson | 547.5K | 1 | 0.1K |
| htslib | 108.3K | 1 | 0.4K | Wireshark | 6,088.9K | 1 | 0.1K |

### CWE Distribution

```
CWE-476  NULL Dereference        ████████████████████████████ 52
CWE-617  Reachable Assertion     ████████████████████████ 40
CWE-122  Heap Overflow           ████████████████████ 34
CWE-416  Use After Free          ███████████████████ 32
CWE-190  Integer Overflow        ███████████████ 26
CWE-121  Stack Overflow          ███████ 13
CWE-670  Incorrect Control Flow  ██ 3
CWE-415  Double Free             ██ 3
CWE-704  Type Confusion          ██ 3
CWE-457  Uninitialized Memory    █ 1
CWE-362  Race Condition          █ 1
CWE-369  Divide by Zero          █ 1
```

---

## Methodology

### What are PoC+ Tests?

**PoC+ tests** are functional tests derived from PoC exploits that perform comprehensive validations beyond crash detection. Unlike common PoCs that only observe if the program crashes, PoC+ tests verify expected program behaviors.

### Three Categories of PoC+ Tests

<table>
<tr>
<th>Category</th>
<th>Description</th>
<th>Projects</th>
</tr>
<tr>
<td><b>Output Checking</b></td>
<td>Validates program output against expected results when processing external inputs</td>
<td>exiv2, hermes, htslib, jasper, libxml2, php, jq, llvm, simdjson, wabt, wireshark</td>
</tr>
<tr>
<td><b>Intermediate Checking</b></td>
<td>Validates return values and intermediate states of API function calls</td>
<td>hdf5, icu, pcapplusplus, libtiff</td>
</tr>
<tr>
<td><b>Self Checking</b></td>
<td>Embeds assertions within interpreted scripts to verify runtime behavior</td>
<td>cpython, mruby, quickjs, v8, vim</td>
</tr>
</table>

### Validation Workflow

```
                    ┌──────────────────────────────────────────────────────────┐
                    │                   PoC+ Test Generation                   │
                    └──────────────────────────────────────────────────────────┘
                                              │
          ┌───────────────────────────────────┼───────────────────────────────────┐
          │                                   │                                   │
          ▼                                   ▼                                   ▼
    ┌──────────────────┐            ┌──────────────────┐            ┌──────────────────┐
    │  Output Checking │            │   Intermediate   │            │  Self Checking   │
    │                  │            │    Checking      │            │                  │
    │  Run program     │            │  Run harness     │            │  LLM Agent       │
    │  Compare outputs │            │  Check returns   │            │  Iterative       │
    │  (Deterministic) │            │  (LLM-assisted)  │            │  refinement      │
    └──────────────────┘            └──────────────────┘            └──────────────────┘
```

---

## Experimental Results

### AVR Tool Performance

We evaluated three state-of-the-art AVR systems with two LLMs (GPT-4.1 and Claude Sonnet-4):

| Tool | Model | Basic Tests | +Dev PoC+ | +Gen PoC+ | FDR |
|------|-------|-------------|-----------|-----------|-----|
| **PatchAgent** | Sonnet-4 | 83.5% | 50.7% | 50.1% | 40.1% |
| **PatchAgent** | GPT-4.1 | 76.4% | 45.2% | 44.5% | 41.7% |
| **San2Patch** | Sonnet-4 | 41.3% | 21.6% | 20.7% | 49.8% |
| **San2Patch** | GPT-4.1 | 37.9% | 20.2% | 19.6% | 48.2% |
| **SWE-Agent** | Sonnet-4 | 29.0% | 20.5% | 19.6% | 32.3% |
| **SWE-Agent** | GPT-4.1 | 14.4% | 8.4% | 8.3% | 41.3% |
| **Overall** | - | **47.1%** | **27.8%** | **27.1%** | **42.3%** |

> **FDR (False Discovery Rate)**: Fraction of patches passing basic tests that fail PoC+ tests

### Patch Quality Analysis

For patches that pass PoC+ tests, manual comparison with developer patches reveals:

| Category | Percentage | Description |
|----------|------------|-------------|
| **Semantic Equivalent** | 74.38% | Functionally identical to developer patches |
| Suboptimal Repair | 12.22% | Correct but inferior implementation quality |
| Check Circumvention | 10.11% | Bypasses checks rather than fixing root cause |
| Performance Issue | 3.29% | Higher time/space complexity than developer solution |

### False Positive Analysis

Patches that pass basic tests but fail PoC+ tests fall into three categories:

```
Specification Violation    ████████████████████████████████████████████ 54.38%
Incorrect Root Cause       █████████████████████████████████ 41.18%
Poor Code Practice         ████ 4.40%
```

---

## Motivating Example

### The Problem: Plausible but Incorrect Patches

Consider a type confusion vulnerability in PHP's `range()` function:

```c
// Vulnerable code - type confusion when mixing doubles and arrays
if (start_type >= IS_STRING || end_type >= IS_STRING) {
    // VULNERABLE: condition fails when IS_DOUBLE(5) + IS_ARRAY(7) = 12 = 2*IS_STRING
    if (start_type + end_type < 2*IS_STRING) {
        goto handle_numeric_inputs;
    }
    // TYPE CONFUSION: reaches string handling with non-string types
    unsigned char low = Z_STRVAL_P(user_start)[0];  // CRASH
}
```

**Developer Patch** (Correct):
```diff
- if (start_type + end_type < 2*IS_STRING) {
+ if (start_type < IS_STRING || end_type < IS_STRING) {
```

**AVR-Generated Patch** (Passes basic tests, fails PoC+):
```diff
+ if (Z_TYPE_P(user_start) != IS_STRING) {
+     zend_argument_value_error(1, "must be a string");
+     RETURN_THROWS();
+ }
```

### Why PoC+ Tests Catch This

The PoC+ test verifies that `range(9.9, '0')` produces the expected numeric array:

```php
// PoC+ test
<?php var_dump(range(9.9, '0')); ?>
// Expected: array(10) { [0]=>float(9.9), [1]=>float(8.9), ... }
```

The AVR patch incorrectly throws an error, violating PHP's specification that allows mixed-type inputs.

---

## Getting Started

### Prerequisites

- Docker (recommended) or native build environment
- Python 3.12+
- Git


### Directory Structure

```
PVBench/
├── artifacts/              # Generated artifacts and test outputs
│   └── gen/               # Auto-generated PoC+ tests
├── pvbench-*/             # Per-project vulnerability cases
│   └── <issue-id>/        # Individual vulnerability
│       ├── poc/           # Proof-of-concept exploits
│       ├── patch/         # Developer patches
│       ├── tests/         # Basic test suite
│       └── poc_plus/      # PoC+ tests
├── PatchAgent/            # AVR tool integration
├── scripts/               # Utility scripts
│   └── generate_*.py      # PoC+ generation scripts
└── README.md
```

---

## PoC+ Test Generation

### Output Checking (Deterministic)

Projects with native support for automated test generation:

| Project | Script Location |
|---------|-----------------|
| Hermes | `utils/updateErrorTest.py` |
| libxml2 | `codegen/genTestApi.py` |
| LLVM | `llvm/utils/update_*_test_checks.py` |
| PHP | `scripts/dev/bless_tests.php` |
| Wabt | `test/run-tests.py` |

### Intermediate Checking (LLM-assisted)

```python
# Prompt template for generating intermediate checks
"""
You are an expert C/C++ programmer specializing in test code generation.
Given:
- harness.cc: A program that calls APIs but lacks checking
- dump.txt: Expected return values captured at runtime

Transform harness.cc into a robust test by adding assertions.
"""
```

### Self Checking (LLM Agent)

An iterative agent framework that:
1. Analyzes the patch to understand the bug fix
2. Selects appropriate testing patterns
3. Generates and executes tests
4. Refines based on feedback

---

## Implications for AVR Research

### Key Takeaways

1. **Current validation overestimates effectiveness** - 40%+ of "correct" patches fail rigorous testing

2. **Specification awareness is crucial** - Most false positives violate project specifications not inferable from code alone

3. **PoC+ tests provide reliable validation** - 70%+ semantic equivalence with developer patches

### Recommendations

- Adopt multi-layered validation beyond PoC + basic tests
- Incorporate specification information (docs, API references) into AVR systems
- Use PoC+ tests or similar approaches for comprehensive evaluation


### Areas for Contribution

- Adding new vulnerability cases to PVBench
- Improving PoC+ test generation methods
- Integrating additional AVR tools
- Documentation and examples


<div align="center">

**[Back to Top](#pvbench)**

Made with dedication for advancing Automated Vulnerability Repair research

</div>
