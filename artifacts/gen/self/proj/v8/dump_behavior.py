#!/usr/bin/env python3
"""
Dump expected behavior from poc.js by running with d8.
Creates dump.txt with information about expected assertions.
"""

import sys
import os
import re
import subprocess
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

SCRIPT_DIR = Path(__file__).parent
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", 4))


def find_d8() -> Path | None:
    """Find d8 binary."""
    # Primary: Use the d8 from src/v8
    src_d8 = SCRIPT_DIR / "src" / "v8" / "out" / "x64.release" / "d8"
    if src_d8.exists():
        return src_d8

    # Check in script directory (symlink)
    local_d8 = SCRIPT_DIR / "d8"
    if local_d8.exists():
        return local_d8

    # Check vu directory
    vu_dir = SCRIPT_DIR / "vu"
    for build_type in ["x64.release", "release", "debug"]:
        d8_path = vu_dir / "out" / build_type / "d8"
        if d8_path.exists():
            return d8_path

    return None


def extract_flags(poc_content: str) -> list[str]:
    """Extract V8 flags from poc.js content."""
    flags = []
    for line in poc_content.split('\n'):
        if line.strip().startswith('// Flags:'):
            flag_str = line.split('// Flags:')[1].strip()
            flags.extend(flag_str.split())
    return flags


def analyze_poc_patterns(poc_content: str) -> dict:
    """Analyze poc.js to identify patterns that need assertions."""
    patterns = {
        "try_catch_empty": [],  # try { code } catch (e) { } -> assertThrows
        "try_catch_code": [],   # The actual code inside try blocks (for error extraction)
        "function_calls": [],    # standalone function calls -> assertEquals
        "wasm_exports": [],      # WebAssembly export calls
        "console_log": [],       # console.log(expr) -> assertEquals(stdout, expr)
        "has_assertions": False, # Already has assertEquals/assertThrows
    }

    # Check if already has assertions
    if re.search(r'\b(assertEquals|assertThrows|assertTrue|assertFalse)\b', poc_content):
        patterns["has_assertions"] = True

    # Find empty try/catch blocks
    try_catch_pattern = r'try\s*\{([^}]+)\}\s*catch\s*\([^)]*\)\s*\{\s*\}'
    for match in re.finditer(try_catch_pattern, poc_content):
        code = match.group(1).strip()
        patterns["try_catch_empty"].append(code[:100] + "..." if len(code) > 100 else code)
        patterns["try_catch_code"].append(code)

    # Find WebAssembly instantiate and export calls
    wasm_pattern = r'(builder\.instantiate\(\)\.exports\.\w+)\s*\(\s*\)'
    for match in re.finditer(wasm_pattern, poc_content):
        patterns["wasm_exports"].append(match.group(1))

    # Find console.log/print calls (to convert to assertEquals)
    console_pattern = r'(?:console\.log|print)\s*\(([^;]+)\);'
    for match in re.finditer(console_pattern, poc_content):
        expr = match.group(1).strip()
        patterns["console_log"].append(expr)

    return patterns


def extract_error_from_poc(d8_path: Path, poc_content: str, v8_src: Path, timeout: int = 10) -> dict:
    """Run poc.js with try/catch removed to capture the error type."""
    import tempfile
    result = {"error_type": None, "error_message": None}

    # Remove empty try/catch blocks to let errors propagate
    modified = re.sub(
        r'try\s*\{([^}]+)\}\s*catch\s*\([^)]*\)\s*\{\s*\}',
        r'\1',  # Replace with just the try block content
        poc_content
    )

    # Extract flags
    flags = extract_flags(poc_content)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
        f.write(modified)
        temp_path = f.name

    try:
        cmd = [str(d8_path)] + flags + [temp_path]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(v8_src),
        )

        if proc.returncode != 0:
            combined = proc.stderr + "\n" + proc.stdout
            # Match Error, TypeError, RangeError, etc.
            type_match = re.search(r'\b(\w*Error):', combined)
            if type_match:
                result["error_type"] = type_match.group(1)
            msg_match = re.search(r'\b\w*Error:\s*(.+?)(?:\n|$)', combined)
            if msg_match:
                result["error_message"] = msg_match.group(1).strip()
    except:
        pass
    finally:
        os.unlink(temp_path)

    return result


