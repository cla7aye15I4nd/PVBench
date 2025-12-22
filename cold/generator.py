#!/usr/bin/env python3
"""
Test code generator with feedback loop.

This module generates test code from harness.cc and dump.txt,
validates against developer patches, and regenerates with feedback on failure.

Runs entirely inside Docker with the project's build environment.

Usage (inside Docker):
    COLD_ACTION=gentest-gen python -m cold.cli [--id VULN_ID]
"""

import sys
import os
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Tuple, Dict, List

from agents import Agent, Runner, FunctionTool
from pydantic import BaseModel

from cold.env import SOURCE, GENTEST, MAX_PROC
from cold.logger import logger

# Configuration
DOCS_DIR = GENTEST / "docs"
PROJ_DIR = GENTEST / "proj"

MAX_RETRIES = 3
MAX_FEEDBACK_ROUNDS = 2
NUM_GENERATIONS = 3
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1")


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


BASE_INSTRUCTIONS = """You are an expert C/C++ programmer specializing in test code generation for library APIs.

## Task Background

You are working on a vulnerability testing benchmark. Each test case has:
- **harness.cc**: A minimal test program that calls library APIs but lacks assertions
- **dump.txt**: Documents expected behavior - which calls should succeed or fail

Your job is to transform harness.cc into a robust test by adding assertions that verify the expected behavior.

## Input Format

**harness.cc** contains bare API calls without return value checking.

**dump.txt** uses format: `line|function_call|expected_result|comment`
- If it says "No expected failures", all operations should succeed
- If it lists specific failures, those calls should return error values

## CRITICAL RULES

1. **Use EXACT same types and function signatures as harness.cc**
   - Do NOT change variable types
   - Do NOT add extra parameters to function calls
   - Copy types and function calls EXACTLY from harness.cc

2. **Follow dump.txt for expected behavior**
   - If dump.txt says "No expected failures", assert success for all calls
   - If dump.txt lists specific failures, assert those return errors

3. **Keep tests minimal**
   - Only add assertions for return values
   - Do NOT add assertions about file properties or argc
   - Do NOT add any extra operations not in the original harness.cc

## Output Requirements

1. Add `#include <assert.h>` (C) or `#include <cassert>` (C++)
2. Capture return values and add assertions
3. Keep original code structure intact

## API Reference
{api_docs}

## Action Required
After generating the code, you MUST call the write_generated_cc tool to save it.
"""


FEEDBACK_TEMPLATE = """
## IMPORTANT: Previous Generation Failed

**Error Type:** {error_type}
**Error Message:**
```
{error_message}
```

**Your Previous Code:**
```cpp
{previous_code}
```

Please fix the issues and regenerate. Common issues:
- Missing parameters in API calls (check documentation)
- Using wrong assertion patterns for return types
- Adding unnecessary assertions (argc, file properties)

Generate corrected code and call write_generated_cc.
"""


def get_compile_command(project: str, build_path: Path, gen_file: Path, output_file: Path,
                        build_env: Dict[str, str]) -> List[str]:
    """Get compile command for a specific project."""
    install_dir = build_path / "install"
    cc = build_env.get("CC", "gcc")
    cxx = build_env.get("CXX", "g++")
    cflags = build_env.get("CFLAGS", "").split()
    cxxflags = build_env.get("CXXFLAGS", "").split()
    ldflags = build_env.get("LDFLAGS", "").split()

    if project == "icu":
        cmd = [cxx] + cxxflags + [
            "-I", str(install_dir / "include"),
            "-L", str(install_dir / "lib"),
            "-licuuc", "-licui18n", "-licudata",
            f"-Wl,-rpath,{install_dir / 'lib'}",
        ] + ldflags + ["-o", str(output_file), str(gen_file)]
    elif project == "hdf5":
        cmd = [cc] + cflags + [
            "-I", str(install_dir / "include"),
            "-L", str(install_dir / "lib"),
            "-lhdf5",
            f"-Wl,-rpath={install_dir / 'lib'}",
        ] + ldflags + ["-o", str(output_file), str(gen_file)]
    elif project == "pcapplusplus":
        cmd = [cxx] + cxxflags + [
            "-I", str(install_dir / "include" / "pcapplusplus"),
            "-L", str(install_dir / "lib"),
            "-lPcap++", "-lCommon++", "-lPacket++",
            f"-Wl,-rpath={install_dir / 'lib'}",
        ] + ldflags + ["-o", str(output_file), str(gen_file)]
    elif project == "libtiff":
        cmd = [cc] + cflags + [
            "-I", str(install_dir / "include"),
            "-L", str(install_dir / "lib"),
            "-ltiff", "-lz", "-ljpeg", "-llzma",
            f"-Wl,-rpath={install_dir / 'lib'}",
        ] + ldflags + ["-o", str(output_file), str(gen_file)]
    else:
        raise ValueError(f"Unknown project: {project}")

    return [x for x in cmd if x]


