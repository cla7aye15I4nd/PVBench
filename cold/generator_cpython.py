#!/usr/bin/env python3
"""
Test code generator for CPython with feedback loop.

This module generates test code (generated_N.py) from poc.py and patch.diff,
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
        name="write_generated_py",
        description="Write the generated checking code to generated.py file. Args: code (str) - The complete Python code",
        params_json_schema=WriteArgs.model_json_schema(),
        on_invoke_tool=write_fn,
    )


def create_run_tool(output_path: Path, work_dir: Path, python_exec: str):
    """Create a run tool for executing the generated Python test."""
    async def run_fn(ctx, args: str) -> str:
        if not output_path.exists():
            return f"Error: {output_path.name} does not exist. Use write_generated_py first."

        try:
            env = os.environ.copy()
            env["TERM"] = "xterm"
            result = subprocess.run(
                [python_exec, str(output_path)],
                capture_output=True,
                text=True,
                timeout=60,
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
            return "Error: Script timed out after 60 seconds"
        except Exception as e:
            return f"Error running script: {e}"

    return FunctionTool(
        name="run_test",
        description="Run the generated test script and return the output.",
        params_json_schema={"type": "object", "properties": {}},
        on_invoke_tool=run_fn,
    )


BASE_INSTRUCTIONS = """You are an expert Python test engineer. Your task is to analyze a patch.diff file and a poc.py (proof of concept) file, then generate a comprehensive check.py-style test script.

## Your Goal
Transform a simple poc.py into a robust test by adding assertions that verify the expected behavior.

## Input Format

**poc.py** contains bare code that demonstrates a bug or vulnerability.

**patch.diff** shows the fix that was applied to CPython source code.

## CRITICAL RULES

1. **Understand the bug fix from patch.diff**
   - The patch shows what code was changed to fix the bug
   - Your test should verify that the fix works correctly

2. **Use the appropriate CHECK APIs**
   - For tests that might crash/segfault: use subprocess isolation
   - For tests that should raise exceptions: use try/except
   - For tests that should produce output: check stdout/stderr

3. **Keep tests minimal but comprehensive**
   - Test the fix works (no crash, correct behavior)
   - Test edge cases related to the fix
   - Add assertions with helpful error messages

## AVAILABLE CHECK APIS

### 1. Subprocess Isolation (for crash/segfault tests)
Use when the code might crash, segfault, or needs process isolation:

```python
from test.support.script_helper import assert_python_ok

code = \"\"\"if 1:
    # Your test code here
    import some_module
    some_module.function_that_might_crash()
\"\"\"

rc, out, err = assert_python_ok('-c', code)
```

### 2. Catching Unraisable Exceptions
Use for exceptions raised in __del__, callbacks, or other contexts where they can't be caught normally:

```python
from test import support

with support.catch_unraisable_exception() as cm:
    # Code that triggers unraisable exception
    do_something()
    assert cm.unraisable.exc_type == RuntimeError, f"Expected RuntimeError, got {cm.unraisable.exc_type}"
```

### 3. Direct Exception Testing
Use for testing that specific exceptions are raised:

```python
try:
    function_that_should_raise()
    assert False, "Expected SomeException"
except SomeException as e:
    assert "expected message" in str(e), f"Expected 'expected message' in error, got: {e}"
```

### 4. Async Tests
Use for asyncio-related tests:

```python
import asyncio

async def main():
    # async test code
    result = await some_async_function()
    assert result == expected, f"Expected {expected}, got {result}"

asyncio.run(main())
```

### 5. Function-Based Tests
Use for organizing multiple test cases:

```python
def test_case_one():
    # test code
    assert condition, "error message"

def test_case_two():
    # test code
    assert condition, "error message"

if __name__ == '__main__':
    test_case_one()
    test_case_two()
```

---

## CHECKABLE FIELDS

