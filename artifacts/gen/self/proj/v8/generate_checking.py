#!/usr/bin/env python3
"""
Generate check.js from poc.js using OpenAI Agents SDK.

This script transforms V8 PoC (proof of concept) JavaScript files into
proper test files with assertions using V8's testing infrastructure.
"""

import sys
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from agents import Agent, Runner, FunctionTool
from pydantic import BaseModel

SCRIPT_DIR = Path(__file__).parent
MAX_RETRIES = 3
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", 4))


class WriteArgs(BaseModel):
    code: str


def create_write_tool(output_path: Path):
    """Create a write tool bound to specific output path."""
    def write_fn(ctx, args: str) -> str:
        parsed = WriteArgs.model_validate_json(args)
        output_path.write_text(parsed.code)
        return "File written successfully"

    return FunctionTool(
        name="write_check_js",
        description="Write the generated checking code to check.js file. Args: code (str) - The complete JavaScript code",
        params_json_schema=WriteArgs.model_json_schema(),
        on_invoke_tool=write_fn,
    )


INSTRUCTIONS = """You are an expert JavaScript programmer specializing in V8 test code generation.

## Task Background

You are working on a vulnerability testing benchmark for V8 JavaScript engine. Each test case has:
- **poc.js**: A minimal proof-of-concept that triggers a bug but lacks proper assertions
- **config.yaml**: Contains metadata about the vulnerability type
- **dump.txt**: Contains the actual runtime behavior from running poc.js with d8, including:
  - Whether execution succeeded or failed
  - Error types and messages thrown
  - Patterns detected in the code

Your job is to transform poc.js into a proper V8 test file (generated.js) by adding appropriate assertions based on the actual runtime behavior documented in dump.txt.

## V8 Assertion Functions

V8's test framework (mjsunit) provides these assertion functions:

1. **assertEquals(expected, actual)** - Verifies exact equality
   ```javascript
   assertEquals(42, builder.instantiate().exports.main());
   assertEquals(1n, foo(9n, 2n, 1n));
   ```

2. **assertThrows(fn, [ErrorType], [messagePattern])** - Verifies code throws an exception
   ```javascript
   assertThrows(() => Intl.DateTimeFormat("invalid"), RangeError);
   assertThrows(() => new C1(), TypeError);
   assertThrows(() => new WebAssembly.Exception(tag, [], proxy), Error, 'boom');
   ```

3. **assertTrue(value)** / **assertFalse(value)** - Boolean assertions
   ```javascript
   assertTrue(result > 0);
   assertFalse(done);
   ```

4. **assertPromiseResult(promise, onFulfilled)** - Async promise verification
   ```javascript
   assertPromiseResult(
       WebAssembly.promising(instance.exports.byteLength)(dataview),
       v => assertEquals(v, kLength));
   ```

5. **assertSame(expected, actual)** - Verifies object identity (===)

6. **assertNotEquals(unexpected, actual)** - Verifies values are different

## Transformation Rules

1. **try/catch without assertions** → **assertThrows**
   ```javascript
   // Before (poc.js):
   try { new C1(); } catch (e) { }

   // After (check.js):
   assertThrows(() => new C1(), TypeError);
   ```

2. **Function calls without return value checking** → **assertEquals**
   ```javascript
   // Before:
   foo(9n, 2n, 1n);

   // After (if expected value is known):
   assertEquals(1n, foo(9n, 2n, 1n));
   ```

3. **Code that should just run without crashing** → Keep as-is
   - Some tests verify that code doesn't crash
   - These don't need assertions, just keep the original code

4. **WebAssembly tests** → Add assertEquals for exported function calls
   ```javascript
   // Before:
   builder.instantiate().exports.main();

   // After:
   assertEquals(42, builder.instantiate().exports.main());
   ```

## Guidelines

1. Preserve all original comments, copyright notices, and // Flags: directives
2. Keep the original code structure and logic intact
3. Infer the expected error type from context:
   - Invalid Intl parameters → RangeError
   - Undefined property access → TypeError
   - Invalid constructor calls → TypeError
   - WebAssembly exceptions with custom errors → Error
4. If the code doesn't have clear assertions to add (no try/catch, no obvious expected values), keep it as-is
5. For tests with %PrepareFunctionForOptimization and %OptimizeFunctionOnNextCall, the focus is usually on not crashing during optimization
6. Look for patterns where values should be checked (e.g., method return values, property accesses)

## Input Format

You will receive:
- **poc.js**: The original proof-of-concept code
- **config.yaml**: Metadata about the vulnerability (type, sanitizer used, etc.)
- **dump.txt**: Actual runtime behavior from d8 execution

## Using dump.txt - CRITICAL

The dump.txt file contains the ACTUAL runtime behavior. You MUST use this information:

### 1. For Empty Try/Catch Blocks
Look for this section in dump.txt:
```
## Empty Try/Catch Blocks (convert to assertThrows)
- code: <the code inside try block>
  error_type: <EXACT error type to use>
  error_message: <error message>
```

Convert the try/catch to assertThrows using the EXACT error_type from dump.txt:
```javascript
// Before (poc.js):
try { <code> } catch (e) { }

// After (generated.js) - use error_type from dump.txt:
assertThrows(() => <code>, <error_type>);
```

### 2. For Direct Exceptions (success: False)
Look for this section:
```
## Exception
type: <error type>
message: <error message>
```

Wrap the throwing code with assertThrows using the EXACT type from dump.txt.

### 3. For Successful Execution (success: True, no try/catch)
- If there are WebAssembly export calls, add assertEquals
- If code just runs without crashing (no patterns to convert), keep as-is

### 4. For Console.log Calls
Look for this section in dump.txt:
```
## Console.log Calls (convert to assertEquals)
- expression: <the expression being logged>
  expected_output: '<the actual output value>'
```

Convert:
```javascript
console.log(<expression>);
```
To:
```javascript
assertEquals('<expected_output>', <expression>);
```

### Concrete Examples:

**Example 1**: dump.txt shows:
```
## Empty Try/Catch Blocks (convert to assertThrows)
- code: new C1();
  error_type: TypeError
  error_message: (intermediate value).p is not a function
```
Generate: `assertThrows(() => new C1(), TypeError);`

**Example 2**: dump.txt shows:
```
## Exception
type: RangeError
message: Internal error. Icu error.
```
Wrap the call with: `assertThrows(() => Intl.DateTimeFormat("de-u-22300-true-x-true"), RangeError);`

**Example 3**: dump.txt shows:
```
## Empty Try/Catch Blocks (convert to assertThrows)
- code: new WebAssembly.Exception(tag, [], proxy);
  error_type: Error
  error_message: boom
```
Generate: `assertThrows(() => new WebAssembly.Exception(tag, [], proxy), Error, 'boom');`

**Example 4**: dump.txt shows:
```
## Console.log Calls (convert to assertEquals)
- expression: (-1.777435286647996e+308).toExponential(100)
  expected_output: '-1.7774352866479959137616855978032470542052397040225939205262400173577628014729345083522107643115812351e+308'
```
Convert `console.log((-1.777435286647996e+308).toExponential(100));` to:
```javascript
assertEquals(
    '-1.7774352866479959137616855978032470542052397040225939205262400173577628014729345083522107643115812351e+308',
    (-1.777435286647996e+308).toExponential(100));
```

## Output Requirements

Generate a complete generated.js file that:
1. Includes the original copyright header
2. Preserves all // Flags: directives
3. Uses the EXACT error types from dump.txt for assertThrows
4. Replaces empty try/catch with assertThrows using the error type from dump.txt
5. Adds assertEquals for verifiable return values
6. Maintains the original test logic and structure

## Action Required

After generating the code, you MUST call the write_check_js tool to save it.
"""


