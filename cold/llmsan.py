from typing import Optional

from anthropic import Anthropic, AnthropicError
from patchagent.parser import Sanitizer, SanitizerReport
from patchagent.parser.cwe import CWE
from pydantic import BaseModel, Field
from pydantic_core import ValidationError

from cold.prompt import HUMAN_PROMPT, SYSTEM_PROMPT


class SanitizerAnalysis(BaseModel):
    plausible: bool = Field(description="Whether the sanitizer output is plausible given the input")
    explanation: str = Field(description="Detailed explanation of why the output is or isn't plausible")


class LLMSanitizerReport(SanitizerReport):
    def __init__(self, summary: str, poc_input: str, out: str, err: str):
        super().__init__(Sanitizer.UnknownSanitizer, "", CWE.UNKNOWN, [])
        self._summary = summary
        self._poc_input = poc_input
        self._out = out
        self._err = err

    @property
    def summary(self) -> str:
        return (
            f"We assume the behavior of the program is not intended. The poc input is: \n\n{self._poc_input}\n\n"
            f"The standard output is: \n\n{self._out}\n\n"
            f"The error output is: \n\n{self._err}\n\n"
            f"The analysis is: \n\n{self._summary}\n\n"
        )

    @staticmethod
    def parse(poc_input: bytes, out: bytes, err: bytes, max_retries: int = 5) -> Optional["LLMSanitizerReport"]:
        client = Anthropic()

        poc_input_str = poc_input.decode("utf-8", errors="replace")
        out_str = out.decode("utf-8", errors="replace")
        err_str = err.decode("utf-8", errors="replace")

        human_prompt = HUMAN_PROMPT.format(
            poc_input_str=poc_input_str,
            out_str=out_str,
            err_str=err_str,
        )

        for retry_count in range(max_retries):
            try:
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1024,
                    temperature=0.7,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": human_prompt}],
                    tools=[
                        {
                            "name": "analyze_sanitizer_output",
                            "description": "Analyze whether sanitizer output is plausible",
                            "input_schema": SanitizerAnalysis.model_json_schema(),
                        }
                    ],
                    tool_choice={
                        "type": "tool",
                        "name": "analyze_sanitizer_output",
                    },
                )

                if response.content and len(response.content) > 0:
                    for content in response.content:
                        if hasattr(content, "input") and content.type == "tool_use":
                            input = content.input
                            analysis = SanitizerAnalysis.model_validate(input)

                            if analysis.plausible:
                                return None
                            else:
                                return LLMSanitizerReport(summary=analysis.explanation, poc_input=poc_input_str, out=out_str, err=err_str)
            except (AnthropicError, ValidationError) as e:
                print(f"Validate[{retry_count}] LLM analysis failed: {str(e)}")
                if retry_count == max_retries - 1:
                    raise

        return None


if __name__ == "__main__":
    poc_input = b"var_dump(range(9.9, '0'));"
    out_1 = """Fatal error: Uncaught ValueError: range(): Argument #1
($start) must be a valid string in /test.php:2,→
Stack trace:
#0 /test.php(2): range(9.9, '0')
#1 {main}
thrown in /test.php on line 2""".encode()
    out_2 = """array(10) {
9 [0]=>float(9.9)
10 [1]=>float(8.9)
11 [2]=>float(7.9)
12 [3]=>float(6.9)
13 [4]=>float(5.9)
14 [5]=>float(4.9)
15 [6]=>float(3.9000000000000004)
16 [7]=>float(2.9000000000000004)
17 [8]=>float(1.9000000000000004)
18 [9]=>float(0.9000000000000004)
19 }""".encode()

    print("Out 1")
    report = LLMSanitizerReport.parse(poc_input, out_1, b"")
    if report is None:
        print("Sanitizer output is plausible")
    else:
        print(report.summary)

    print("Out 2")
    report = LLMSanitizerReport.parse(poc_input, out_2, b"")
    if report is None:
        print("Sanitizer output is plausible")
    else:
        print(report.summary)
