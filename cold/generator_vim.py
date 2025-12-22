#!/usr/bin/env python3
"""
Test code generator for Vim with feedback loop.

This module generates test code (generated_N.vim) from poc.vim and patch.diff,
validates using provided validate_fn, and regenerates with feedback on failure.
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from agents import Agent, FunctionTool, Runner
from pydantic import BaseModel

from cold.env import MAX_PROC
from cold.logger import logger

# Configuration
MAX_RETRIES = 3
MAX_FEEDBACK_ROUNDS = 2
MODEL = os.environ.get("OPENAI_MODEL", "gpt-5")


class WriteArgs(BaseModel):
    code: str


def create_write_tool(output_path: Path):
    """Create a write tool bound to specific output path."""
    async def write_fn(ctx, args: str) -> str:
        parsed = WriteArgs.model_validate_json(args)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(parsed.code)
        return "File written successfully"

    return FunctionTool(
        name="write_generated_vim",
        description="Write the generated checking code to generated.vim file. Args: code (str) - The complete Vimscript code",
        params_json_schema=WriteArgs.model_json_schema(),
        on_invoke_tool=write_fn,
    )


def create_run_tool(output_path: Path, work_dir: Path, vim_exec: str):
    """Create a run tool for executing the generated Vim test."""
    async def run_fn(ctx, args: str) -> str:
        if not output_path.exists():
            return f"Error: {output_path.name} does not exist. Use write_generated_vim first."

        try:
            env = os.environ.copy()
            env["TERM"] = "xterm"
            # Run vim in Ex mode (-e) and silent mode (-s) with the script
            # -u NONE to skip loading vimrc
            # -N for nocompatible mode
            cmd = [vim_exec, "-e", "-s", "-N", "-u", "NONE", "-S", str(output_path)]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(work_dir),
                env=env
            )
            output = f"Exit code: {result.returncode}\n"
            if result.stdout:
                output += f"STDOUT:\n{result.stdout}\n"
            if result.stderr:
                output += f"STDERR:\n{result.stderr}\n"
            return output.strip() or "Script ran successfully with no output"
        except subprocess.TimeoutExpired:
            return "Error: Script timed out after 30 seconds"
        except Exception as e:
            return f"Error running script: {e}"

    return FunctionTool(
        name="run_test",
        description="Run the generated test script and return the output.",
        params_json_schema={"type": "object", "properties": {}},
        on_invoke_tool=run_fn,
    )


BASE_INSTRUCTIONS = """You are an expert Vimscript test engineer. Your task is to analyze a patch.diff file and a poc.vim (proof of concept) file, then generate a comprehensive test script for Vim.

## Your Goal
Transform a simple poc.vim into a robust test by adding checks that verify the expected behavior after the bug fix.

## Input Format

**poc.vim** contains Vimscript code that demonstrates a bug or vulnerability in Vim.

**patch.diff** shows the fix that was applied to Vim source code.

## CRITICAL RULES

1. **Understand the bug fix from patch.diff**
   - The patch shows what code was changed to fix the bug
   - Your test should verify that the fix works correctly

2. **The test runs in Ex mode (-e -s)**
   - Vim runs in silent Ex mode, not interactive
   - Use `qall!` at the end to exit cleanly
   - Use `echo` or write to files for output

3. **Keep tests minimal but comprehensive**
   - Test the fix works (no crash, correct behavior)
   - Test edge cases related to the fix

## AVAILABLE CHECK PATTERNS

### 1. Basic Assertion
```vim
let result = SomeFunction()
if result != expected
    echoerr 'Expected ' . expected . ', got ' . result
    cquit 1
endif
```

### 2. No-Crash Testing
```vim
" If this command used to crash, just execute it
" If we reach the end without crash, the fix works
try
    exe 'command that might crash'
catch
    echoerr 'Unexpected error: ' . v:exception
    cquit 1
endtry
qall!
```

### 3. Testing Buffer Operations
```vim
new
call setline(1, ['line1', 'line2', 'line3'])
" perform operation
let lines = getline(1, '$')
if lines != ['expected1', 'expected2']
    echoerr 'Unexpected content'
    cquit 1
endif
qall!
```

### 4. Testing Help/Documentation
```vim
" For help-related bugs
try
    exe 'help topic'
catch
    " Expected if help not available, that's OK
endtry
qall!
```

### 5. Testing with repeat()
```vim
" For overflow/boundary bugs
let longstr = repeat('x', 1000)
try
    " operation with longstr
catch
    echoerr 'Error: ' . v:exception
    cquit 1
endtry
qall!
```

---

## Workflow
1. Use write_generated_vim to create generated.vim with your test code
2. Use run_test to verify it works correctly
3. If there are errors, analyze them and fix the code
4. Iterate until the test passes

## Important Notes
- The generated.vim runs with: vim -e -s -N -u NONE -S generated.vim
- Always end with `qall!` to exit cleanly
- Use `cquit 1` to exit with error status
- Use `echoerr` to output error messages (goes to stderr)
- Use `echo` for regular output (goes to stdout, but may not show in -s mode)
- For testing crashes, the test passes if Vim doesn't crash
- Don't rely on user's .vimrc (we use -u NONE)
"""


FEEDBACK_TEMPLATE = """
## IMPORTANT: Previous Generation Failed

