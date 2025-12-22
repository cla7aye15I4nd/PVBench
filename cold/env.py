import os
from pathlib import Path

DCC: str = (Path(__file__).parent / "compiler" / "dcc").resolve().as_posix()

DPP: str = (Path(__file__).parent / "compiler" / "d++").resolve().as_posix()

SOURCE: Path = Path("/testcases")

REPO: Path = Path("/repo")

WORKSPACE: Path = Path("/tmp")

ARCHIVE: Path = Path("/archive")

ACTION: str = os.environ.get("COLD_ACTION", "check")

MODEL: str = os.environ.get("COLD_MODEL", "gpt-4.1")

MAX_PROC: int = int(os.environ.get("COLD_MAX_PROC", 4))

# Path to generated test cases (for gentest action)
GENTEST: Path = Path(os.environ.get("COLD_GENTEST", "/gentest"))

# Path to cpython generated test cases (separate from C/C++ projects)
GENTEST_CPYTHON: Path = Path(os.environ.get("COLD_GENTEST_CPYTHON", "/gentest-cpython"))

# Path to mruby generated test cases
GENTEST_MRUBY: Path = Path(os.environ.get("COLD_GENTEST_MRUBY", "/gentest-mruby"))

# Path to quickjs generated test cases
GENTEST_QUICKJS: Path = Path(os.environ.get("COLD_GENTEST_QUICKJS", "/gentest-quickjs"))

# Path to v8 generated test cases
GENTEST_V8: Path = Path(os.environ.get("COLD_GENTEST_V8", "/gentest-v8"))

# Path to vim generated test cases
GENTEST_VIM: Path = Path(os.environ.get("COLD_GENTEST_VIM", "/gentest-vim"))

# OpenAI model for test generation (for gentest-gen action)
OPENAI_MODEL: str = os.environ.get("OPENAI_MODEL", "gpt-5")
