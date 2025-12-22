import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from patchagent.parser import Sanitizer, SanitizerReport
from patchagent.parser.cwe import CWE
from patchagent.parser.utils import guess_relpath, remove_empty_stacktrace

LLVMPattern = "PLEASE submit a bug report to https://github.com/llvm/llvm-project/issues/"
LLVMStackTracePattern = r"^\s*#(\d+)\s+(0x[\w\d]+)\s+(.+)\s+(/.*)\s*"


def llvm_simplify_and_extract_stacktraces(
    lines: List[str],
    source_path: Optional[Path] = None,
    work_path: Optional[Path] = None,
) -> Tuple[str, List[List[Tuple[str, Path, int, int]]]]:
    body: List[str] = []
    current_count: int = -1
    stacktraces: List[List[Tuple[str, Path, int, int]]] = [[]]

    for line in lines:
        if line.strip().startswith("#"):
            count = int(line.split()[0][1:])
            if count == current_count + 1:
                current_count += 1
            else:
                stacktraces.append([])
                current_count = 0
                assert count == 0

            if (match := re.search(LLVMStackTracePattern, line)) is not None:
                function_name = match.group(3)
                entries = match.group(4).split(":")

                # NOTE: Here is an example of the entries list length may be greater than 3
                # - /usr/src/zlib-1:1.3.dfsg-3.1ubuntu2/inflate.c:429:9
                # - /usr/src/zlib-1:1.3.dfsg-3.1ubuntu2/inflate.c:1279:13
                while len(entries) > 3 or (len(entries) > 1 and any(not c.isdigit() for c in entries[1:])):
                    entries[0] = entries[0] + ":" + entries[1]
                    entries.pop(1)

                if len(entries) == 0:
                    continue

                while len(entries) < 3:
                    entries.append("0")
                filepath, line_number, column_number = entries
                assert filepath.startswith("/")

                normpath = Path(filepath).resolve()
                desc = f"{normpath}:{line_number}:{column_number}"

                if work_path is not None:
                    if normpath.is_relative_to(work_path):
                        stacktraces[-1].append((function_name, normpath.relative_to(work_path), int(line_number), int(column_number)))
                elif source_path is not None:
                    if (relpath := guess_relpath(source_path, normpath)) is not None:
                        stacktraces[-1].append((function_name, relpath, int(line_number), int(column_number)))
                else:
                    stacktraces[-1].append((function_name, normpath, int(line_number), int(column_number)))

                if work_path is None:
                    body.append(f"    - {function_name} {desc}")
                elif normpath.is_relative_to(work_path):
                    body.append(f"    - {function_name} {normpath.relative_to(work_path)}:{line_number}:{column_number}")
        elif all(len(stk) == 0 for stk in stacktraces):
            body.append(re.sub(r"==[0-9]+==", "", line))
        else:
            break

    return "\n".join(body), remove_empty_stacktrace(stacktraces)


class LLVMSanitizerReport(SanitizerReport):
    def __init__(
        self,
        content: str,
        stacktraces: List[List[Tuple[str, Path, int, int]]],
        purified_content: str = "",
    ):
        super().__init__(Sanitizer.UnknownSanitizer, content, CWE.UNKNOWN, stacktraces)
        self.purified_content: str = purified_content

    @staticmethod
    def parse(
        raw_content: str,
        source_path: Optional[Path] = None,
        work_path: Optional[Path] = None,
        *args: List[Any],
        **kwargs: Dict[str, Any],
    ) -> Optional["LLVMSanitizerReport"]:
        if LLVMPattern not in raw_content:
            return None

        lines = []
        for line in raw_content.splitlines():
            if line.startswith(LLVMPattern):
                continue
            lines.append(line)
        body, stacktraces = llvm_simplify_and_extract_stacktraces(
            lines,
            source_path=source_path,
            work_path=work_path,
        )

        return LLVMSanitizerReport(raw_content, stacktraces, body)

    @property
    def summary(self) -> str:
        return f"This is an LLVM error report. Please refer the error message for more details.\n\n{self.purified_content}"


if __name__ == "__main__":
    for vuln_path in (Path(__file__).parent.parent / "vuln/llvm").iterdir():
        report_txt = vuln_path / "report.txt"
        if not report_txt.is_file():
            continue
        san_report = LLVMSanitizerReport.parse(
            report_txt.read_text(),
            work_path=Path("/tmp") / vuln_path.name / "build",
        )
        assert san_report is not None
        assert len(san_report.stacktraces) > 0

        summary_txt = vuln_path / "summary.txt"
        summary_txt.write_text(san_report.summary)