def validate_test(project: str, vuln_id: str, gen_file: Path) -> Tuple[bool, str, str]:
    """
    Validate generated test against developer patch.

    Returns: (success, error_type, error_message)
    """
    from cold.builder import ColdBuilder
    from patchagent.builder.utils import BuilderProcessError, BuilderTimeoutError

    try:
        builder = ColdBuilder(vuln_id)

        # Read developer patch
        patch_path = SOURCE / vuln_id / "patch.diff"
        if not patch_path.exists():
            return False, "missing", f"No developer patch found at {patch_path}"
        dev_patch = patch_path.read_text()

        # Build with developer patch
        try:
            builder.build(dev_patch)
        except (BuilderProcessError, BuilderTimeoutError) as e:
            return False, "build", f"Failed to build with developer patch: {e}"

        test_binary = builder.build_path / ".test_binary"

        # Get compile command
        compile_cmd = get_compile_command(project, builder.build_path, gen_file, test_binary, builder.build_env)

        # Compile
        result = subprocess.run(compile_cmd, capture_output=True, timeout=120)
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace")[:4000]
            return False, "compile", stderr

        # Run test
        input_dir = SOURCE / vuln_id / "input"
        input_files = list(input_dir.iterdir()) if input_dir.is_dir() else []
        run_cmd = [str(test_binary)]
        if input_files:
            run_cmd.append(str(input_files[0].resolve()))

        result = subprocess.run(run_cmd, capture_output=True, timeout=60, cwd=builder.build_path)

        # Clean up
        if test_binary.exists():
            test_binary.unlink()

        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace")[:4000]
            return False, "runtime", stderr or f"Exit code {result.returncode}"

        return True, "", ""

    except Exception as e:
        import traceback
        return False, "exception", f"{e}\n{traceback.format_exc()[:2000]}"


def get_project_for_vuln_id(vuln_id: str) -> Optional[str]:
    """Determine project from vulnerability ID."""
    for proj_dir in PROJ_DIR.iterdir():
        if proj_dir.is_dir():
            case_dir = proj_dir / vuln_id
            if case_dir.exists():
                return proj_dir.name
    return None


