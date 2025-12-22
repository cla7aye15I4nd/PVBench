#!/usr/bin/env python3
"""
Test code generator for V8 with feedback loop.

This module generates test code (generated_N.js) from poc.js and patch.diff,
validates using provided validate_fn, and regenerates with feedback on failure.
"""

import os
import re
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


def extract_v8_flags(content: str) -> List[str]:
    """Extract V8 flags from // Flags: comments in the source."""
    flags = []
    for line in content.split('\n'):
        match = re.match(r'//\s*Flags:\s*(.+)', line)
        if match:
            flags.extend(match.group(1).split())
    return flags


def create_write_tool(output_path: Path):
    """Create a write tool bound to specific output path."""
    async def write_fn(ctx, args: str) -> str:
        parsed = WriteArgs.model_validate_json(args)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(parsed.code)
        return "File written successfully"

    return FunctionTool(
        name="write_generated_js",
        description="Write the generated checking code to generated.js file. Args: code (str) - The complete JavaScript code",
        params_json_schema=WriteArgs.model_json_schema(),
        on_invoke_tool=write_fn,
    )


def create_run_tool(output_path: Path, work_dir: Path, d8_exec: str):
    """Create a run tool for executing the generated V8 test."""
    async def run_fn(ctx, args: str) -> str:
        if not output_path.exists():
            return f"Error: {output_path.name} does not exist. Use write_generated_js first."

        try:
            content = output_path.read_text()
            flags = extract_v8_flags(content)

            env = os.environ.copy()
            env["TERM"] = "xterm"
            cmd = [d8_exec] + flags + [str(output_path)]
            result = subprocess.run(
                cmd,
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


BASE_INSTRUCTIONS = """You are an expert JavaScript test engineer for V8 (Chrome's JavaScript engine). Your task is to analyze a patch.diff file and a poc.js (proof of concept) file, then generate a comprehensive test script.

## Your Goal
Transform a simple poc.js into a robust test by adding assertions that verify the expected behavior after the bug fix.

## Input Format

**poc.js** contains JavaScript code that demonstrates a bug or vulnerability in V8.

**patch.diff** shows the fix that was applied to V8 source code.

## CRITICAL RULES

1. **Preserve V8-specific flags**
   - If the poc.js contains `// Flags: --some-flag`, keep these in your generated test
   - Common flags: `--allow-natives-syntax`, `--expose-gc`, `--no-lazy`

2. **Understand the bug fix from patch.diff**
   - The patch shows what code was changed to fix the bug
   - Your test should verify that the fix works correctly

3. **Use appropriate assertion patterns**
   - For tests that should not crash: use try/catch
   - For optimization bugs: use %PrepareFunctionForOptimization and %OptimizeFunctionOnNextCall
   - For value checks: explicit equality checks

4. **Keep tests minimal but comprehensive**
   - Test the fix works (no crash, correct behavior)
   - Test edge cases related to the fix

## V8 NATIVE SYNTAX (requires --allow-natives-syntax flag)

When testing optimization-related bugs, use V8's native functions:
```javascript
// Flags: --allow-natives-syntax

function foo(a, b) {
    return a + b;
}

%PrepareFunctionForOptimization(foo);
foo(1, 2);  // Warm up
%OptimizeFunctionOnNextCall(foo);
var result = foo(1, 2);  // This call will be optimized

// Check result
if (result !== 3) throw new Error("Expected 3, got " + result);
```

## AVAILABLE CHECK PATTERNS

### 1. Basic Assertion
```javascript
function assertEquals(actual, expected, message) {
    if (actual !== expected) {
        throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
    }
}
```

### 2. Exception Testing
```javascript
try {
    codeThatShouldThrow();
    throw new Error("Expected exception was not raised");
} catch (e) {
    if (!(e instanceof ExpectedErrorType)) {
        throw new Error("Wrong exception type: " + e);
    }
}
```

### 3. No-Crash Testing (common for V8 bugs)
```javascript
// Flags: --allow-natives-syntax

// The original code that crashed
function problematicFunction() {
    // code from poc.js
}

%PrepareFunctionForOptimization(problematicFunction);
problematicFunction();
%OptimizeFunctionOnNextCall(problematicFunction);
problematicFunction();  // Should not crash after fix

print("OK");
```

### 4. BigInt Testing (common in V8)
```javascript
// Flags: --allow-natives-syntax

function foo(a, b) {
    return BigInt.asUintN(64, a + b);
}

%PrepareFunctionForOptimization(foo);
var result = foo(1n, 2n);
%OptimizeFunctionOnNextCall(foo);
result = foo(1n, 2n);

if (result !== 3n) throw new Error("Expected 3n, got " + result);
print("OK");
```

---

## Workflow
1. Use write_generated_js to create generated.js with your test code
2. Use run_test to verify it works correctly
3. If there are errors, analyze them and fix the code
4. Iterate until the test passes

## Important Notes
- The generated.js should be self-contained and runnable with d8
- Preserve any `// Flags:` comments from the original poc.js
- V8's d8 uses `print()` for output
- Add comments explaining what each test case verifies
- If the test completes without throwing, print "OK" at the end
- For optimization bugs, ensure you're testing both interpreted and optimized code paths
"""


FEEDBACK_TEMPLATE = """
## IMPORTANT: Previous Generation Failed

**Error Type:** {error_type}
**Error Message:**
```
{error_message}
```

**Your Previous Code:**
```javascript
{previous_code}
```

Please fix the issues and regenerate. Common issues:
- Missing required V8 flags (check if --allow-natives-syntax is needed)
- Using APIs not available in d8 (use print() not console.log())
- Incorrect BigInt handling
- Wrong expected behavior assumptions

Generate corrected code and call write_generated_js.
"""


# Type alias for validation function: (gen_file: Path) -> Tuple[success, error_type, error_message]
ValidateFn = Optional[callable]


def generate_test(case_dir: Path, gen_num: int,
                  validate_fn: ValidateFn = None) -> Tuple[str, int, bool, str]:
    """
    Generate test with feedback loop.

    Args:
        case_dir: Directory containing poc.js and patch.diff
        gen_num: Generation number (1, 2, 3)
        validate_fn: Validation function (gen_file: Path) -> (success, error_type, error_msg)
                    REQUIRED - must be provided by caller (uses built d8)

    Returns: (case_name, gen_num, success, message)
    """
    poc_path = case_dir / "poc.js"
    patch_path = case_dir / "patch.diff"
    output_path = case_dir / f"generated_{gen_num}.js"
    vuln_id = case_dir.name

    if not poc_path.exists():
        return case_dir.name, gen_num, False, "Missing poc.js"
    if not patch_path.exists():
        return case_dir.name, gen_num, False, "Missing patch.diff"
    if validate_fn is None:
        return case_dir.name, gen_num, False, "validate_fn is required"

    # Read files with error handling for binary/non-UTF-8 content
    try:
        poc_content = poc_path.read_text(errors='replace')
    except Exception as e:
        poc_bytes = poc_path.read_bytes()
        poc_content = f"[Binary file - {len(poc_bytes)} bytes]\nHex dump:\n" + poc_bytes[:200].hex()

    try:
        patch_content = patch_path.read_text(errors='replace')
    except Exception as e:
        return case_dir.name, gen_num, False, f"Cannot read patch.diff: {e}"

    # Extract flags from poc
    poc_flags = extract_v8_flags(poc_content)
    flags_info = ""
    if poc_flags:
        flags_info = f"\n**Note:** The poc.js uses these V8 flags: {' '.join(poc_flags)} - make sure to include them in your generated test.\n"

    # Check for reference check.js
    check_path = case_dir / "check.js"
    reference_info = ""
    if check_path.exists():
        try:
            check_content = check_path.read_text(errors='replace')
        except Exception:
            check_content = "[Binary content - cannot display]"
        reference_info = f"""

## Reference check.js (for format reference only - create your own based on this style)
```javascript
{check_content}
```
"""

    base_prompt = f"""Please analyze the following files and generate a comprehensive test script that verifies the bug fix described in the patch.

## poc.js (Proof of Concept)
```javascript
{poc_content}
```

## patch.diff
```diff
{patch_content}
```
{flags_info}{reference_info}
## Task
1. Analyze the patch to understand what bug is being fixed
2. Create the test file that:
   - Preserves any V8-specific flags from poc.js
   - Enriches the poc.js with additional test scenarios based on the patch
   - Uses appropriate assertion patterns for V8/d8
   - Tests edge cases related to the fix

Please use the write_generated_js tool to create the test file, then use run_test to verify it works correctly. Iterate if needed to fix any issues.
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
        # Use system d8 for agent's run_test (quick sanity check)
        run_tool = create_run_tool(output_path, case_dir, "d8")
        agent = Agent(
            name="V8TestGenerator",
            instructions=instructions,
            tools=[write_tool, run_tool],
            model=MODEL,
        )

        prompt = base_prompt
        if round_num > 0:
            prompt += "\n\nIMPORTANT: You must call write_generated_js tool now."

        # Generate
        for attempt in range(MAX_RETRIES):
            try:
                Runner.run_sync(agent, prompt)
                if output_path.exists():
                    break
            except Exception as e:
                logger.warning(f"  [v8] {vuln_id}/gen{gen_num}: Generation attempt {attempt+1} failed: {e}")
                continue

        if not output_path.exists():
            return case_dir.name, gen_num, False, f"Generation failed after {MAX_RETRIES} attempts"

        generated_code = output_path.read_text()

        # Validate using provided function (built d8)
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
            logger.info(f"  [v8] {vuln_id}/gen{gen_num}: FAIL ({error_type}) - retrying with feedback")
        else:
            return case_dir.name, gen_num, False, f"FAIL ({error_type}): {error_message[:200]}"

    return case_dir.name, gen_num, False, f"Exhausted {MAX_FEEDBACK_ROUNDS} feedback rounds"
