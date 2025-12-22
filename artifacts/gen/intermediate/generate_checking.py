#!/usr/bin/env python3
"""
Generate generated.cc from harness.cc and dump.txt using OpenAI Agents SDK.
"""

import sys
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from agents import Agent, Runner, FunctionTool
from pydantic import BaseModel

SCRIPT_DIR = Path(__file__).parent
PROJ_DIR = SCRIPT_DIR / "proj"
DOCS_DIR = SCRIPT_DIR / "docs"
MAX_RETRIES = 3
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", 4))
NUM_GENERATIONS = 3  # Generate 3 independent versions


class WriteArgs(BaseModel):
    code: str


def create_write_tool(output_path: Path):
    """Create a write tool bound to specific output path."""
    async def write_fn(ctx, args: str) -> str:
        parsed = WriteArgs.model_validate_json(args)
        output_path.write_text(parsed.code)
        return "File written successfully"

    return FunctionTool(
        name="write_generated_cc",
        description="Write the generated checking code to generated.cc file. Args: code (str) - The complete C/C++ code",
        params_json_schema=WriteArgs.model_json_schema(),
        on_invoke_tool=write_fn,
    )


INSTRUCTIONS = """You are an expert C/C++ programmer specializing in test code generation for library APIs.

## Task Background

You are working on a vulnerability testing benchmark. Each test case has:
- **harness.cc**: A minimal test program that calls library APIs but lacks assertions
- **dump.txt**: Documents expected behavior - which calls should succeed or fail

Your job is to transform harness.cc into a robust test by adding assertions that verify the expected behavior.

## Input Format

**harness.cc** contains bare API calls without return value checking. Example:
```cpp
hid_t fid = H5Fopen(filename, H5F_ACC_RDONLY, H5P_DEFAULT);
H5Fclose(fid);
```

**dump.txt** uses format: `line|function_call|expected_result|comment`
- If it says "No expected failures", all operations should succeed
- If it lists specific failures, those calls should return error values (e.g., `return == -1`)

## CRITICAL RULES

1. **Use EXACT same types and function signatures as harness.cc**
   - Do NOT change `H5O_info_t` to `H5O_info2_t`
   - Do NOT add extra parameters to function calls
   - Do NOT use constants that don't exist (e.g., `H5O_INFO_ALL`, `H5L_INFO_ALL`)
   - Copy types and function calls EXACTLY from harness.cc

2. **Follow dump.txt for expected behavior**
   - If dump.txt lists a function with `return == -1`, assert it returns error
   - If dump.txt says "No expected failures", assert success for all calls
   - Do NOT assume success if dump.txt says failure is expected

3. **Keep tests minimal - avoid over-strict assertions**
   - Only add assertions for return values and explicitly documented behavior
   - Do NOT add assertions about file properties (e.g., `totalDirs >= 1`)
   - The test input may be malformed/corrupted - don't assume valid file structure
   - Focus on API behavior, not input file validity

## Output Requirements

1. Add `#include <assert.h>` (C) or `#include <cassert>` (C++)
2. Capture return values and add assertions:
   - Success: `assert(ret >= 0)` or `assert(ptr != NULL)`
   - Expected failure: `assert(ret == -1)` or `assert(ret < 0)`
3. Keep original code structure and logic intact
4. Add necessary variable declarations (e.g., `herr_t ret;`)
5. **Semantic assertions** (optional, only for documented behavior):
   - Values within valid ranges (e.g., `assert(month <= maxMonth)`)
   - Only add if you're confident it won't fail on malformed input

## Example Transformations

**Example 1 - Success case:**
```cpp
// Before (harness.cc):
hid_t fid = H5Fopen(file, H5F_ACC_RDONLY, H5P_DEFAULT);
H5Fclose(fid);

// dump.txt: No expected failures

// After:
#include <assert.h>
hid_t fid = H5Fopen(file, H5F_ACC_RDONLY, H5P_DEFAULT);
assert(fid >= 0);
herr_t ret = H5Fclose(fid);
assert(ret >= 0);
```

**Example 2 - Expected failure case:**
```cpp
// Before (harness.cc):
H5L_info2_t linfo;
H5Lget_info2(H5Tcopy(H5T_NATIVE_INT), argv[1], &linfo, H5P_DEFAULT);

// dump.txt: 6|H5Lget_info2|return == -1|Invalid loc_id

// After:
#include <assert.h>
H5L_info2_t linfo;
hid_t dtype = H5Tcopy(H5T_NATIVE_INT);
assert(dtype >= 0);
herr_t ret = H5Lget_info2(dtype, argv[1], &linfo, H5P_DEFAULT);
assert(ret == -1);  // Expected to fail per dump.txt
H5Tclose(dtype);
```

## API Reference
{api_docs}

## Action Required
After generating the code, you MUST call the write_generated_cc tool to save it.
"""