def run_with_d8(d8_path: Path, poc_path: Path, v8_src: Path, timeout: int = 30) -> dict:
    """Run poc.js with d8 and capture behavior."""
    poc_content = poc_path.read_text()
    flags = extract_flags(poc_content)

    # Build command - run from v8_src so d8.file.execute can find test files
    cmd = [str(d8_path)] + flags
    cmd.append(str(poc_path))

    result = {
        "success": False,
        "exit_code": None,
        "stdout": "",
        "stderr": "",
        "threw": False,
        "error_type": None,
        "error_message": None,
    }

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(v8_src),  # Run from V8 source for relative paths
        )
        result["exit_code"] = proc.returncode
        result["stdout"] = proc.stdout
        result["stderr"] = proc.stderr
        result["success"] = proc.returncode == 0

        # Parse error from stderr or stdout
        if proc.returncode != 0:
            result["threw"] = True
            # Check both stderr and stdout for error info
            combined_output = proc.stderr + "\n" + proc.stdout
            # Try to extract error type (matches Error, TypeError, RangeError, etc.)
            type_match = re.search(r'\b(\w*Error):', combined_output)
            if type_match:
                result["error_type"] = type_match.group(1)
            msg_match = re.search(r'\b\w*Error:\s*(.+?)(?:\n|$)', combined_output)
            if msg_match:
                result["error_message"] = msg_match.group(1).strip()

    except subprocess.TimeoutExpired:
        result["error_type"] = "Timeout"
        result["error_message"] = f"Execution exceeded {timeout}s"
    except Exception as e:
        result["error_type"] = type(e).__name__
        result["error_message"] = str(e)

    return result


def create_dump(case_dir: Path, d8_path: Path, v8_src: Path) -> bool:
    """Create dump.txt for a test case."""
    poc_path = case_dir / "poc.js"
    dump_path = case_dir / "dump.txt"

    if not poc_path.exists():
        return False

    poc_content = poc_path.read_text()
    patterns = analyze_poc_patterns(poc_content)

    # Run with d8 to get actual behavior
    run_result = run_with_d8(d8_path, poc_path, v8_src)

    # Generate dump content
    dump_lines = [
        f"# Dump for {case_dir.name}",
        f"# Generated by dump_behavior.py",
        "",
        "## Execution Result",
        f"success: {run_result['success']}",
        f"exit_code: {run_result['exit_code']}",
    ]

    if run_result["threw"]:
        dump_lines.extend([
            "",
            "## Exception",
            f"type: {run_result['error_type']}",
            f"message: {run_result['error_message']}",
        ])

    dump_lines.extend([
        "",
        "## Patterns Found",
        f"has_existing_assertions: {patterns['has_assertions']}",
    ])

    if patterns["try_catch_empty"]:
        dump_lines.append("")
        dump_lines.append("## Empty Try/Catch Blocks (convert to assertThrows)")
        # Extract actual error type by running full poc with try/catch removed
        error_info = extract_error_from_poc(d8_path, poc_content, v8_src)
        for code in patterns["try_catch_empty"]:
            dump_lines.append(f"- code: {code}")
        if error_info["error_type"]:
            dump_lines.append(f"  error_type: {error_info['error_type']}")
        if error_info["error_message"]:
            dump_lines.append(f"  error_message: {error_info['error_message']}")

    if patterns["wasm_exports"]:
        dump_lines.append("")
        dump_lines.append("## WebAssembly Export Calls (add assertEquals)")
        for call in patterns["wasm_exports"]:
            dump_lines.append(f"- {call}")

    if patterns["console_log"] and run_result["stdout"]:
        dump_lines.append("")
        dump_lines.append("## Console.log Calls (convert to assertEquals)")
        stdout_lines = run_result["stdout"].strip().split('\n')
        for i, expr in enumerate(patterns["console_log"]):
            expected_value = stdout_lines[i] if i < len(stdout_lines) else ""
            dump_lines.append(f"- expression: {expr}")
            dump_lines.append(f"  expected_output: '{expected_value}'")

    if run_result["stdout"]:
        dump_lines.extend([
            "",
            "## Stdout",
            run_result["stdout"][:2000],
        ])

    if run_result["stderr"] and not run_result["success"]:
        dump_lines.extend([
            "",
            "## Stderr",
            run_result["stderr"][:2000],
        ])

    dump_path.write_text("\n".join(dump_lines))
    return True


