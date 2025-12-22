#!/usr/bin/env python3
"""
OpenAI Agents SDK script for generating check.py from poc.py based on patch.diff analysis.

This agent:
1. Analyzes the patch.diff to understand the bug fix
2. Enriches the poc.py with additional test scenarios
3. Adds assertions to verify expected behavior
4. Generates generated.py similar to check.py

Tools:
- write_code: Write Python code to a file
- run_test: Execute the generated test script

Usage:
    pip install openai-agents
    python generate_check_agent.py              # Run all py-pr-* cases
    python generate_check_agent.py [case_path]  # Run single case
"""

import asyncio
import logging
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from agents import Agent, Runner, function_tool


SCRIPT_DIR = Path(__file__).parent
MAX_RETRIES = 3
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", 4))
NUM_GENERATIONS = 3  # Number of generated.py files to create per case


def setup_case_logger(case_dir: Path) -> logging.Logger:
    """Setup a no-op logger (logging disabled)."""
    logger = logging.getLogger(f"case_{case_dir.name}")
    logger.setLevel(logging.CRITICAL + 1)  # Disable all logging
    logger.handlers.clear()
    return logger


SYSTEM_INSTRUCTIONS = """You are an expert Python test engineer. Your task is to analyze a patch.diff file and a poc.py (proof of concept) file, then generate a comprehensive check.py-style test script.

## Your Goal
Transform a simple poc.py into a robust check script (generated.py) that:
1. Verifies the bug is fixed by the patch
2. Uses proper test infrastructure
3. Includes assertions that verify expected behavior
4. Handles edge cases related to the bug fix

## Analysis Process
1. First, understand what bug the patch is fixing by analyzing the diff
2. Understand the original proof of concept (poc.py)
3. Enrich the test with more comprehensive scenarios based on the patch
4. Add assertions to verify expected behavior after the fix

---

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
1. Use write_code to create generated.py with your test code
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


def create_tools(work_dir: Path, output_filename: str, case_logger: logging.Logger):
    """Create tools with context captured via closure."""
    output_path = work_dir / output_filename

    @function_tool
    def write_code(content: str) -> str:
        """Write Python code to the generated test file.

        Args:
            content: The Python code content to write
        """
        case_logger.info(f"[TOOL] write_code({output_filename})")
        case_logger.info(f"Content:\n{content}")

        if output_path.exists():
            result = f"Skipping - {output_filename} already exists"
            case_logger.info(f"[TOOL RESULT] {result}")
            return result

        try:
            output_path.write_text(content)
            result = f"Successfully wrote {len(content)} bytes to {output_filename}"
            case_logger.info(f"[TOOL RESULT] {result}")
            return result
        except Exception as e:
            result = f"Error writing to {output_filename}: {e}"
            case_logger.error(f"[TOOL ERROR] {result}")
            return result

    @function_tool
    def run_test() -> str:
        """Run the generated test script and return the output."""
        case_logger.info(f"[TOOL] run_test({output_filename})")

        if not output_path.exists():
            result = f"Error: {output_filename} does not exist. Use write_code first."
            case_logger.error(f"[TOOL ERROR] {result}")
            return result

        case_logger.info(f"[TOOL] Using Python: {sys.executable}")

        try:
            proc_result = subprocess.run(
                [sys.executable, str(output_path)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(work_dir)
            )
            output = f"Exit code: {proc_result.returncode}\n"
            if proc_result.stdout:
                output += f"STDOUT:\n{proc_result.stdout}\n"
            if proc_result.stderr:
                output += f"STDERR:\n{proc_result.stderr}\n"
            result = output.strip() or "Script ran successfully with no output"
            case_logger.info(f"[TOOL RESULT]\n{result}")
            return result
        except subprocess.TimeoutExpired:
            result = "Error: Script timed out after 30 seconds"
            case_logger.error(f"[TOOL ERROR] {result}")
            return result
        except Exception as e:
            result = f"Error running script: {e}"
            case_logger.error(f"[TOOL ERROR] {result}")
            return result

    return [write_code, run_test]


def create_agent(tools: list) -> Agent:
    """Create the check generation agent with tools."""
    return Agent(
        name="Check Generator",
        instructions=SYSTEM_INSTRUCTIONS,
        model="gpt-5",
        tools=tools,
    )


async def run_agent_async(work_dir: Path, generation_index: int = 1) -> bool:
    """Run the agent to generate check.py from poc.py.

    Args:
        work_dir: The case directory containing poc.py and patch.diff
        generation_index: The index for this generation (1, 2, 3, etc.)
    """
    output_filename = f"generated_{generation_index}.py"
    output_path = work_dir / output_filename

    # Skip if already generated
    if output_path.exists():
        print(f"Skipping {work_dir.name}/{output_filename} - already exists")
        return True

    case_logger = setup_case_logger(work_dir)

    # Read input files
    poc_path = work_dir / "poc.py"
    patch_path = work_dir / "patch.diff"

    if not poc_path.exists():
        raise FileNotFoundError(f"poc.py not found in {work_dir}")
    if not patch_path.exists():
        raise FileNotFoundError(f"patch.diff not found in {work_dir}")

    poc_content = poc_path.read_text()
    patch_content = patch_path.read_text()

    # Create tools with context
    tools = create_tools(work_dir, output_filename, case_logger)

    # Log input files
    case_logger.info(f"=== Processing {work_dir.name} ===")
    case_logger.info(f"poc.py:\n{poc_content}")
    case_logger.info(f"patch.diff:\n{patch_content}")

    # Check for reference check.py (for understanding the expected format)
    check_path = work_dir / "check.py"
    reference_info = ""
    if check_path.exists():
        check_content = check_path.read_text()
        case_logger.info(f"check.py (reference):\n{check_content}")
        reference_info = f"""

