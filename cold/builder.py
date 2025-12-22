import os
import shutil
from functools import cached_property
from pathlib import Path
from typing import Optional, Union

import yaml
from git import Repo
from patchagent.builder import Builder, PoC
from patchagent.builder.utils import (
    BuilderProcessError,
    BuilderTimeoutError,
    safe_subprocess_run,
)
from patchagent.lang import Lang
from patchagent.lsp.ctags import CtagsServer
from patchagent.lsp.hybridc import HybridCServer
from patchagent.parser import Sanitizer, SanitizerReport, parse_sanitizer_report

from cold.env import DCC, DPP, REPO, SOURCE, WORKSPACE
from cold.llmsan import LLMSanitizerReport
from cold.llvm import LLVMSanitizerReport
from cold.logger import logger
from cold.utils import backdoor_subprocess_run
from cold.v8 import V8SanitizerReport


class ColdPoC(PoC):
    def __init__(self, path: Path):
        super().__init__()
        self.path = path


class ColdBuilder(Builder):
    def __init__(
        self,
        id: str,
        backdoor: bool = False,
        replay_poc_timeout: int = 360,
        replay_max_retry: Optional[int] = None,
        function_test_timeout: int = 3600,  # 1 hour
    ):

        config = SOURCE / id / "config.yaml"
        if not config.is_file():
            raise FileNotFoundError(f"Config file not found for {id}")

        config_data = yaml.safe_load(config.read_text())
        project = config_data["project"]
        commit = config_data["trigger_commit"]
        repo_path = REPO
        source_path = WORKSPACE / f".cache/{id}"

        if not source_path.is_dir():
            logger.info(f"[📦] Copying {project} from {repo_path} to {source_path}")
            shutil.copytree(repo_path, source_path, symlinks=True)
            logger.info(f"[📦] Checking out commit {commit}")
            repo = Repo(source_path)
            repo.git.checkout(commit)

            # NOTE: We temporarily do not have 2+ layers of submodules
            repo.git.submodule("update", "--checkout")

        super().__init__(project, source_path, workspace=WORKSPACE / id)
        self.id = id
        self.backdoor = backdoor
        self.replay_poc_timeout = replay_poc_timeout
        self.function_test_timeout = function_test_timeout
        if replay_max_retry is None:
            ## HACK: We set a small retry for vim
            if project == "vim":
                self.replay_max_retry = 10
            else:
                self.replay_max_retry = 100
        else:
            self.replay_max_retry = replay_max_retry

        self.sanitizer: Union[Sanitizer, str]
        match config_data["sanitizer"]:
            case "AddressSanitizer":
                self.sanitizer = Sanitizer.AddressSanitizer
                self.replay_env = {"ASAN_OPTIONS": "detect_leaks=0"}
                self.build_env = {
                    "CC": DCC,
                    "CXX": DPP,
                    "CFLAGS": "-fsanitize=address",
                    "CXXFLAGS": "-fsanitize=address",
                    "LDFLAGS": "-fsanitize=address",
                }
            case "LeakAddressSanitizer":
                self.sanitizer = Sanitizer.LeakAddressSanitizer
                self.replay_env = {"ASAN_OPTIONS": "detect_leaks=1"}
                self.build_env = {
                    "CC": DCC,
                    "CXX": DPP,
                    "CFLAGS": "-fsanitize=address",
                    "CXXFLAGS": "-fsanitize=address",
                    "LDFLAGS": "-fsanitize=address",
                }
            case "ThreadSanitizer":
                self.sanitizer = Sanitizer.ThreadSanitizer
                self.replay_env = {}
                self.build_env = {
                    "CC": DCC,
                    "CXX": DPP,
                    "CFLAGS": "-fsanitize=thread",
                    "CXXFLAGS": "-fsanitize=thread",
                    "LDFLAGS": "-fsanitize=thread",
                }
            case "MemorySanitizer":
                self.sanitizer = Sanitizer.MemorySanitizer
                self.replay_env = {}
                self.build_env = {
                    "CC": DCC,
                    "CXX": DPP,
                    "CFLAGS": "-fsanitize=memory",
                    "CXXFLAGS": "-fsanitize=memory",
                    "LDFLAGS": "-fsanitize=memory",
                }
            case "UndefinedBehaviorSanitizer":
                self.sanitizer = Sanitizer.UndefinedBehaviorSanitizer
                self.replay_env = {
                    "UBSAN_OPTIONS": "halt_on_error=1:print_stacktrace=1",
                }
                self.build_env = {
                    "CC": DCC,
                    "CXX": DPP,
                    "CFLAGS": "-fsanitize=undefined",
                    "CXXFLAGS": "-fsanitize=undefined",
                    "LDFLAGS": "-fsanitize=undefined",
                }
            case "LLVMSanitizer":
                self.sanitizer = "LLVMSanitizer"
                self.replay_env = {}
                self.build_env = {}
            case "V8Sanitizer":
                self.sanitizer = "V8Sanitizer"
                self.replay_env = {}
                self.build_env = {}
            case _:
                raise NotImplementedError(f"{config_data['sanitizer']} not supported")

    @property
    def language(self) -> Lang:
        return Lang.CLIKE

    def find_file(self, script: str) -> Path:
        default_script = SOURCE / "common" / script
        custom_script = SOURCE / self.id / script
        return custom_script if custom_script.is_file() else default_script

    @cached_property
    def build_script(self) -> Path:
        return self.find_file("build.sh")

    @cached_property
    def exploit_script(self) -> Path:
        return self.find_file("exp.sh")

    @cached_property
    def test_script(self) -> Path:
        return self.find_file("test.sh")

    def apply_patch(self, patch: bytes, path: Path) -> None:
        safe_subprocess_run(
            ["git", "apply", "--allow-empty"],
            cwd=path,
            input=patch,
        )

    @cached_property
    def source_repo(self) -> Repo:
        target_path = self.workspace / "git" / self.org_source_path.name
        if not target_path.is_dir():
            shutil.copytree(self.source_path, target_path, symlinks=True)

        assert (target_path / ".git").is_dir()
        return Repo(target_path)

    @property
    def build_path(self) -> Path:
        return self.workspace / "build"

    def build(self, patch: str = "") -> None:
        logger.info(f"[🧱][{self.id}] Building ...")

        shutil.rmtree(self.build_path, ignore_errors=True)
        shutil.copytree(self.source_path, self.build_path, symlinks=True)

        self.apply_patch(patch.encode(), self.build_path)

        safe_subprocess_run(
            [self.build_script],
            cwd=self.build_path,
            env=os.environ | self.build_env,
        )

    def replay(self, poc: PoC, patch: str = "") -> Optional[SanitizerReport]:
        assert isinstance(poc, ColdPoC)
        self.build(patch)

        logger.info(f"[🔍][{self.id}] Running exploit...")
        for i in range(self.replay_max_retry + 1):
            try:
                if i < self.replay_max_retry:
                    safe_subprocess_run(
                        [self.exploit_script, poc.path.resolve().as_posix()],
                        cwd=self.build_path,
                        timeout=self.replay_poc_timeout,
                        env=os.environ | self.replay_env,
                    )
                elif self.backdoor:
                    out, err = backdoor_subprocess_run(
                        [self.exploit_script, poc.path.resolve().as_posix()],
                        cwd=self.build_path,
                        timeout=self.replay_poc_timeout,
                        env=os.environ | self.replay_env,
                    )
                    return LLMSanitizerReport.parse(poc.path.read_bytes(), out, err)
            except BuilderProcessError as e:
                for report in [e.stdout, e.stderr]:
                    san_report: Optional[SanitizerReport] = self.parse_sanitizer_report(report)
                    if san_report is not None:
                        return san_report

        return None

    def parse_sanitizer_report(self, report: str) -> Optional[SanitizerReport]:
        if isinstance(self.sanitizer, Sanitizer):
            return parse_sanitizer_report(
                report,
                self.sanitizer,
                source_path=self.source_path,
                work_path=self.build_path,
            )
        elif self.sanitizer == "LLVMSanitizer":
            return LLVMSanitizerReport.parse(
                report,
                source_path=self.source_path,
                work_path=self.build_path,
            )
        elif self.sanitizer == "V8Sanitizer":
            return V8SanitizerReport.parse(
                report,
                source_path=self.source_path,
                work_path=self.build_path,
            )

        return None

    def function_test(self, patch: str = "") -> None:
        source_path = self.workspace / "function"

        def test() -> None:
            shutil.rmtree(source_path, ignore_errors=True)
            shutil.copytree(self.source_path, source_path, symlinks=True)

            self.apply_patch(patch.encode(), source_path)
            safe_subprocess_run(
                [self.test_script],
                cwd=source_path,
                timeout=self.function_test_timeout,
            )

        RETRY = 3
        for retry in range(RETRY):
            logger.info(f"[🧱][{self.id}] Testing ... {retry + 1}/{RETRY}")
            try:
                return test()
            except BuilderTimeoutError:
                raise
            except:
                if retry == RETRY - 1:
                    raise

    def post_function_test(self, patch: str = "") -> None:
        source_path = self.workspace / "post_function"

        def test() -> None:
            shutil.rmtree(source_path, ignore_errors=True)
            shutil.copytree(self.source_path, source_path, symlinks=True)

            self.apply_patch(patch.encode(), source_path)

            if (test_rich_diff := self.find_file("test_rich.diff")).is_file():
                self.apply_patch(test_rich_diff.read_bytes(), source_path)
            else:
                self.apply_patch(self.find_file("test.diff").read_bytes(), source_path)

            safe_subprocess_run(
                [self.test_script],
                cwd=source_path,
                timeout=self.function_test_timeout,
            )

        RETRY = 3
        for retry in range(RETRY):
            logger.info(f"[🧱][{self.id}] Post Testing ... {retry + 1}/{RETRY}")
            try:
                return test()
            except BuilderTimeoutError:
                raise
            except:
                if retry == RETRY - 1:
                    raise

    @cached_property
    def language_server(self) -> HybridCServer | CtagsServer:
        ctags_source = self.workspace / "ctags"
        if not ctags_source.is_dir():
            shutil.copytree(self.source_path, ctags_source, symlinks=True)

        clangd_source = self.workspace / "clangd"
        if not clangd_source.is_dir():
            shutil.copytree(self.source_path, clangd_source, symlinks=True)

        try:
            if self.project != "v8":
                compile_commands = clangd_source / "compile_commands.json"
                if not compile_commands.is_file():
                    safe_subprocess_run(
                        ["bear", "--", self.build_script],
                        cwd=clangd_source,
                    )

                    assert compile_commands.is_file()

                return HybridCServer(ctags_source, clangd_source)
        except BuilderProcessError:
            logger.warning(f"[⚠️] Failed to generate compile_commands.json for {self.project}. Using CtagsServer instead.")

        return CtagsServer(ctags_source)