### For subprocess tests (assert_python_ok):
- **Return code**: `assert rc == 0, f"Expected return code 0, got: {rc}"`
- **Stdout content**: `assert b'expected' in out, f"Expected 'expected' in stdout, got: {out}"`
- **Stdout empty**: `assert out == b'', f"Expected empty stdout, got: {out}"`
- **Stderr content**: `assert b'ErrorType' in err, f"Expected 'ErrorType' in stderr, got: {err}"`
- **Stderr empty**: `assert err == b'', f"Expected empty stderr, got: {err}"` or `assert not err, f"Expected no stderr, got: {err}"`

### For unraisable exceptions:
- **Exception type**: `assert cm.unraisable.exc_type == RuntimeError, f"Expected RuntimeError, got {cm.unraisable.exc_type}"`

### For direct exception testing:
- **Exception raised**: Use try/except with `assert False, "Expected XException"` in try block
- **Exception message**: `assert "expected text" in str(e), f"Expected 'expected text' in error, got: {e}"`

### For return values and state:
- **Exact value**: `assert result == expected, f"Expected {expected}, got {result}"`
- **Type check**: `assert isinstance(obj, ExpectedType), f"Expected ExpectedType, got {type(obj)}"`
- **Attribute exists**: `assert hasattr(obj, 'attr'), "Missing attribute 'attr'"`
- **Dict key exists**: `assert 'key' in d, f"Expected 'key' in dict, got: {d.keys()}"`
- **Dict value**: `assert d['key'] == value, f"Expected {value}, got: {d['key']}"`
- **Is None**: `assert result is None, f"Expected None, got {result}"`

### Crash tests (no explicit assertion):
- If code reaches end without crash: `assert True` or just comment `# If we reach here without crash, the test passes`

---

## COMMON TEST PATTERNS

### Pattern 1: Testing exception is raised with correct type
```python
try:
    problematic_function(invalid_arg)
    assert False, "Expected TypeError"
except TypeError:
    pass
```

### Pattern 2: Testing exception message content
```python
try:
    function_with_bad_input()
    assert False, "Expected ValueError"
except ValueError as e:
    assert "invalid" in str(e), f"Expected 'invalid' in error, got: {e}"
```

### Pattern 3: Testing crash fix via subprocess
```python
from test.support.script_helper import assert_python_ok

code = \"\"\"if 1:
    import module
    # Code that used to crash but now should work
    module.fixed_function()
\"\"\"
rc, out, err = assert_python_ok("-c", code)
assert not err, f"Expected no stderr, got: {err}"
```

### Pattern 4: Testing use-after-free / mutation during iteration
```python
class Evil:
    def __eq__(self, other):
        container.clear()  # Mutate during comparison
        return NotImplemented

container = [Evil()]
try:
    container.index(0)
    assert False, "Expected RuntimeError"
except RuntimeError:
    pass
```

### Pattern 5: Testing boundary conditions
```python
# Test negative values
try:
    function_with_size(-1)
    assert False, "Expected ValueError"
except ValueError:
    pass

# Test minimum integer
try:
    function_with_size(-2147483648)
    assert False, "Expected ValueError"
except ValueError:
    pass

# Test valid edge case
function_with_size(0)  # Should not raise
```

### Pattern 6: Testing feature availability
```python
import module

if not hasattr(module, 'feature'):
    # Feature not available in this Python version, skip test
    pass
else:
    # Test the feature
    result = module.feature()
    assert result == expected
```

### Pattern 7: Testing with cleanup/finally
```python
old_value = module.setting
try:
    module.setting = test_value
    # Test code
    assert condition, "error"
finally:
    module.setting = old_value
```

---

## Workflow
1. Use write_generated_py to create generated.py with your test code
2. Use run_test to verify it works correctly
3. If there are errors, analyze them and fix the code
4. Iterate until the test passes