## Reference check.py (for format reference only - create your own based on this style)
```python
{check_content}
```
"""

    user_message = f"""Please analyze the following files and generate a comprehensive test script that verifies the bug fix described in the patch.

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

Please use the write_code tool to create the test file, then use run_test to verify it works correctly. Iterate if needed to fix any issues.
"""

    print(f"Starting agent for {work_dir.name} (generation {generation_index})...")
    print("-" * 50)

    agent = create_agent(tools)

    for attempt in range(MAX_RETRIES):
        if attempt == 0:
            # First attempt: use original user message
            current_message = user_message
            case_logger.info(f"[Attempt 1] Sending initial prompt for {output_filename}")
        else:
            # Retry: ask agent to continue/complete the task
            print(f"\n[Retry {attempt}/{MAX_RETRIES - 1}] {output_filename} not created, asking agent to continue...")
            current_message = f"""You have not created the test file yet. Please complete the task:

1. Use the write_code tool to create the test file with your test code
2. Use run_test to verify it works correctly
3. Make sure the file is actually written before finishing

Do not explain - just create the file now."""
            case_logger.info(f"[Attempt {attempt + 1}] Sending retry prompt")

        try:
            result = await Runner.run(
                agent,
                current_message,
                max_turns=20,
            )
            print(f"\nAgent completed (attempt {attempt + 1}).")
            if result.final_output:
                case_logger.info(f"Agent final output:\n{result.final_output}")
                # Truncate long output for display
                output = result.final_output
                if len(output) > 500:
                    output = output[:500] + "..."
                print(f"Final message: {output}")
        except Exception as e:
            print(f"\nAgent error: {e}")
            case_logger.error(f"Agent error: {e}")
            if attempt == MAX_RETRIES - 1:
                return False
            continue

        # Check if output file was created
        if output_path.exists():
            generated_content = output_path.read_text()
            case_logger.info(f"{output_filename} created:\n{generated_content}")
            print(f"\n✓ Generated {output_path}")
            return True

    print(f"\n✗ {output_filename} was not created after {MAX_RETRIES} attempts")
    case_logger.error(f"Failed to create {output_filename} after {MAX_RETRIES} attempts")
    return False


def process_case(case_dir: Path) -> tuple[str, bool]:
    """Process a single test case. Returns (case_name, success)."""
    poc_path = case_dir / "poc.py"
    patch_path = case_dir / "patch.diff"

    if not poc_path.exists() or not patch_path.exists():
        return case_dir.name, False

    all_success = True
    for i in range(1, NUM_GENERATIONS + 1):
        output_path = case_dir / f"generated_{i}.py"

        # Skip if already generated
        if output_path.exists():
            continue

        success = asyncio.run(run_agent_async(case_dir, generation_index=i))
        if not success:
            all_success = False

    return case_dir.name, all_success


def find_all_cases() -> list[Path]:
    """Find all py-pr-* cases in SCRIPT_DIR."""
    cases = []
    for d in SCRIPT_DIR.iterdir():
        if d.is_dir() and d.name.startswith("py-pr-") and (d / "poc.py").exists():
            cases.append(d)
    return sorted(cases)


def run_all():
    """Run all cases with multiprocessing."""
    all_cases = find_all_cases()
    if not all_cases:
        print("No py-pr-* cases found")
        return 1

    print(f"Processing {len(all_cases)} cases with {MAX_WORKERS} workers ({NUM_GENERATIONS} generations each)...")

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_case, case_dir): case_dir for case_dir in all_cases}

        for future in as_completed(futures):
            case_dir = futures[future]
            try:
                case_name, ok = future.result()
                results.append((case_name, ok))
                status = "OK" if ok else "FAIL"
                print(f"  [{case_name}]: {status}")
            except Exception as e:
                print(f"  [{case_dir.name}]: ERROR - {e}")
                results.append((case_dir.name, False))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    success_count = sum(1 for _, s in results if s)
    print(f"Success: {success_count}/{len(results)}")
    for name, success in sorted(results):
        status = "✓" if success else "✗"
        print(f"  {status} {name}")

    return 0


def run_single(case_path: str):
    """Run single case."""
    case_dir = Path(case_path)
    if not case_dir.is_dir():
        print(f"Error: {case_path} is not a directory")
        return 1

    print(f"Processing: {case_dir.name}")
    _, ok = process_case(case_dir)
    print("OK" if ok else "FAIL")
    return 0 if ok else 1


def main():
    if len(sys.argv) == 1:
        return run_all()
    elif len(sys.argv) == 2:
        return run_single(sys.argv[1])
    else:
        print("Usage: python generate_check_agent.py [case_path]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