**Error Type:** {error_type}
**Error Message:**
```
{error_message}
```

**Your Previous Code:**
```vim
{previous_code}
```

Please fix the issues and regenerate. Common issues:
- Missing `qall!` at the end (script hangs)
- Using interactive commands that don't work in Ex mode
- Incorrect Vimscript syntax
- Missing error handling

Generate corrected code and call write_generated_vim.
"""


# Type alias for validation function: (gen_file: Path) -> Tuple[success, error_type, error_message]
ValidateFn = Optional[callable]


def generate_test(case_dir: Path, gen_num: int,
                  validate_fn: ValidateFn = None) -> Tuple[str, int, bool, str]:
    """
    Generate test with feedback loop.

    Args:
        case_dir: Directory containing poc.vim and patch.diff
        gen_num: Generation number (1, 2, 3)
        validate_fn: Validation function (gen_file: Path) -> (success, error_type, error_msg)
                    REQUIRED - must be provided by caller (uses built vim)

    Returns: (case_name, gen_num, success, message)
    """
    poc_path = case_dir / "poc.vim"
    patch_path = case_dir / "patch.diff"
    output_path = case_dir / f"generated_{gen_num}.vim"
    vuln_id = case_dir.name

    if not poc_path.exists():
        return case_dir.name, gen_num, False, "Missing poc.vim"
    if not patch_path.exists():
        return case_dir.name, gen_num, False, "Missing patch.diff"
    if validate_fn is None:
        return case_dir.name, gen_num, False, "validate_fn is required"

    # Read files with error handling for binary/non-UTF-8 content
    try:
        poc_content = poc_path.read_text(errors='replace')
    except Exception as e:
        # If file is truly binary, read as bytes and show hex representation
        poc_bytes = poc_path.read_bytes()
        poc_content = f"[Binary file - {len(poc_bytes)} bytes]\nHex dump:\n" + poc_bytes[:200].hex()

    try:
        patch_content = patch_path.read_text(errors='replace')
    except Exception as e:
        return case_dir.name, gen_num, False, f"Cannot read patch.diff: {e}"

    # Check for reference check.vim
    check_path = case_dir / "check.vim"
    reference_info = ""
    if check_path.exists():
        try:
            check_content = check_path.read_text(errors='replace')
        except Exception:
            check_content = "[Binary content - cannot display]"
        reference_info = f"""

## Reference check.vim (for format reference only - create your own based on this style)
```vim
{check_content}
```
"""

    base_prompt = f"""Please analyze the following files and generate a comprehensive test script that verifies the bug fix described in the patch.

## poc.vim (Proof of Concept)
```vim
{poc_content}
```

## patch.diff
```diff
{patch_content}
```
{reference_info}
## Task
1. Analyze the patch to understand what bug is being fixed
2. Create the test file that:
   - Enriches the poc.vim with additional test scenarios based on the patch
   - Uses appropriate Vimscript patterns for testing
   - Tests edge cases related to the fix
   - Ends with `qall!` to exit cleanly

Please use the write_generated_vim tool to create the test file, then use run_test to verify it works correctly. Iterate if needed to fix any issues.
"""

    feedback_history: List[Dict] = []
    max_rounds = MAX_FEEDBACK_ROUNDS + 1

    for round_num in range(max_rounds):
        # Build instructions with feedback if available
        if feedback_history:
            last = feedback_history[-1]
            feedback_section = FEEDBACK_TEMPLATE.format(
                error_type=last["error_type"],
                error_message=last["error_message"],
                previous_code=last["code"]
            )
            instructions = BASE_INSTRUCTIONS + feedback_section
        else:
            instructions = BASE_INSTRUCTIONS

        write_tool = create_write_tool(output_path)
        # Use system vim for agent's run_test (quick sanity check)
        run_tool = create_run_tool(output_path, case_dir, "vim")
        agent = Agent(
            name="VimTestGenerator",
            instructions=instructions,
            tools=[write_tool, run_tool],
            model=MODEL,
        )

        prompt = base_prompt
        if round_num > 0:
            prompt += "\n\nIMPORTANT: You must call write_generated_vim tool now."

        # Generate
        for attempt in range(MAX_RETRIES):
            try:
                Runner.run_sync(agent, prompt)
                if output_path.exists():
                    break
            except Exception as e:
                logger.warning(f"  [vim] {vuln_id}/gen{gen_num}: Generation attempt {attempt+1} failed: {e}")
                continue

        if not output_path.exists():
            return case_dir.name, gen_num, False, f"Generation failed after {MAX_RETRIES} attempts"

        generated_code = output_path.read_text()

        # Validate using provided function (built vim)
        success, error_type, error_message = validate_fn(output_path)

        if success:
            return case_dir.name, gen_num, True, f"OK (round {round_num + 1})"

        if round_num < max_rounds - 1:
            feedback_history.append({
                "error_type": error_type,
                "error_message": error_message,
                "code": generated_code
            })
            output_path.unlink()
            logger.info(f"  [vim] {vuln_id}/gen{gen_num}: FAIL ({error_type}) - retrying with feedback")
        else:
            return case_dir.name, gen_num, False, f"FAIL ({error_type}): {error_message[:200]}"

    return case_dir.name, gen_num, False, f"Exhausted {MAX_FEEDBACK_ROUNDS} feedback rounds"