def process_single_generation(case_dir: Path, project: str, gen_num: int) -> tuple[str, int, bool]:
    """Process a single generation for a test case. Returns (case_name, gen_num, success)."""
    harness_path = case_dir / "harness.cc"
    dump_path = case_dir / "dump.txt"
    gen_dir = case_dir / f"generated{gen_num}"
    output_path = gen_dir / "generated.cc"

    if not harness_path.exists() or not dump_path.exists():
        return case_dir.name, gen_num, False

    if output_path.exists():
        return case_dir.name, gen_num, True

    # Create generation directory
    gen_dir.mkdir(exist_ok=True)

    doc_path = DOCS_DIR / f"{project}.txt"
    api_docs = doc_path.read_text() if doc_path.exists() else ""

    write_tool = create_write_tool(output_path)
    agent = Agent(
        name="CodeGenerator",
        instructions=INSTRUCTIONS.format(api_docs=api_docs),
        tools=[write_tool],
        model="gpt-5",
    )

    base_prompt = f"harness.cc:\n```cpp\n{harness_path.read_text()}```\n\ndump.txt:\n```\n{dump_path.read_text()}```"

    for attempt in range(1, MAX_RETRIES + 1):
        prompt = base_prompt if attempt == 1 else f"{base_prompt}\n\nIMPORTANT: You must call write_generated_cc tool now."
        Runner.run_sync(agent, prompt)
        if output_path.exists():
            return case_dir.name, gen_num, True

    return case_dir.name, gen_num, False


def find_all_cases() -> list[tuple[Path, str]]:
    """Find all cases as (case_dir, project) tuples."""
    cases = []
    for p in PROJ_DIR.iterdir():
        if p.is_dir() and p.name != "docs":
            for d in p.iterdir():
                if d.is_dir() and (d / "harness.cc").exists():
                    cases.append((d, p.name))
    return cases


def run_all():
    """Run all cases with multiprocessing."""
    all_cases = find_all_cases()
    assert all_cases, "No cases found"

    # Create tasks for all cases x generations
    all_tasks = [(case_dir, project, gen_num)
                 for case_dir, project in all_cases
                 for gen_num in range(1, NUM_GENERATIONS + 1)]

    print(f"Processing {len(all_cases)} cases x {NUM_GENERATIONS} generations = {len(all_tasks)} tasks with {MAX_WORKERS} workers...")

    success = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_single_generation, case_dir, project, gen_num): (case_dir, project, gen_num)
                   for case_dir, project, gen_num in all_tasks}

        for future in as_completed(futures):
            case_dir, project, gen_num = futures[future]
            case_name, _, ok = future.result()
            status = "OK" if ok else "SKIP/FAIL"
            print(f"  [{project}] {case_name}/generated{gen_num}: {status}")
            if ok:
                success += 1

    print(f"\nSummary: {success}/{len(all_tasks)}")
    return 0


def run_single(case_path: str):
    """Run single case."""
    case_dir = Path(case_path)
    assert case_dir.is_dir(), f"{case_path} is not a directory"
    project = case_dir.parent.name
    print(f"Project: {project}, Case: {case_dir.name}")

    all_ok = True
    for gen_num in range(1, NUM_GENERATIONS + 1):
        _, _, ok = process_single_generation(case_dir, project, gen_num)
        status = "OK" if ok else "FAIL"
        print(f"  generated{gen_num}: {status}")
        if not ok:
            all_ok = False

    return 0 if all_ok else 1


def main():
    if len(sys.argv) == 1:
        return run_all()
    elif len(sys.argv) == 2:
        return run_single(sys.argv[1])
    print("Usage: python generate_checking.py [case_path]")
    return 1


if __name__ == "__main__":
    sys.exit(main())