## Important Notes
- The generated.py should be self-contained and runnable
- Include proper imports at the top
- Add comments explaining what each test case verifies
- Make assertions specific with helpful error messages using f-strings
- Use `if 1:` block inside triple-quoted code strings for proper indentation
"""


FEEDBACK_TEMPLATE = """
## IMPORTANT: Previous Generation Failed

**Error Type:** {error_type}
**Error Message:**
```
{error_message}
```

**Your Previous Code:**
```python
{previous_code}
```

Please fix the issues and regenerate. Common issues:
- Import errors (missing modules)
- Incorrect assertion patterns
- Wrong expected behavior assumptions

Generate corrected code and call write_generated_py.
"""


# Type alias for validation function: (gen_file: Path) -> Tuple[success, error_type, error_message]
ValidateFn = Optional[callable]


def generate_test(case_dir: Path, gen_num: int,
                  validate_fn: ValidateFn = None) -> Tuple[str, int, bool, str]:
    """
    Generate test with feedback loop.

    Args:
        case_dir: Directory containing poc.py and patch.diff
        gen_num: Generation number (1, 2, 3)
        validate_fn: Validation function (gen_file: Path) -> (success, error_type, error_msg)
                    REQUIRED - must be provided by caller (uses built Python)

    Returns: (case_name, gen_num, success, message)
    """
    poc_path = case_dir / "poc.py"
    patch_path = case_dir / "patch.diff"
    output_path = case_dir / f"generated_{gen_num}.py"
    vuln_id = case_dir.name

    if not poc_path.exists():
        return case_dir.name, gen_num, False, "Missing poc.py"
    if not patch_path.exists():
        return case_dir.name, gen_num, False, "Missing patch.diff"
    if validate_fn is None:
        return case_dir.name, gen_num, False, "validate_fn is required"

    poc_content = poc_path.read_text()
    patch_content = patch_path.read_text()

    # Check for reference check.py
    check_path = case_dir / "check.py"
    reference_info = ""
    if check_path.exists():
        check_content = check_path.read_text()
        reference_info = f"""

## Reference check.py (for format reference only - create your own based on this style)
```python
{check_content}
```
"""

    base_prompt = f"""Please analyze the following files and generate a comprehensive test script that verifies the bug fix described in the patch.

## poc.py (Proof of Concept)
```python
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
   - Enriches the poc.py with additional test scenarios based on the patch
   - Uses the appropriate CHECK API from the system instructions (subprocess for crashes, direct for exceptions, etc.)
   - Adds assertions using the CHECKABLE FIELDS documented in the system instructions
   - Tests edge cases related to the fix

Please use the write_generated_py tool to create the test file, then use run_test to verify it works correctly. Iterate if needed to fix any issues.
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
        # Use system python for agent's run_test (quick sanity check)
        run_tool = create_run_tool(output_path, case_dir, "python")
        agent = Agent(
            name="PythonTestGenerator",
            instructions=instructions,
            tools=[write_tool, run_tool],
            model=MODEL,
        )

        prompt = base_prompt
        if round_num > 0:
            prompt += "\n\nIMPORTANT: You must call write_generated_py tool now."

        # Generate
        for attempt in range(MAX_RETRIES):
            try:
                Runner.run_sync(agent, prompt)
                if output_path.exists():
                    break
            except Exception as e:
                logger.warning(f"  [cpython] {vuln_id}/gen{gen_num}: Generation attempt {attempt+1} failed: {e}")
                continue

        if not output_path.exists():
            return case_dir.name, gen_num, False, f"Generation failed after {MAX_RETRIES} attempts"

        generated_code = output_path.read_text()

        # Validate using provided function (built Python)
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
            logger.info(f"  [cpython] {vuln_id}/gen{gen_num}: FAIL ({error_type}) - retrying with feedback")
        else:
            return case_dir.name, gen_num, False, f"FAIL ({error_type}): {error_message[:200]}"

    return case_dir.name, gen_num, False, f"Exhausted {MAX_FEEDBACK_ROUNDS} feedback rounds"