def process_case(case_dir: Path) -> tuple[str, bool]:
    """Process a single test case with retry. Returns (case_name, success)."""
    poc_path = case_dir / "poc.js"
    config_path = case_dir / "config.yaml"
    dump_path = case_dir / "dump.txt"
    output_path = case_dir / "generated.js"

    if not poc_path.exists():
        return case_dir.name, False

    if output_path.exists():
        return case_dir.name, True

    # Read all input files
    poc_text = poc_path.read_text()
    config_text = config_path.read_text() if config_path.exists() else ""
    dump_text = dump_path.read_text() if dump_path.exists() else "No dump.txt available - infer expected behavior from code patterns."

    write_tool = create_write_tool(output_path)
    agent = Agent(
        name="V8CheckGenerator",
        instructions=INSTRUCTIONS,
        tools=[write_tool],
        model="gpt-4.1",
    )

    base_prompt = f"""poc.js:
```javascript
{poc_text}
```

config.yaml:
```yaml
{config_text}
```

dump.txt:
```
{dump_text}
```"""

    for attempt in range(1, MAX_RETRIES + 1):
        prompt = base_prompt if attempt == 1 else f"{base_prompt}\n\nIMPORTANT: You must call write_check_js tool now."
        Runner.run_sync(agent, prompt)
        if output_path.exists():
            return case_dir.name, True

    return case_dir.name, False


def find_all_cases() -> list[Path]:
    """Find all V8 test cases with poc.js files."""
    cases = []
    for d in SCRIPT_DIR.iterdir():
        if d.is_dir() and (d / "poc.js").exists():
            cases.append(d)
    return sorted(cases)


def run_all():
    """Run all cases with multiprocessing."""
    all_cases = find_all_cases()
    if not all_cases:
        print("No cases found")
        return 1

    print(f"Processing {len(all_cases)} V8 cases with {MAX_WORKERS} workers...")

    success = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_case, case_dir): case_dir
                   for case_dir in all_cases}

        for future in as_completed(futures):
            case_dir = futures[future]
            case_name, ok = future.result()
            status = "OK" if ok else "SKIP/FAIL"
            print(f"  {case_name}: {status}")
            if ok:
                success += 1

    print(f"\nSummary: {success}/{len(all_cases)}")
    return 0


def run_single(case_path: str):
    """Run single case."""
    case_dir = Path(case_path)
    if not case_dir.is_absolute():
        case_dir = SCRIPT_DIR / case_path

    if not case_dir.is_dir():
        print(f"{case_path} is not a directory")
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
    print("Usage: python generate_checking.py [case_path]")
    return 1


if __name__ == "__main__":
    sys.exit(main())
