from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from patchagent.parser import Sanitizer, SanitizerReport
from patchagent.parser.cwe import CWE

V8Pattern = "==== C stack trace ==============================="


class V8SanitizerReport(SanitizerReport):
    def __init__(
        self,
        content: str,
        stacktraces: List[List[Tuple[str, Path, int, int]]] = [],
    ):
        super().__init__(Sanitizer.UnknownSanitizer, content, CWE.UNKNOWN, stacktraces)

    @staticmethod
    def parse(
        raw_content: str,
        source_path: Optional[Path] = None,
        work_path: Optional[Path] = None,
        *args: List[Any],
        **kwargs: Dict[str, Any],
    ) -> Optional["V8SanitizerReport"]:
        if V8Pattern not in raw_content:
            return None

        return V8SanitizerReport(raw_content)

    @property
    def summary(self) -> str:
        return f"This is an V8 error report. Please refer the error message for more details.\n\n{self.content}"


if __name__ == "__main__":
    for vuln_path in (Path(__file__).parent.parent / "vuln/v8").iterdir():
        report_txt = vuln_path / "report.txt"
        if not report_txt.is_file():
            continue
        content = report_txt.read_text()
        if "AddressSanitizer" not in content:
            san_report = V8SanitizerReport.parse(
                content,
                work_path=Path("/tmp") / vuln_path.name / "build",
            )
            assert san_report is not None

            summary_txt = vuln_path / "summary.txt"
            summary_txt.write_text(san_report.summary)