def generate_test(case_dir: Path, project: str, gen_num: int,
                  use_feedback: bool = True) -> Tuple[str, int, bool, str]:
    """
    Generate test with optional feedback loop.

    Returns: (case_name, gen_num, success, message)
    """
    harness_path = case_dir / "harness.cc"
    dump_path = case_dir / "dump.txt"
    gen_dir = case_dir / f"generated{gen_num}"
    output_path = gen_dir / "generated.cc"
    vuln_id = case_dir.name

    if not harness_path.exists() or not dump_path.exists():
        return case_dir.name, gen_num, False, "Missing harness.cc or dump.txt"

    gen_dir.mkdir(exist_ok=True)

    # Load API docs
    doc_path = DOCS_DIR / f"{project}.txt"
    api_docs = doc_path.read_text() if doc_path.exists() else ""

    harness_content = harness_path.read_text()
    dump_content = dump_path.read_text()
    base_prompt = f"harness.cc:\n```cpp\n{harness_content}```\n\ndump.txt:\n```\n{dump_content}```"

    feedback_history: List[Dict] = []
    max_rounds = MAX_FEEDBACK_ROUNDS + 1 if use_feedback else 1

    for round_num in range(max_rounds):
        # Build instructions with feedback if available
        if feedback_history:
            last = feedback_history[-1]
            feedback_section = FEEDBACK_TEMPLATE.format(
                error_type=last["error_type"],
                error_message=last["error_message"],
                previous_code=last["code"]
            )
            instructions = BASE_INSTRUCTIONS.format(api_docs=api_docs) + feedback_section
        else:
            instructions = BASE_INSTRUCTIONS.format(api_docs=api_docs)

        write_tool = create_write_tool(output_path)
        agent = Agent(
            name="CodeGenerator",
            instructions=instructions,
            tools=[write_tool],
            model=MODEL,
        )

        prompt = base_prompt
        if round_num > 0:
            prompt += "\n\nIMPORTANT: You must call write_generated_cc tool now."

        # Generate
        for attempt in range(MAX_RETRIES):
            try:
                Runner.run_sync(agent, prompt)
                if output_path.exists():
                    break
            except Exception as e:
                logger.warning(f"  [{project}] {vuln_id}/gen{gen_num}: Generation attempt {attempt+1} failed: {e}")
                continue

        if not output_path.exists():
            return case_dir.name, gen_num, False, f"Generation failed after {MAX_RETRIES} attempts"

        generated_code = output_path.read_text()

        # Validate
        success, error_type, error_message = validate_test(project, vuln_id, output_path)

        if success:
            return case_dir.name, gen_num, True, f"OK (round {round_num + 1})"

        if use_feedback and round_num < max_rounds - 1:
            feedback_history.append({
                "error_type": error_type,
                "error_message": error_message,
                "code": generated_code
            })
            output_path.unlink()
            logger.info(f"  [{project}] {vuln_id}/gen{gen_num}: FAIL ({error_type}) - retrying with feedback")
        else:
            return case_dir.name, gen_num, False, f"FAIL ({error_type}): {error_message[:200]}"

    return case_dir.name, gen_num, False, f"Exhausted {MAX_FEEDBACK_ROUNDS} feedback rounds"


def find_cases_for_vuln_id(vuln_id: str) -> Optional[Tuple[Path, str]]:
    """Find case directory for a vulnerability ID."""
    project = get_project_for_vuln_id(vuln_id)
    if project:
        case_dir = PROJ_DIR / project / vuln_id
        if case_dir.exists():
            return case_dir, project
    return None


def find_all_cases_for_project(project: str) -> List[Tuple[Path, str]]:
    """Find all cases for a specific project."""
    cases = []
    proj_path = PROJ_DIR / project
    if proj_path.exists():
        for d in proj_path.iterdir():
            if d.is_dir() and (d / "harness.cc").exists():
                cases.append((d, project))
    return cases


def run_generate(vuln_id: Optional[str] = None, use_feedback: bool = True, workers: int = MAX_PROC):
    """Run generation for specific vulnerability or all in current project."""
    if vuln_id:
        result = find_cases_for_vuln_id(vuln_id)
        if not result:
            logger.error(f"Vulnerability {vuln_id} not found in gentest directory")
            return 1
        cases = [result]
    else:
        # Find all cases for the current project (based on SOURCE directory)
        # Determine project from SOURCE path
        project = None
        for proj_dir in PROJ_DIR.iterdir():
            if proj_dir.is_dir():
                # Check if any vuln in this project matches testcases
                for vuln_dir in proj_dir.iterdir():
                    if vuln_dir.is_dir():
                        testcase_path = SOURCE / vuln_dir.name
                        if testcase_path.exists():
                            project = proj_dir.name
                            break
                if project:
                    break

        if not project:
            logger.error("Could not determine project from SOURCE directory")
            return 1

        cases = find_all_cases_for_project(project)

    if not cases:
        logger.error("No cases found")
        return 1

    tasks = [(case_dir, project, gen_num)
             for case_dir, project in cases
             for gen_num in range(1, NUM_GENERATIONS + 1)]

    logger.info(f"[🔧] Processing {len(cases)} cases x {NUM_GENERATIONS} generations = {len(tasks)} tasks")
    logger.info(f"[🔧] Feedback loop: {'enabled' if use_feedback else 'disabled'}")
    logger.info(f"[🔧] Model: {MODEL}")

    success = 0
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(generate_test, case_dir, project, gen_num, use_feedback): (case_dir, project, gen_num)
                   for case_dir, project, gen_num in tasks}

        for future in as_completed(futures):
            case_dir, project, gen_num = futures[future]
            try:
                case_name, _, ok, msg = future.result()
                status = "✅" if ok else "❌"
                logger.info(f"  [{status}][{project}] {case_name}/gen{gen_num}: {msg}")
                if ok:
                    success += 1
            except Exception as e:
                logger.error(f"  [🚨][{project}] {case_dir.name}/gen{gen_num}: ERROR - {e}")

    logger.info(f"[📊] Summary: {success}/{len(tasks)} succeeded")
    return 0 if success == len(tasks) else 1