def process_case(case_dir: Path, d8_path: Path, v8_src: Path) -> tuple[str, bool]:
    """Process a single case."""
    try:
        ok = create_dump(case_dir, d8_path, v8_src)
        return case_dir.name, ok
    except Exception as e:
        print(f"Error processing {case_dir.name}: {e}")
        return case_dir.name, False


def find_v8_src() -> Path | None:
    """Find V8 source directory."""
    # Primary: Use src/v8
    src_v8 = SCRIPT_DIR / "src" / "v8"
    if (src_v8 / "test" / "mjsunit").exists():
        return src_v8

    # Check vu directory
    vu_dir = SCRIPT_DIR / "vu"
    if (vu_dir / "test" / "mjsunit").exists():
        return vu_dir

    return None


def find_all_cases() -> list[Path]:
    """Find all V8 test cases."""
    cases = []
    for d in SCRIPT_DIR.iterdir():
        if d.is_dir() and (d / "poc.js").exists():
            cases.append(d)
    return sorted(cases)


def run_all():
    """Run dump for all cases."""
    d8_path = find_d8()
    if not d8_path:
        print("Error: d8 not found. Run build_d8.sh first.")
        return 1

    v8_src = find_v8_src()
    if not v8_src:
        print("Error: V8 source not found in pvbench-v8")
        return 1

    print(f"Using d8: {d8_path}")
    print(f"Using V8 source: {v8_src}")

    all_cases = find_all_cases()
    if not all_cases:
        print("No cases found")
        return 1

    print(f"Processing {len(all_cases)} cases with {MAX_WORKERS} workers...")

    success = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_case, case_dir, d8_path, v8_src): case_dir
                   for case_dir in all_cases}

        for future in as_completed(futures):
            case_name, ok = future.result()
            status = "OK" if ok else "FAIL"
            print(f"  {case_name}: {status}")
            if ok:
                success += 1

    print(f"\nSummary: {success}/{len(all_cases)}")
    return 0


def run_single(case_path: str):
    """Run dump for single case."""
    d8_path = find_d8()
    if not d8_path:
        print("Error: d8 not found. Run build_d8.sh first.")
        return 1

    v8_src = find_v8_src()
    if not v8_src:
        print("Error: V8 source not found")
        return 1

    case_dir = Path(case_path)
    if not case_dir.is_absolute():
        case_dir = SCRIPT_DIR / case_path

    if not case_dir.is_dir():
        print(f"{case_path} is not a directory")
        return 1

    print(f"Processing: {case_dir.name}")
    _, ok = process_case(case_dir, d8_path, v8_src)
    print("OK" if ok else "FAIL")
    return 0 if ok else 1


def main():
    if len(sys.argv) == 1:
        return run_all()
    elif len(sys.argv) == 2:
        return run_single(sys.argv[1])
    print("Usage: python dump_behavior.py [case_path]")
    return 1


if __name__ == "__main__":
    sys.exit(main())