def run_fix_invalid(use_feedback: bool = True, workers: int = MAX_PROC):
    """Find and regenerate invalid tests."""
    # Find invalid tests based on archive
    from cold.env import ARCHIVE
    archive_gentest = ARCHIVE / "gentest"

    if not archive_gentest.exists():
        logger.info("No gentest archive found")
        return 0

    invalid_tests = []
    for vuln_dir in archive_gentest.iterdir():
        if not vuln_dir.is_dir():
            continue
        vuln_id = vuln_dir.name
        project = get_project_for_vuln_id(vuln_id)
        if not project:
            continue

        for invalid_file in vuln_dir.glob("dev:gen*.invalid.json"):
            try:
                name = invalid_file.stem
                gen_num = int(name.split("gen")[1].split(".")[0])
                case_dir = PROJ_DIR / project / vuln_id
                if case_dir.exists():
                    invalid_tests.append((case_dir, project, gen_num, invalid_file))
            except (IndexError, ValueError):
                continue

    if not invalid_tests:
        logger.info("No invalid tests found")
        return 0

    logger.info(f"[🔧] Found {len(invalid_tests)} invalid tests")

    # Delete generated.cc files and invalid.json markers
    for case_dir, project, gen_num, invalid_file in invalid_tests:
        gen_file = case_dir / f"generated{gen_num}" / "generated.cc"
        if gen_file.exists():
            gen_file.unlink()
            logger.info(f"  Deleted: {gen_file}")
        if invalid_file.exists():
            invalid_file.unlink()
            logger.info(f"  Deleted: {invalid_file}")

    # Regenerate
    logger.info("[🔧] Regenerating...")
    tasks = [(case_dir, project, gen_num) for case_dir, project, gen_num, _ in invalid_tests]

    success = 0
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(generate_test, case_dir, project, gen_num, use_feedback): (case_dir, project, gen_num)
                   for case_dir, project, gen_num in tasks}

        for future in as_completed(futures):
            case_dir, project, gen_num = futures[future]
            try:
                case_name, _, ok, msg = future.result()
                status = "✅" if ok else "❌"
                logger.info(f"  [{status}][{project}] {case_name}/gen{gen_num}: {msg}")
                if ok:
                    success += 1
            except Exception as e:
                logger.error(f"  [🚨][{project}] {case_dir.name}/gen{gen_num}: ERROR - {e}")

    logger.info(f"[📊] Summary: {success}/{len(tasks)} regenerated")
    return 0 if success == len(tasks) else 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate test code with feedback loop")
    parser.add_argument("--id", type=str, help="Specific vulnerability ID to process")
    parser.add_argument("--no-feedback", action="store_true", help="Disable feedback loop")
    parser.add_argument("--fix-invalid", action="store_true", help="Find and fix invalid tests")
    parser.add_argument("--workers", type=int, default=MAX_PROC, help="Number of workers")

    args = parser.parse_args()
    use_feedback = not args.no_feedback

    if args.fix_invalid:
        sys.exit(run_fix_invalid(use_feedback, args.workers))
    else:
        sys.exit(run_generate(args.id, use_feedback, args.workers))
