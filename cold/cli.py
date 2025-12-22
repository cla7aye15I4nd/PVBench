import argparse
import concurrent.futures
import json
import os
import shutil
import traceback
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, List

import yaml
from patchagent.agent.generator import agent_generator
from patchagent.builder.utils import BuilderProcessError, BuilderTimeoutError
from patchagent.task import PatchTask, ValidationResult

try:
    from san2patch.internal_error import San2PatchInternalError
    from san2patch.patching.llm.anthropic_llm_patcher import Claude4SonnetPatcher
    from san2patch.patching.llm.openai_llm_patcher import GPT41Patcher as OpenAIGPT41Patcher
    from san2patch.patching.patcher import San2Patcher, TestEvalRetCode
except ImportError:
    ...

from cold.builder import ColdBuilder, ColdPoC
from cold.env import (
    ACTION, ARCHIVE, DCC, DPP, GENTEST, GENTEST_CPYTHON, GENTEST_MRUBY,
    GENTEST_QUICKJS, GENTEST_V8, GENTEST_VIM, MAX_PROC, MODEL, SOURCE, WORKSPACE
)
from cold.logger import logger

# Error type suffixes for gentest (only track build/compile errors)
SUFFIX_BUILD_ERR = ".build_err"
SUFFIX_COMPILE_ERR = ".compile_err"

parser = argparse.ArgumentParser()
parser.add_argument("--id", type=str, help="ID of the vulnerability")
parser.add_argument("--skip-sec", action="store_true", help="Skip security test")
parser.add_argument("--skip-func", action="store_true", help="Skip function test")
parser.add_argument("--skip-post", action="store_true", help="Skip post test")
parser.add_argument("--update", action="store_true", help="Update report")
parser.add_argument("--max-proc", type=int, default=MAX_PROC, help="Max number of processes")

args = parser.parse_args()


class CLIException(Exception): ...


def check_internal(id_path: Path) -> None:
    builder = ColdBuilder(id_path.name)
    patch_path = id_path / "patch.diff"
    id = id_path.name

    if not args.skip_sec:
        for poc_path in (id_path / "input").iterdir():
            report = builder.replay(ColdPoC(poc_path))
            if report is None:
                raise CLIException(f"{id} {poc_path.name} cannot be replayed")
            report_txt = id_path / "report.txt"
            if not report_txt.is_file():
                report_txt.write_text(report.content)

        assert report is not None
        logger.info(f"[✅] {id} can trigger sanitizer")
        if args.update:
            report_txt = id_path / "report.txt"
            workspace_prefix = WORKSPACE.as_posix()
            report_txt.write_text(report.content.replace(workspace_prefix, ""))

        for poc_path in (id_path / "input").iterdir():
            if builder.replay(ColdPoC(poc_path), patch_path.read_text()) is not None:
                raise CLIException(f"{id} with patch be replayed")

        logger.info(f"[✅] {id} can be repaired")

    if not args.skip_func:
        builder.function_test()
        logger.info(f"[✅] {id} can pass function test")
        builder.function_test(patch_path.read_text())
        logger.info(f"[✅] {id} with patch can pass function test")

    if not args.skip_post:
        builder.post_function_test(patch_path.read_text())
        logger.info(f"[✅] {id} with patch can pass post function test")


def check() -> None:
    logger.info("[🔍] Cold Patch CLI Starting (check)")

    failed = False
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_proc) as executor:
        future_to_id: Dict[Any, str] = {}
        for id_path in SOURCE.iterdir():
            config = id_path / "config.yaml"
            if config.is_file() and (args.id is None or id_path.name == args.id):
                future = executor.submit(check_internal, id_path)
                future_to_id[future] = id_path.name

        for future in concurrent.futures.as_completed(future_to_id):
            id = future_to_id[future]
            try:
                future.result()
            except Exception as e:
                logger.error(f"[🚨][{id}] {e}")

                failed = True
                err_file = SOURCE / id / "check.err"
                err_file.write_text(str(e))

    if failed:
        logger.error("[🚨] Some tests failed")
        os._exit(1)


def double_check_internal(id_path: Path) -> None:
    builder = ColdBuilder(id_path.name)
    for engine in ["patchagent", "san2patch"]:
        for i in range(5):
            log_file = ARCHIVE / engine / f"{id_path.name}:{MODEL}:{i}.json"
            post_file = ARCHIVE / engine / f"{id_path.name}:{MODEL}:{i}:post.json"
            if log_file.is_file() and post_file.is_file():
                post_data = json.loads(post_file.read_text())
                patch, result = post_data["patch"], post_data["result"]

                err_file = ARCHIVE / engine / f"{id_path.name}:{MODEL}:{i}.err"

                try:
                    builder.function_test(patch)
                except (BuilderProcessError, BuilderTimeoutError) as e:
                    err_file.write_text(f"{e}")
                    continue

                try:
                    builder.post_function_test(patch)
                    if result is False:
                        post_file.write_text(json.dumps({"patch": patch, "result": True}))
                        err_file.write_text(f"The original post function test result is {result} but the current result is {True}")
                except (BuilderProcessError, BuilderTimeoutError) as e:
                    if result is True:
                        post_file.write_text(json.dumps({"patch": patch, "result": False, "error": str(e)}))
                        err_file.write_text(f"The original post function test result is {result} but the current result is {False}")


def double_check() -> None:
    logger.info("[🔍] Cold Patch CLI Starting (double-check)")

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_proc) as executor:
        future_to_id = {}
        for id_path in SOURCE.iterdir():
            config = id_path / "config.yaml"
            if config.is_file() and (args.id is None or id_path.name == args.id):
                future = executor.submit(double_check_internal, id_path)
                future_to_id[future] = id_path.name

        for future in concurrent.futures.as_completed(future_to_id):
            id = future_to_id[future]
            try:
                future.result()
            except Exception as e:
                logger.error(f"[🚨][{id}] {e}")


def patchagent_interal(id_path: Path) -> None:
    for i in range(5):
        log_file = ARCHIVE / "patchagent" / f"{id_path.name}:{MODEL}:{i}.json"
        if not log_file.is_file():
            tmp_file = ARCHIVE / "patchagent" / f"{id_path.name}:{MODEL}:{i}.json.tmp"

            try:
                builder = ColdBuilder(id_path.name)

                pocs: List[ColdPoC] = []
                for poc_path in (id_path / "input").iterdir():
                    pocs.append(ColdPoC(poc_path))

                patch_task = PatchTask(pocs, builder, log_file=tmp_file)

                result, err_msg = patch_task.initialize()
                if result != ValidationResult.BugDetected:
                    assert patch_task._report is None, err_msg
                    patch_task._report = builder.parse_sanitizer_report((id_path / "report.txt").read_text(errors="ignore"))

                if builder.project == "v8":
                    patch_task.repair(agent_generator(model=MODEL, fast=True))
                else:
                    patch_task.repair(agent_generator(model=MODEL, fast=False))

                log_file.write_bytes(tmp_file.read_bytes())
                tmp_file.unlink()
            except Exception:
                if tmp_file.is_file():
                    tmp_file.unlink()

                err_file = ARCHIVE / "patchagent" / f"{id_path.name}:{MODEL}:{i}.err"
                err_file.write_text(traceback.format_exc())
                raise

        post_verify = ARCHIVE / "patchagent" / f"{id_path.name}:{MODEL}:{i}:post.json"
        patch = None
        for round in json.loads(log_file.read_text()):
            if round["patch"] is not None:
                patch = round["patch"]
                break

        if not post_verify.is_file() and patch is not None:
            builder = ColdBuilder(id_path.name)
            try:
                builder.post_function_test(patch)
                post_verify.write_text(json.dumps({"patch": patch, "result": True}))
            except (BuilderProcessError, BuilderTimeoutError) as e:
                post_verify.write_text(json.dumps({"patch": patch, "result": False, "error": str(e)}))


def patchagent() -> None:
    logger.info("[🔍] Cold Patch CLI Starting (patchagent)")

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_proc) as executor:
        future_to_id = {}
        for id_path in SOURCE.iterdir():
            config = id_path / "config.yaml"
            if config.is_file() and (args.id is None or id_path.name == args.id):
                future = executor.submit(patchagent_interal, id_path)
                future_to_id[future] = id_path.name

        for future in concurrent.futures.as_completed(future_to_id):
            id = future_to_id[future]
            try:
                future.result()
            except Exception as e:
                logger.error(f"[🚨][{id}] {e}")


def san2patch_internal_once(id_path: Path, i: int) -> str | None:
    san2patch_model_list = {
        "gpt-4.1": OpenAIGPT41Patcher,
        "claude-4-sonnet": Claude4SonnetPatcher,
    }

    data_dir_tmp = TemporaryDirectory()
    data_dir = Path(data_dir_tmp.name)

    assert MODEL in san2patch_model_list, f"Model {MODEL} not found in {san2patch_model_list}"
    model_class = san2patch_model_list[MODEL]

    stage_num = 0
    data_dir.mkdir(parents=True, exist_ok=True)
    version = "tot"
    experiment_name = None
    docker_id = None
    select_method = "sample"
    temperature_setting = "medium_high"

    os.environ["DCC_SAN2PATCH"] = DCC
    os.environ["DPP_SAN2PATCH"] = DPP
    os.environ[f"DATASET_FINAL_DIR_{id_path.name}_{i}"] = data_dir.as_posix()

    # builder
    logger.info(f"[🔍] Cold Patch CLI Starting (san2patch) {id_path.name}")
    builder = ColdBuilder(id_path.name)
    logger.info(f"[🔍] Cold Patch CLI Starting (san2patch) {id_path.name} {builder.source_repo.working_dir}")

    # prepare the content of the data dir

    # read the config file
    coldpatch_config_yaml = id_path / "config.yaml"
    with open(coldpatch_config_yaml, "r") as f:
        coldpatch_config = yaml.load(f, Loader=yaml.FullLoader)

    # repo dir
    repo_dir = data_dir / "repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    current_repo_dir = repo_dir / f'{coldpatch_config["project"]}_{id_path.name}'
    current_repo_dir.mkdir(parents=True, exist_ok=True)
    # copy the repo
    source_repo = builder.source_repo
    shutil.copytree(source_repo.working_dir, current_repo_dir, dirs_exist_ok=True)

    # repo copy dir
    repo_copy_dir = data_dir / "repo_copy"
    repo_copy_dir.mkdir(parents=True, exist_ok=True)

    # sanitizer report
    sanitizer_dir = data_dir / "sanitizer"
    sanitizer_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(id_path / "report.txt", sanitizer_dir / (id_path.name + ".san"))

    sanitizer_raw_dir = data_dir / "sanitizer_raw"
    sanitizer_raw_dir.mkdir(parents=True, exist_ok=True)

    # poc
    input_dir = data_dir / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    # copy the only file in the input dir and rename it to poc.bin
    for file in (id_path / "input").iterdir():
        if file.is_file():
            shutil.copy(file, input_dir / file.name)

    # scripts
    script_dir = data_dir / "script"
    script_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(builder.build_script, script_dir / "build.sh")
    shutil.copy(builder.exploit_script, script_dir / "exp.sh")
    shutil.copy(builder.test_script, script_dir / "test.sh")

    # vuln dir & config file
    vuln_dir = data_dir / "vuln"
    vuln_dir.mkdir(parents=True, exist_ok=True)
    # translate the configure file

    gen_diff_dir = data_dir / "gen_diff"

    san2patch_config = {
        "id": i,
        "subject": coldpatch_config["project"],
        "bug_id": id_path.name,
        "source_file": "/",
        "line_numbers": [],
        "failing_test": [],
        "passing_test": [],
        "count_neg": 0,
        "count_pos": 0,
        "binary_path": coldpatch_config["binary"],
        "crash_input": "$POC input/poc.bin",
        "exploit_file_list": ["input/poc.bin"],
        "crash_stack_trace": [],
        "test_timeout": 10,
        "language": "c",
        "config_script": "config.sh",
        "build_script": "build.sh",
        "test_script": "test.sh",
        "build_command": "make -j20 CFLAGS='-static' CPPFLAGS='-static' LDFLAGS='-static'",
        "bug_type": coldpatch_config["type"],
        # for reproducing
        "sanitizer": coldpatch_config["sanitizer"],
    }
    with open(vuln_dir / (id_path.name + ".json"), "w") as f:
        json.dump(san2patch_config, f)

    patcher = San2Patcher(
        vuln_id=id_path.name,
        data_dir=data_dir.as_posix(),
        mode="test",
        LLMPatcher=model_class,
        version=version,
        aim_run=None,
        experiment_name=experiment_name,
        docker_id=docker_id,
        select_method=select_method,
        temperature_setting=temperature_setting,
    )

    res = patcher.make_diff(try_cnt=i, stage=stage_num)
    if TestEvalRetCode.SUCCESS.value in res.patch_success:
        # copy the patch to the archive
        success_idx = res.patch_success.index(TestEvalRetCode.SUCCESS.value)

        # Get success diff file from dataset_dir
        success_diff_file = os.path.join(
            gen_diff_dir.as_posix(),
            id_path.name,
            f"stage_{stage_num}_{i}",
            f"{id_path.name}_{success_idx}.diff",
        )
        return Path(success_diff_file).read_text()

    return None


def san2patch_internal(id_path: Path) -> None:
    for i in range(5):
        log_file = ARCHIVE / "san2patch" / f"{id_path.name}:{MODEL}:{i}.json"
        if not log_file.is_file():
            try:
                for j in range(1 if id_path.name.startswith("v8-") else 5):
                    try:
                        diff_file_content = san2patch_internal_once(id_path, j)
                        if diff_file_content is not None:
                            log_file.write_text(json.dumps([{"patch": diff_file_content}]))
                            break
                    except San2PatchInternalError:
                        continue
                else:
                    log_file.write_text(json.dumps([{"patch": None} for _ in range(5)]))
            except Exception:
                err_file = ARCHIVE / "san2patch" / f"{id_path.name}:{MODEL}:{i}.err"
                err_file.write_text(traceback.format_exc())
                continue

        post_verify = ARCHIVE / "san2patch" / f"{id_path.name}:{MODEL}:{i}:post.json"

        patch = None
        if log_file.is_file():
            data = json.loads(log_file.read_text())
            if len(data) > 0 and data[0]["patch"] is not None:
                patch = data[0]["patch"]

            if not post_verify.is_file() and patch is not None:
                builder = ColdBuilder(id_path.name)
                try:
                    builder.post_function_test(patch)
                    post_verify.write_text(json.dumps({"patch": patch, "result": True}))
                except (BuilderProcessError, BuilderTimeoutError) as e:
                    post_verify.write_text(json.dumps({"patch": patch, "result": False, "error": str(e)}))


def san2patch() -> None:
    logger.info("[🔍] Cold Patch CLI Starting (san2patch)")

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_proc) as executor:
        future_to_id = {}
        for id_path in SOURCE.iterdir():
            config = id_path / "config.yaml"
            if config.is_file() and (args.id is None or id_path.name == args.id):
                future = executor.submit(san2patch_internal, id_path)
                future_to_id[future] = id_path.name

        for future in concurrent.futures.as_completed(future_to_id):
            id = future_to_id[future]
            try:
                future.result()
            except Exception as e:
                logger.error(f"[🚨][{id}] {e}")


def swe_agent_internal(id_path: Path) -> None:
    for model in ["gpt-4.1", "claude-4-sonnet"]:
        for i in range(5):
            patch_file = ARCHIVE / "mswe-agent" / f"{id_path.name}:{model}:{i}.patch"

            if not patch_file.is_file() and model == "gpt-4.1":
                patch_file = ARCHIVE / "mswe-agent" / f"{id_path.name}:gpt4.1:{i}.patch"

            log_file = ARCHIVE / "mswe-agent" / f"{id_path.name}:{model}:{i}.json"
            if patch_file.is_file() and not log_file.is_file():
                original_patch = patch_file.read_text()
                if len(original_patch) == 0:
                    log_file.write_text(json.dumps([{"patch": None, "error": "No patch generated"}]))
                    continue

                builder = ColdBuilder(id_path.name)
                patch = builder.format_patch(original_patch)

                if patch is None:
                    log_file.write_text(json.dumps([{"patch": None, "error": "The format of the patch is invalid"}]))
                    continue

                pocs: List[ColdPoC] = []
                for poc_path in (id_path / "input").iterdir():
                    pocs.append(ColdPoC(poc_path))

                patch_task = PatchTask(pocs, builder, log_file=None)
                result, error_message = patch_task.validate(patch)
                if result == ValidationResult.BugFree:
                    log_file.write_text(json.dumps([{"patch": patch}]))
                else:
                    log_file.write_text(json.dumps([{"patch": None, "error": error_message}]))

            post_verify = ARCHIVE / "mswe-agent" / f"{id_path.name}:{model}:{i}:post.json"
            if not post_verify.is_file() and log_file.is_file() and json.loads(log_file.read_text())[0]["patch"] is not None:
                builder = ColdBuilder(id_path.name)
                patch = json.loads(log_file.read_text())[0]["patch"]
                try:
                    builder.post_function_test(patch)
                    post_verify.write_text(json.dumps({"patch": patch, "result": True}))
                except (BuilderProcessError, BuilderTimeoutError) as e:
                    post_verify.write_text(json.dumps({"patch": patch, "result": False, "error": str(e)}))


def swe_agent() -> None:
    logger.info("[🔍] Cold Patch CLI Starting (swe-agent)")

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_proc) as executor:
        future_to_id = {}
        for id_path in SOURCE.iterdir():
            config = id_path / "config.yaml"
            if config.is_file() and (args.id is None or id_path.name == args.id):
                future = executor.submit(swe_agent_internal, id_path)
                future_to_id[future] = id_path.name

        for future in concurrent.futures.as_completed(future_to_id):
            id = future_to_id[future]
            try:
                future.result()
            except Exception as e:
                logger.error(f"[🚨][{id}] {e}")


def get_gentest_compile_command(project: str, build_path: Path, test_file: Path, output_file: Path, build_env: Dict[str, str]) -> List[str]:
    """Get compile command for a specific project using build_env from ColdBuilder."""
    install_dir = build_path / "install"

    # Use build_env from ColdBuilder (contains CC, CXX, CFLAGS, CXXFLAGS, LDFLAGS based on sanitizer)
    cc = build_env.get("CC", DCC)
    cxx = build_env.get("CXX", DPP)
    cflags = build_env.get("CFLAGS", "").split()
    cxxflags = build_env.get("CXXFLAGS", "").split()
    ldflags = build_env.get("LDFLAGS", "").split()

    if project == "icu":
        cmd = [cxx] + cxxflags + [
            "-I", str(install_dir / "include"),
            "-L", str(install_dir / "lib"),
            "-licuuc", "-licui18n", "-licudata",
            f"-Wl,-rpath,{install_dir / 'lib'}",
        ] + ldflags + ["-o", str(output_file), str(test_file)]
    elif project == "hdf5":
        cmd = [cc] + cflags + [
            "-I", str(install_dir / "include"),
            "-L", str(install_dir / "lib"),
            "-lhdf5",
            f"-Wl,-rpath={install_dir / 'lib'}",
        ] + ldflags + ["-o", str(output_file), str(test_file)]
    elif project == "pcapplusplus":
        cmd = [cxx] + cxxflags + [
            "-I", str(install_dir / "include" / "pcapplusplus"),
            "-L", str(install_dir / "lib"),
            "-lPcap++", "-lCommon++", "-lPacket++",
            f"-Wl,-rpath={install_dir / 'lib'}",
        ] + ldflags + ["-o", str(output_file), str(test_file)]
    elif project == "libtiff":
        cmd = [cc] + cflags + [
            "-I", str(install_dir / "include"),
            "-L", str(install_dir / "lib"),
            "-ltiff", "-lz", "-ljpeg", "-llzma",
            f"-Wl,-rpath={install_dir / 'lib'}",
        ] + ldflags + ["-o", str(output_file), str(test_file)]
    else:
        raise ValueError(f"Unknown project: {project}")

    # Filter out empty strings from flags
    return [x for x in cmd if x]


def gentest_internal_cpython(id_path: Path) -> None:
    """Test generated.py files against patches for cpython vulnerability.

    For cpython:
    - Build patched CPython once, pass validate_fn to generate_test
    - generate_test handles generation + validation + feedback loop
    - Tests against AI patches
    """
    import subprocess
    from cold.generator_cpython import generate_test

    vuln_id = id_path.name
    case_dir = GENTEST_CPYTHON / vuln_id

    if not case_dir.exists() or not (case_dir / "poc.py").exists():
        logger.warning(f"[{vuln_id}] No case directory or poc.py found in {case_dir}")
        return

    dev_patch_file = id_path / "patch.diff"
    if not dev_patch_file.is_file():
        logger.warning(f"[{vuln_id}] No developer patch (patch.diff) found")
        return
    dev_patch = dev_patch_file.read_text()

    output_dir = ARCHIVE / "gentest" / vuln_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check which tests need processing
    need_processing: List[int] = []
    valid_gen_files: List[tuple] = []

    for gen_num in [1, 2, 3]:
        gen_file = case_dir / f"generated_{gen_num}.py"
        valid_marker = output_dir / f"dev:gen{gen_num}.valid"

        if valid_marker.exists() and gen_file.exists():
            logger.info(f"[{vuln_id}] gen{gen_num}: SKIP (already validated)")
            valid_gen_files.append((gen_num, gen_file))
        else:
            need_processing.append(gen_num)

    if need_processing:
        logger.info(f"[{vuln_id}] Building CPython and processing {len(need_processing)} tests")

        try:
            builder = ColdBuilder(vuln_id)
            builder.build(dev_patch)

            python_binary = builder.build_path / "python"
            if not python_binary.exists():
                logger.error(f"[{vuln_id}] Python binary not found at {python_binary}")
                return

            # Validate function using built Python (include replay_env for sanitizer options)
            def validate_fn(gen_file: Path):
                try:
                    env = os.environ | builder.replay_env
                    env["TERM"] = "xterm"
                    result = subprocess.run(
                        [str(python_binary), str(gen_file)],
                        capture_output=True,
                        timeout=60,
                        cwd=str(builder.build_path),
                        env=env
                    )
                    if result.returncode == 0:
                        return True, "", ""
                    stderr = result.stderr.decode(errors='replace')[:4000] if result.stderr else ""
                    return False, "runtime", stderr or f"Exit code {result.returncode}"
                except subprocess.TimeoutExpired:
                    return False, "timeout", "Timeout"

            for gen_num in need_processing:
                gen_file = case_dir / f"generated_{gen_num}.py"
                logger.info(f"[{vuln_id}] gen{gen_num}: Processing...")

                _, _, ok, msg = generate_test(case_dir, gen_num, validate_fn=validate_fn)

                if ok:
                    logger.info(f"[✅][{vuln_id}] gen{gen_num}: VALID")
                    valid_gen_files.append((gen_num, gen_file))
                    (output_dir / f"dev:gen{gen_num}.valid").touch()
                else:
                    logger.warning(f"[{vuln_id}] gen{gen_num}: FAILED - {msg}")

        except (BuilderProcessError, BuilderTimeoutError) as e:
            logger.error(f"[🚨][{vuln_id}] Failed to build with developer patch: {e}")
            return

    if not valid_gen_files:
        logger.warning(f"[{vuln_id}] No valid generated tests found")
        return

    # Step 2: Load AI-generated patches
    patches: List[tuple] = []
    for agent in ["patchagent", "san2patch", "mswe-agent"]:
        agent_dir = ARCHIVE / agent
        if not agent_dir.is_dir():
            continue
        for post_file in agent_dir.glob(f"{vuln_id}:*:post.json"):
            try:
                data = json.loads(post_file.read_text())
                patch = data.get("patch")
                if patch:
                    parts = post_file.stem.replace(":post", "").split(":")
                    source = f"{agent}:{parts[1]}:{parts[2]}" if len(parts) >= 3 else f"{agent}:{post_file.stem}"
                    patches.append((source, patch))
            except Exception as e:
                logger.warning(f"Failed to load {post_file}: {e}")

    if not patches:
        logger.info(f"[{vuln_id}] No AI patches found")
        return

    # Step 3: Test valid generated.py against AI patches
    logger.info(f"[{vuln_id}] Testing {len(valid_gen_files)} valid tests x {len(patches)} AI patches")

    total_patches = len(patches)
    skipped_count = 0

    for patch_idx, (patch_source, patch) in enumerate(patches, 1):
        # Check which gen files need testing for this patch
        gen_files_to_test = []
        for gen_num, gen_file in valid_gen_files:
            result_file = output_dir / f"{patch_source}:gen{gen_num}.json"
            build_err_file = output_dir / f"{patch_source}:gen{gen_num}{SUFFIX_BUILD_ERR}.json"

            if result_file.exists() or build_err_file.exists():
                skipped_count += 1
                continue
            gen_files_to_test.append((gen_num, gen_file))

        if not gen_files_to_test:
            continue

        logger.info(f"[{vuln_id}] [{patch_idx}/{total_patches}] Processing {patch_source} ({len(gen_files_to_test)} tests)")

        try:
            builder = ColdBuilder(vuln_id)

            # Build with AI patch
            try:
                builder.build(patch)
            except (BuilderProcessError, BuilderTimeoutError) as e:
                logger.warning(f"[{vuln_id}] [{patch_idx}/{total_patches}] {patch_source}: BUILD_ERR")
                for gen_num, _ in gen_files_to_test:
                    err_file = output_dir / f"{patch_source}:gen{gen_num}{SUFFIX_BUILD_ERR}.json"
                    err_file.write_text(json.dumps({"patch": patch, "result": False, "error": str(e)}))
                continue

            python_binary = builder.build_path / "python"
            if not python_binary.exists():
                logger.warning(f"[{vuln_id}] [{patch_idx}/{total_patches}] {patch_source}: No python binary")
                continue

            for gen_num, gen_file in gen_files_to_test:
                result_file = output_dir / f"{patch_source}:gen{gen_num}.json"

                try:
                    # Run: ./python generated_N.py with replay_env for sanitizer options
                    env = os.environ | builder.replay_env
                    env["TERM"] = "xterm"
                    run_result = subprocess.run(
                        [str(python_binary), str(gen_file)],
                        capture_output=True,
                        timeout=60,
                        cwd=str(builder.build_path),
                        env=env
                    )

                    if run_result.returncode == 0:
                        result_file.write_text(json.dumps({"patch": patch, "result": True}))
                        logger.info(f"[✅][{vuln_id}] [{patch_idx}/{total_patches}] {patch_source} gen{gen_num}: PASS")
                    else:
                        stderr_msg = run_result.stderr.decode(errors='replace') if run_result.stderr else ""
                        result_file.write_text(json.dumps({
                            "patch": patch,
                            "result": False,
                            "error": stderr_msg[:4000] or f"Exit code {run_result.returncode}"
                        }))
                        logger.info(f"[❌][{vuln_id}] [{patch_idx}/{total_patches}] {patch_source} gen{gen_num}: FAIL")

                except subprocess.TimeoutExpired:
                    result_file.write_text(json.dumps({"patch": patch, "result": False, "error": "Timeout"}))
                    logger.warning(f"[{vuln_id}] [{patch_idx}/{total_patches}] {patch_source} gen{gen_num}: TIMEOUT")

        except Exception as e:
            logger.error(f"[🚨][{vuln_id}] [{patch_idx}/{total_patches}] {patch_source}: {e}")

    if skipped_count > 0:
        logger.info(f"[{vuln_id}] Skipped {skipped_count} already completed tests")


def gentest_internal_cc(id_path: Path) -> None:
    """Test generated.cc files against patches for C/C++ vulnerability.

    First validates generated.cc against developer patch (patch.diff).
    If generated.cc doesn't exist or fails validation, regenerate with feedback.
    Only valid tests are run against AI patches.
    """
    import subprocess
    from cold.generator import generate_test

    vuln_id = id_path.name
    config_data = yaml.safe_load((id_path / "config.yaml").read_text())
    project = config_data["project"]

    # Get developer patch
    dev_patch_file = id_path / "patch.diff"
    if not dev_patch_file.is_file():
        logger.warning(f"[{vuln_id}] No developer patch (patch.diff) found")
        return
    dev_patch = dev_patch_file.read_text()

    # Get input files (like exp.sh uses)
    input_dir = id_path / "input"
    input_files: List[Path] = []
    if input_dir.is_dir():
        input_files = list(input_dir.iterdir())
    # Use first input file if available
    input_file = input_files[0] if input_files else None

    # Find or generate files
    gen_files: List[tuple] = []
    case_dir = GENTEST / "proj" / project / vuln_id

    for gen_num in [1, 2, 3]:
        gen_file = case_dir / f"generated{gen_num}" / "generated.cc"

        if not gen_file.is_file():
            # Generate if missing
            if case_dir.exists() and (case_dir / "harness.cc").exists():
                logger.info(f"[{vuln_id}] gen{gen_num}: Generating (file missing)...")
                _, _, ok, msg = generate_test(case_dir, project, gen_num, use_feedback=True)
                if ok:
                    logger.info(f"[✅][{vuln_id}] gen{gen_num}: Generated successfully")
                else:
                    logger.warning(f"[{vuln_id}] gen{gen_num}: Generation failed - {msg}")
                    continue

        if gen_file.is_file():
            gen_files.append((gen_num, gen_file))

    if not gen_files:
        logger.warning(f"[{vuln_id}] No generated files found")
        return

    # Output directory
    output_dir = ARCHIVE / "gentest" / vuln_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Validate generated.cc against developer patch
    # Check which tests are already validated (valid or invalid)
    valid_gen_files: List[tuple] = []
    need_validation: List[tuple] = []

    for gen_num, gen_file in gen_files:
        valid_marker = output_dir / f"dev:gen{gen_num}.valid"

        if valid_marker.exists():
            logger.info(f"[{vuln_id}] gen{gen_num}: SKIP (already validated)")
            valid_gen_files.append((gen_num, gen_file))
        else:
            need_validation.append((gen_num, gen_file))

    if need_validation:
        logger.info(f"[{vuln_id}] Validating {len(need_validation)} generated files against developer patch")

        try:
            builder = ColdBuilder(vuln_id)
            builder.build(dev_patch)

            for gen_num, gen_file in need_validation:
                test_binary = output_dir / f".test_binary_{gen_num}"
                is_valid = False
                error_type = ""
                error_msg = ""

                try:
                    # Compile generated.cc
                    compile_cmd = get_gentest_compile_command(project, builder.build_path, gen_file, test_binary, builder.build_env)
                    compile_result = subprocess.run(compile_cmd, capture_output=True, timeout=120)

                    if compile_result.returncode != 0:
                        error_type = "compile"
                        error_msg = compile_result.stderr.decode(errors='replace')[:4000] if compile_result.stderr else ""
                    else:
                        # Run the test with input file if available
                        run_cmd = [str(test_binary)]
                        if input_file:
                            run_cmd.append(str(input_file.resolve()))
                        run_result = subprocess.run(run_cmd, capture_output=True, timeout=60, cwd=builder.build_path)

                        if run_result.returncode == 0:
                            is_valid = True
                        else:
                            error_type = "runtime"
                            error_msg = run_result.stderr.decode(errors='replace')[:4000] if run_result.stderr else f"Exit code {run_result.returncode}"

                    # Clean up
                    if test_binary.exists():
                        test_binary.unlink()

                except subprocess.TimeoutExpired:
                    error_type = "timeout"
                    error_msg = "Timeout with developer patch"

                if is_valid:
                    logger.info(f"[✅][{vuln_id}] gen{gen_num}: VALID (passes with dev patch)")
                    valid_gen_files.append((gen_num, gen_file))
                    (output_dir / f"dev:gen{gen_num}.valid").touch()
                else:
                    # Try to regenerate with feedback
                    if case_dir.exists() and (case_dir / "harness.cc").exists():
                        logger.info(f"[{vuln_id}] gen{gen_num}: FAIL ({error_type}) - regenerating with feedback...")
                        # Delete old generated file
                        if gen_file.exists():
                            gen_file.unlink()
                        # Regenerate with feedback
                        _, _, ok, msg = generate_test(case_dir, project, gen_num, use_feedback=True)
                        if ok:
                            logger.info(f"[✅][{vuln_id}] gen{gen_num}: Regenerated successfully")
                            valid_gen_files.append((gen_num, gen_file))
                            (output_dir / f"dev:gen{gen_num}.valid").touch()
                        else:
                            logger.warning(f"[{vuln_id}] gen{gen_num}: Regeneration failed - {msg}")
                            err_file = output_dir / f"dev:gen{gen_num}.invalid.json"
                            err_file.write_text(json.dumps({
                                "patch": dev_patch,
                                "result": False,
                                "error": f"Regeneration failed: {msg}"
                            }))
                    else:
                        logger.warning(f"[{vuln_id}] gen{gen_num}: INVALID ({error_type})")
                        err_file = output_dir / f"dev:gen{gen_num}.invalid.json"
                        err_file.write_text(json.dumps({
                            "patch": dev_patch,
                            "result": False,
                            "error": f"{error_type}: {error_msg}"
                        }))

        except (BuilderProcessError, BuilderTimeoutError) as e:
            logger.error(f"[🚨][{vuln_id}] Failed to build with developer patch: {e}")
            return

    if not valid_gen_files:
        logger.warning(f"[{vuln_id}] No valid generated tests found")
        return

    # Step 2: Load AI-generated patches
    patches: List[tuple] = []
    for agent in ["patchagent", "san2patch", "mswe-agent"]:
        agent_dir = ARCHIVE / agent
        if not agent_dir.is_dir():
            continue
        for post_file in agent_dir.glob(f"{vuln_id}:*:post.json"):
            try:
                data = json.loads(post_file.read_text())
                patch = data.get("patch")
                if patch:
                    parts = post_file.stem.replace(":post", "").split(":")
                    source = f"{agent}:{parts[1]}:{parts[2]}" if len(parts) >= 3 else f"{agent}:{post_file.stem}"
                    patches.append((source, patch))
            except Exception as e:
                logger.warning(f"Failed to load {post_file}: {e}")

    if not patches:
        logger.warning(f"[{vuln_id}] No AI patches found")
        return

    # Step 3: Test valid generated.cc against AI patches
    logger.info(f"[{vuln_id}] Testing {len(valid_gen_files)} valid tests x {len(patches)} AI patches")

    total_patches = len(patches)
    skipped_count = 0

    for patch_idx, (patch_source, patch) in enumerate(patches, 1):
        # Check which gen files need testing for this patch
        gen_files_to_test = []
        for gen_num, gen_file in valid_gen_files:
            result_file = output_dir / f"{patch_source}:gen{gen_num}.json"
            build_err_file = output_dir / f"{patch_source}:gen{gen_num}{SUFFIX_BUILD_ERR}.json"
            compile_err_file = output_dir / f"{patch_source}:gen{gen_num}{SUFFIX_COMPILE_ERR}.json"

            if result_file.exists() or build_err_file.exists() or compile_err_file.exists():
                skipped_count += 1
                continue
            gen_files_to_test.append((gen_num, gen_file))

        if not gen_files_to_test:
            continue  # All tests for this patch already done

        logger.info(f"[{vuln_id}] [{patch_idx}/{total_patches}] Processing {patch_source} ({len(gen_files_to_test)} tests)")

        try:
            builder = ColdBuilder(vuln_id)

            # Build with AI patch
            try:
                builder.build(patch)
            except (BuilderProcessError, BuilderTimeoutError) as e:
                logger.warning(f"[{vuln_id}] [{patch_idx}/{total_patches}] {patch_source}: BUILD_ERR")
                for gen_num, _ in gen_files_to_test:
                    err_file = output_dir / f"{patch_source}:gen{gen_num}{SUFFIX_BUILD_ERR}.json"
                    err_file.write_text(json.dumps({"patch": patch, "result": False, "error": str(e)}))
                continue

            for gen_num, gen_file in gen_files_to_test:
                test_binary = output_dir / f".test_binary_{gen_num}"
                result_file = output_dir / f"{patch_source}:gen{gen_num}.json"

                try:
                    # Compile generated.cc
                    compile_cmd = get_gentest_compile_command(project, builder.build_path, gen_file, test_binary, builder.build_env)
                    compile_result = subprocess.run(compile_cmd, capture_output=True, timeout=120)

                    if compile_result.returncode != 0:
                        stderr_msg = compile_result.stderr.decode(errors='replace') if compile_result.stderr else ""
                        stdout_msg = compile_result.stdout.decode(errors='replace') if compile_result.stdout else ""
                        err_file = output_dir / f"{patch_source}:gen{gen_num}{SUFFIX_COMPILE_ERR}.json"
                        err_file.write_text(json.dumps({
                            "patch": patch,
                            "result": False,
                            "error": stderr_msg[:4000] or stdout_msg[:4000] or "Compile failed"
                        }))
                        logger.warning(f"[{vuln_id}] [{patch_idx}/{total_patches}] {patch_source} gen{gen_num}: COMPILE_ERR")
                        continue

                    # Run the test with input file if available
                    run_cmd = [str(test_binary)]
                    if input_file:
                        run_cmd.append(str(input_file.resolve()))
                    run_result = subprocess.run(run_cmd, capture_output=True, timeout=60, cwd=builder.build_path)

                    # Save result to JSON
                    if run_result.returncode == 0:
                        result_file.write_text(json.dumps({"patch": patch, "result": True}))
                        logger.info(f"[✅][{vuln_id}] [{patch_idx}/{total_patches}] {patch_source} gen{gen_num}: PASS")
                    else:
                        stderr_msg = run_result.stderr.decode(errors='replace') if run_result.stderr else ""
                        result_file.write_text(json.dumps({
                            "patch": patch,
                            "result": False,
                            "error": stderr_msg[:4000] or f"Exit code {run_result.returncode}"
                        }))
                        logger.info(f"[❌][{vuln_id}] [{patch_idx}/{total_patches}] {patch_source} gen{gen_num}: FAIL")

                    # Clean up test binary
                    if test_binary.exists():
                        test_binary.unlink()

                except subprocess.TimeoutExpired as e:
                    err_file = output_dir / f"{patch_source}:gen{gen_num}{SUFFIX_COMPILE_ERR}.json"
                    err_file.write_text(json.dumps({"patch": patch, "result": False, "error": f"Timeout: {e}"}))
                    logger.warning(f"[{vuln_id}] [{patch_idx}/{total_patches}] {patch_source} gen{gen_num}: TIMEOUT")

        except Exception as e:
            logger.error(f"[🚨][{vuln_id}] [{patch_idx}/{total_patches}] {patch_source}: {e}")

    if skipped_count > 0:
        logger.info(f"[{vuln_id}] Skipped {skipped_count} already completed tests")


def gentest_internal_mruby(id_path: Path) -> None:
    """Test generated.rb files against patches for mruby vulnerability."""
    import subprocess
    import re
    from cold.generator_mruby import generate_test

    vuln_id = id_path.name
    case_dir = GENTEST_MRUBY / vuln_id

    if not case_dir.exists() or not (case_dir / "poc.rb").exists():
        logger.warning(f"[{vuln_id}] No case directory or poc.rb found in {case_dir}")
        return

    dev_patch_file = id_path / "patch.diff"
    if not dev_patch_file.is_file():
        logger.warning(f"[{vuln_id}] No developer patch (patch.diff) found")
        return
    dev_patch = dev_patch_file.read_text()

    output_dir = ARCHIVE / "gentest" / vuln_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check which tests need processing
    need_processing: List[int] = []
    valid_gen_files: List[tuple] = []

    for gen_num in [1, 2, 3]:
        gen_file = case_dir / f"generated_{gen_num}.rb"
        valid_marker = output_dir / f"dev:gen{gen_num}.valid"

        if valid_marker.exists() and gen_file.exists():
            logger.info(f"[{vuln_id}] gen{gen_num}: SKIP (already validated)")
            valid_gen_files.append((gen_num, gen_file))
        else:
            need_processing.append(gen_num)

    if need_processing:
        logger.info(f"[{vuln_id}] Building mruby and processing {len(need_processing)} tests")

        try:
            builder = ColdBuilder(vuln_id)
            builder.build(dev_patch)

            mruby_binary = builder.build_path / "bin" / "mruby"
            if not mruby_binary.exists():
                mruby_binary = builder.build_path / "mruby"
            if not mruby_binary.exists():
                logger.error(f"[{vuln_id}] mruby binary not found")
                return

            def validate_fn(gen_file: Path):
                try:
                    env = os.environ | builder.replay_env
                    env["TERM"] = "xterm"
                    result = subprocess.run(
                        [str(mruby_binary), str(gen_file)],
                        capture_output=True,
                        timeout=60,
                        cwd=str(builder.build_path),
                        env=env
                    )
                    if result.returncode == 0:
                        return True, "", ""
                    stderr = result.stderr.decode(errors='replace')[:4000] if result.stderr else ""
                    return False, "runtime", stderr or f"Exit code {result.returncode}"
                except subprocess.TimeoutExpired:
                    return False, "timeout", "Timeout"

            for gen_num in need_processing:
                gen_file = case_dir / f"generated_{gen_num}.rb"
                logger.info(f"[{vuln_id}] gen{gen_num}: Processing...")

                _, _, ok, msg = generate_test(case_dir, gen_num, validate_fn=validate_fn)

                if ok:
                    logger.info(f"[✅][{vuln_id}] gen{gen_num}: VALID")
                    valid_gen_files.append((gen_num, gen_file))
                    (output_dir / f"dev:gen{gen_num}.valid").touch()
                else:
                    logger.warning(f"[{vuln_id}] gen{gen_num}: FAILED - {msg}")

        except (BuilderProcessError, BuilderTimeoutError) as e:
            logger.error(f"[🚨][{vuln_id}] Failed to build with developer patch: {e}")
            return

    if not valid_gen_files:
        logger.warning(f"[{vuln_id}] No valid generated tests found")
        return

    # Load AI-generated patches
    patches: List[tuple] = []
    for agent in ["patchagent", "san2patch", "mswe-agent"]:
        agent_dir = ARCHIVE / agent
        if not agent_dir.is_dir():
            continue
        for post_file in agent_dir.glob(f"{vuln_id}:*:post.json"):
            try:
                data = json.loads(post_file.read_text())
                patch = data.get("patch")
                if patch:
                    parts = post_file.stem.replace(":post", "").split(":")
                    source = f"{agent}:{parts[1]}:{parts[2]}" if len(parts) >= 3 else f"{agent}:{post_file.stem}"
                    patches.append((source, patch))
            except Exception as e:
                logger.warning(f"Failed to load {post_file}: {e}")

    if not patches:
        logger.info(f"[{vuln_id}] No AI patches found")
        return

    # Test valid generated.rb against AI patches
    logger.info(f"[{vuln_id}] Testing {len(valid_gen_files)} valid tests x {len(patches)} AI patches")

    total_patches = len(patches)
    skipped_count = 0

    for patch_idx, (patch_source, patch) in enumerate(patches, 1):
        gen_files_to_test = []
        for gen_num, gen_file in valid_gen_files:
            result_file = output_dir / f"{patch_source}:gen{gen_num}.json"
            build_err_file = output_dir / f"{patch_source}:gen{gen_num}{SUFFIX_BUILD_ERR}.json"

            if result_file.exists() or build_err_file.exists():
                skipped_count += 1
                continue
            gen_files_to_test.append((gen_num, gen_file))

        if not gen_files_to_test:
            continue

        logger.info(f"[{vuln_id}] [{patch_idx}/{total_patches}] Processing {patch_source} ({len(gen_files_to_test)} tests)")

        try:
            builder = ColdBuilder(vuln_id)

            try:
                builder.build(patch)
            except (BuilderProcessError, BuilderTimeoutError) as e:
                logger.warning(f"[{vuln_id}] [{patch_idx}/{total_patches}] {patch_source}: BUILD_ERR")
                for gen_num, _ in gen_files_to_test:
                    err_file = output_dir / f"{patch_source}:gen{gen_num}{SUFFIX_BUILD_ERR}.json"
                    err_file.write_text(json.dumps({"patch": patch, "result": False, "error": str(e)}))
                continue

            mruby_binary = builder.build_path / "bin" / "mruby"
            if not mruby_binary.exists():
                mruby_binary = builder.build_path / "mruby"
            if not mruby_binary.exists():
                logger.warning(f"[{vuln_id}] [{patch_idx}/{total_patches}] {patch_source}: No mruby binary")
                continue

            for gen_num, gen_file in gen_files_to_test:
                result_file = output_dir / f"{patch_source}:gen{gen_num}.json"

                try:
                    env = os.environ | builder.replay_env
                    env["TERM"] = "xterm"
                    run_result = subprocess.run(
                        [str(mruby_binary), str(gen_file)],
                        capture_output=True,
                        timeout=60,
                        cwd=str(builder.build_path),
                        env=env
                    )

                    if run_result.returncode == 0:
                        result_file.write_text(json.dumps({"patch": patch, "result": True}))
                        logger.info(f"[✅][{vuln_id}] [{patch_idx}/{total_patches}] {patch_source} gen{gen_num}: PASS")
                    else:
                        stderr_msg = run_result.stderr.decode(errors='replace') if run_result.stderr else ""
                        result_file.write_text(json.dumps({
                            "patch": patch,
                            "result": False,
                            "error": stderr_msg[:4000] or f"Exit code {run_result.returncode}"
                        }))
                        logger.info(f"[❌][{vuln_id}] [{patch_idx}/{total_patches}] {patch_source} gen{gen_num}: FAIL")

                except subprocess.TimeoutExpired:
                    result_file.write_text(json.dumps({"patch": patch, "result": False, "error": "Timeout"}))
                    logger.warning(f"[{vuln_id}] [{patch_idx}/{total_patches}] {patch_source} gen{gen_num}: TIMEOUT")

        except Exception as e:
            logger.error(f"[🚨][{vuln_id}] [{patch_idx}/{total_patches}] {patch_source}: {e}")

    if skipped_count > 0:
        logger.info(f"[{vuln_id}] Skipped {skipped_count} already completed tests")


def gentest_internal_quickjs(id_path: Path) -> None:
    """Test generated.js files against patches for QuickJS vulnerability."""
    import subprocess
    from cold.generator_quickjs import generate_test

    vuln_id = id_path.name
    case_dir = GENTEST_QUICKJS / vuln_id

    if not case_dir.exists() or not (case_dir / "poc.js").exists():
        logger.warning(f"[{vuln_id}] No case directory or poc.js found in {case_dir}")
        return

    dev_patch_file = id_path / "patch.diff"
    if not dev_patch_file.is_file():
        logger.warning(f"[{vuln_id}] No developer patch (patch.diff) found")
        return
    dev_patch = dev_patch_file.read_text()

    output_dir = ARCHIVE / "gentest" / vuln_id
    output_dir.mkdir(parents=True, exist_ok=True)

    need_processing: List[int] = []
    valid_gen_files: List[tuple] = []

    for gen_num in [1, 2, 3]:
        gen_file = case_dir / f"generated_{gen_num}.js"
        valid_marker = output_dir / f"dev:gen{gen_num}.valid"

        if valid_marker.exists() and gen_file.exists():
            logger.info(f"[{vuln_id}] gen{gen_num}: SKIP (already validated)")
            valid_gen_files.append((gen_num, gen_file))
        else:
            need_processing.append(gen_num)

    if need_processing:
        logger.info(f"[{vuln_id}] Building quickjs and processing {len(need_processing)} tests")

        try:
            builder = ColdBuilder(vuln_id)
            builder.build(dev_patch)

            qjs_binary = builder.build_path / "qjs"
            if not qjs_binary.exists():
                qjs_binary = builder.build_path / "build" / "qjs"
            if not qjs_binary.exists():
                logger.error(f"[{vuln_id}] qjs binary not found")
                return

            def validate_fn(gen_file: Path):
                try:
                    env = os.environ | builder.replay_env
                    env["TERM"] = "xterm"
                    result = subprocess.run(
                        [str(qjs_binary), str(gen_file)],
                        capture_output=True,
                        timeout=60,
                        cwd=str(builder.build_path),
                        env=env
                    )
                    if result.returncode == 0:
                        return True, "", ""
                    stderr = result.stderr.decode(errors='replace')[:4000] if result.stderr else ""
                    return False, "runtime", stderr or f"Exit code {result.returncode}"
                except subprocess.TimeoutExpired:
                    return False, "timeout", "Timeout"

            for gen_num in need_processing:
                gen_file = case_dir / f"generated_{gen_num}.js"
                logger.info(f"[{vuln_id}] gen{gen_num}: Processing...")

                _, _, ok, msg = generate_test(case_dir, gen_num, validate_fn=validate_fn)

                if ok:
                    logger.info(f"[✅][{vuln_id}] gen{gen_num}: VALID")
                    valid_gen_files.append((gen_num, gen_file))
                    (output_dir / f"dev:gen{gen_num}.valid").touch()
                else:
                    logger.warning(f"[{vuln_id}] gen{gen_num}: FAILED - {msg}")

        except (BuilderProcessError, BuilderTimeoutError) as e:
            logger.error(f"[🚨][{vuln_id}] Failed to build with developer patch: {e}")
            return

    if not valid_gen_files:
        logger.warning(f"[{vuln_id}] No valid generated tests found")
        return

    # Load AI-generated patches
    patches: List[tuple] = []
    for agent in ["patchagent", "san2patch", "mswe-agent"]:
        agent_dir = ARCHIVE / agent
        if not agent_dir.is_dir():
            continue
        for post_file in agent_dir.glob(f"{vuln_id}:*:post.json"):
            try:
                data = json.loads(post_file.read_text())
                patch = data.get("patch")
                if patch:
                    parts = post_file.stem.replace(":post", "").split(":")
                    source = f"{agent}:{parts[1]}:{parts[2]}" if len(parts) >= 3 else f"{agent}:{post_file.stem}"
                    patches.append((source, patch))
            except Exception as e:
                logger.warning(f"Failed to load {post_file}: {e}")

    if not patches:
        logger.info(f"[{vuln_id}] No AI patches found")
        return

    logger.info(f"[{vuln_id}] Testing {len(valid_gen_files)} valid tests x {len(patches)} AI patches")

    total_patches = len(patches)
    skipped_count = 0

    for patch_idx, (patch_source, patch) in enumerate(patches, 1):
        gen_files_to_test = []
        for gen_num, gen_file in valid_gen_files:
            result_file = output_dir / f"{patch_source}:gen{gen_num}.json"
            build_err_file = output_dir / f"{patch_source}:gen{gen_num}{SUFFIX_BUILD_ERR}.json"

            if result_file.exists() or build_err_file.exists():
                skipped_count += 1
                continue
            gen_files_to_test.append((gen_num, gen_file))

        if not gen_files_to_test:
            continue

        logger.info(f"[{vuln_id}] [{patch_idx}/{total_patches}] Processing {patch_source} ({len(gen_files_to_test)} tests)")

        try:
            builder = ColdBuilder(vuln_id)

            try:
                builder.build(patch)
            except (BuilderProcessError, BuilderTimeoutError) as e:
                logger.warning(f"[{vuln_id}] [{patch_idx}/{total_patches}] {patch_source}: BUILD_ERR")
                for gen_num, _ in gen_files_to_test:
                    err_file = output_dir / f"{patch_source}:gen{gen_num}{SUFFIX_BUILD_ERR}.json"
                    err_file.write_text(json.dumps({"patch": patch, "result": False, "error": str(e)}))
                continue

            qjs_binary = builder.build_path / "qjs"
            if not qjs_binary.exists():
                qjs_binary = builder.build_path / "build" / "qjs"
            if not qjs_binary.exists():
                logger.warning(f"[{vuln_id}] [{patch_idx}/{total_patches}] {patch_source}: No qjs binary")
                continue

            for gen_num, gen_file in gen_files_to_test:
                result_file = output_dir / f"{patch_source}:gen{gen_num}.json"

                try:
                    env = os.environ | builder.replay_env
                    env["TERM"] = "xterm"
                    run_result = subprocess.run(
                        [str(qjs_binary), str(gen_file)],
                        capture_output=True,
                        timeout=60,
                        cwd=str(builder.build_path),
                        env=env
                    )

                    if run_result.returncode == 0:
                        result_file.write_text(json.dumps({"patch": patch, "result": True}))
                        logger.info(f"[✅][{vuln_id}] [{patch_idx}/{total_patches}] {patch_source} gen{gen_num}: PASS")
                    else:
                        stderr_msg = run_result.stderr.decode(errors='replace') if run_result.stderr else ""
                        result_file.write_text(json.dumps({
                            "patch": patch,
                            "result": False,
                            "error": stderr_msg[:4000] or f"Exit code {run_result.returncode}"
                        }))
                        logger.info(f"[❌][{vuln_id}] [{patch_idx}/{total_patches}] {patch_source} gen{gen_num}: FAIL")

                except subprocess.TimeoutExpired:
                    result_file.write_text(json.dumps({"patch": patch, "result": False, "error": "Timeout"}))
                    logger.warning(f"[{vuln_id}] [{patch_idx}/{total_patches}] {patch_source} gen{gen_num}: TIMEOUT")

        except Exception as e:
            logger.error(f"[🚨][{vuln_id}] [{patch_idx}/{total_patches}] {patch_source}: {e}")

    if skipped_count > 0:
        logger.info(f"[{vuln_id}] Skipped {skipped_count} already completed tests")


def gentest_internal_v8(id_path: Path) -> None:
    """Test generated.js files against patches for V8 vulnerability."""
    import subprocess
    import re
    from cold.generator_v8 import generate_test, extract_v8_flags

    vuln_id = id_path.name
    case_dir = GENTEST_V8 / vuln_id

    if not case_dir.exists() or not (case_dir / "poc.js").exists():
        logger.warning(f"[{vuln_id}] No case directory or poc.js found in {case_dir}")
        return

    dev_patch_file = id_path / "patch.diff"
    if not dev_patch_file.is_file():
        logger.warning(f"[{vuln_id}] No developer patch (patch.diff) found")
        return
    dev_patch = dev_patch_file.read_text()

    output_dir = ARCHIVE / "gentest" / vuln_id
    output_dir.mkdir(parents=True, exist_ok=True)

    need_processing: List[int] = []
    valid_gen_files: List[tuple] = []

    for gen_num in [1, 2, 3]:
        gen_file = case_dir / f"generated_{gen_num}.js"
        valid_marker = output_dir / f"dev:gen{gen_num}.valid"

        if valid_marker.exists() and gen_file.exists():
            logger.info(f"[{vuln_id}] gen{gen_num}: SKIP (already validated)")
            valid_gen_files.append((gen_num, gen_file))
        else:
            need_processing.append(gen_num)

    if need_processing:
        logger.info(f"[{vuln_id}] Building V8 and processing {len(need_processing)} tests")

        try:
            builder = ColdBuilder(vuln_id)
            builder.build(dev_patch)

            d8_binary = builder.build_path / "out" / "debug_asan" / "d8"
            if not d8_binary.exists():
                d8_binary = builder.build_path / "d8"
            if not d8_binary.exists():
                logger.error(f"[{vuln_id}] d8 binary not found")
                return

            def validate_fn(gen_file: Path):
                try:
                    content = gen_file.read_text()
                    flags = extract_v8_flags(content)
                    env = os.environ | builder.replay_env
                    env["TERM"] = "xterm"
                    cmd = [str(d8_binary)] + flags + [str(gen_file)]
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        timeout=60,
                        cwd=str(builder.build_path),
                        env=env
                    )
                    if result.returncode == 0:
                        return True, "", ""
                    stderr = result.stderr.decode(errors='replace')[:4000] if result.stderr else ""
                    return False, "runtime", stderr or f"Exit code {result.returncode}"
                except subprocess.TimeoutExpired:
                    return False, "timeout", "Timeout"

            for gen_num in need_processing:
                gen_file = case_dir / f"generated_{gen_num}.js"
                logger.info(f"[{vuln_id}] gen{gen_num}: Processing...")

                _, _, ok, msg = generate_test(case_dir, gen_num, validate_fn=validate_fn)

                if ok:
                    logger.info(f"[✅][{vuln_id}] gen{gen_num}: VALID")
                    valid_gen_files.append((gen_num, gen_file))
                    (output_dir / f"dev:gen{gen_num}.valid").touch()
                else:
                    logger.warning(f"[{vuln_id}] gen{gen_num}: FAILED - {msg}")

        except (BuilderProcessError, BuilderTimeoutError) as e:
            logger.error(f"[🚨][{vuln_id}] Failed to build with developer patch: {e}")
            return

    if not valid_gen_files:
        logger.warning(f"[{vuln_id}] No valid generated tests found")
        return

    # Load AI-generated patches
    patches: List[tuple] = []
    for agent in ["patchagent", "san2patch", "mswe-agent"]:
        agent_dir = ARCHIVE / agent
        if not agent_dir.is_dir():
            continue
        for post_file in agent_dir.glob(f"{vuln_id}:*:post.json"):
            try:
                data = json.loads(post_file.read_text())
                patch = data.get("patch")
                if patch:
                    parts = post_file.stem.replace(":post", "").split(":")
                    source = f"{agent}:{parts[1]}:{parts[2]}" if len(parts) >= 3 else f"{agent}:{post_file.stem}"
                    patches.append((source, patch))
            except Exception as e:
                logger.warning(f"Failed to load {post_file}: {e}")

    if not patches:
        logger.info(f"[{vuln_id}] No AI patches found")
        return

    logger.info(f"[{vuln_id}] Testing {len(valid_gen_files)} valid tests x {len(patches)} AI patches")

    total_patches = len(patches)
    skipped_count = 0

    for patch_idx, (patch_source, patch) in enumerate(patches, 1):
        gen_files_to_test = []
        for gen_num, gen_file in valid_gen_files:
            result_file = output_dir / f"{patch_source}:gen{gen_num}.json"
            build_err_file = output_dir / f"{patch_source}:gen{gen_num}{SUFFIX_BUILD_ERR}.json"

            if result_file.exists() or build_err_file.exists():
                skipped_count += 1
                continue
            gen_files_to_test.append((gen_num, gen_file))

        if not gen_files_to_test:
            continue

        logger.info(f"[{vuln_id}] [{patch_idx}/{total_patches}] Processing {patch_source} ({len(gen_files_to_test)} tests)")

        try:
            builder = ColdBuilder(vuln_id)

            try:
                builder.build(patch)
            except (BuilderProcessError, BuilderTimeoutError) as e:
                logger.warning(f"[{vuln_id}] [{patch_idx}/{total_patches}] {patch_source}: BUILD_ERR")
                for gen_num, _ in gen_files_to_test:
                    err_file = output_dir / f"{patch_source}:gen{gen_num}{SUFFIX_BUILD_ERR}.json"
                    err_file.write_text(json.dumps({"patch": patch, "result": False, "error": str(e)}))
                continue

            d8_binary = builder.build_path / "out" / "debug_asan" / "d8"
            if not d8_binary.exists():
                d8_binary = builder.build_path / "d8"
            if not d8_binary.exists():
                logger.warning(f"[{vuln_id}] [{patch_idx}/{total_patches}] {patch_source}: No d8 binary")
                continue

            for gen_num, gen_file in gen_files_to_test:
                result_file = output_dir / f"{patch_source}:gen{gen_num}.json"

                try:
                    content = gen_file.read_text()
                    flags = extract_v8_flags(content)
                    env = os.environ | builder.replay_env
                    env["TERM"] = "xterm"
                    cmd = [str(d8_binary)] + flags + [str(gen_file)]
                    run_result = subprocess.run(
                        cmd,
                        capture_output=True,
                        timeout=60,
                        cwd=str(builder.build_path),
                        env=env
                    )

                    if run_result.returncode == 0:
                        result_file.write_text(json.dumps({"patch": patch, "result": True}))
                        logger.info(f"[✅][{vuln_id}] [{patch_idx}/{total_patches}] {patch_source} gen{gen_num}: PASS")
                    else:
                        stderr_msg = run_result.stderr.decode(errors='replace') if run_result.stderr else ""
                        result_file.write_text(json.dumps({
                            "patch": patch,
                            "result": False,
                            "error": stderr_msg[:4000] or f"Exit code {run_result.returncode}"
                        }))
                        logger.info(f"[❌][{vuln_id}] [{patch_idx}/{total_patches}] {patch_source} gen{gen_num}: FAIL")

                except subprocess.TimeoutExpired:
                    result_file.write_text(json.dumps({"patch": patch, "result": False, "error": "Timeout"}))
                    logger.warning(f"[{vuln_id}] [{patch_idx}/{total_patches}] {patch_source} gen{gen_num}: TIMEOUT")

        except Exception as e:
            logger.error(f"[🚨][{vuln_id}] [{patch_idx}/{total_patches}] {patch_source}: {e}")

    if skipped_count > 0:
        logger.info(f"[{vuln_id}] Skipped {skipped_count} already completed tests")


def gentest_internal_vim(id_path: Path) -> None:
    """Test generated.vim files against patches for Vim vulnerability."""
    import subprocess
    from cold.generator_vim import generate_test

    vuln_id = id_path.name
    case_dir = GENTEST_VIM / vuln_id

    if not case_dir.exists() or not (case_dir / "poc.vim").exists():
        logger.warning(f"[{vuln_id}] No case directory or poc.vim found in {case_dir}")
        return

    dev_patch_file = id_path / "patch.diff"
    if not dev_patch_file.is_file():
        logger.warning(f"[{vuln_id}] No developer patch (patch.diff) found")
        return
    dev_patch = dev_patch_file.read_text()

    output_dir = ARCHIVE / "gentest" / vuln_id
    output_dir.mkdir(parents=True, exist_ok=True)

    need_processing: List[int] = []
    valid_gen_files: List[tuple] = []

    for gen_num in [1, 2, 3]:
        gen_file = case_dir / f"generated_{gen_num}.vim"
        valid_marker = output_dir / f"dev:gen{gen_num}.valid"

        if valid_marker.exists() and gen_file.exists():
            logger.info(f"[{vuln_id}] gen{gen_num}: SKIP (already validated)")
            valid_gen_files.append((gen_num, gen_file))
        else:
            need_processing.append(gen_num)

    if need_processing:
        logger.info(f"[{vuln_id}] Building Vim and processing {len(need_processing)} tests")

        try:
            builder = ColdBuilder(vuln_id)
            builder.build(dev_patch)

            vim_binary = builder.build_path / "src" / "vim"
            if not vim_binary.exists():
                vim_binary = builder.build_path / "vim"
            if not vim_binary.exists():
                logger.error(f"[{vuln_id}] vim binary not found")
                return

            def validate_fn(gen_file: Path):
                try:
                    env = os.environ | builder.replay_env
                    env["TERM"] = "xterm"
                    # Run vim in Ex mode (-e) and silent mode (-s) with the script
                    cmd = [str(vim_binary), "-e", "-s", "-N", "-u", "NONE", "-S", str(gen_file)]
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        timeout=30,
                        cwd=str(builder.build_path),
                        env=env
                    )
                    if result.returncode == 0:
                        return True, "", ""
                    stderr = result.stderr.decode(errors='replace')[:4000] if result.stderr else ""
                    return False, "runtime", stderr or f"Exit code {result.returncode}"
                except subprocess.TimeoutExpired:
                    return False, "timeout", "Timeout"

            for gen_num in need_processing:
                gen_file = case_dir / f"generated_{gen_num}.vim"
                logger.info(f"[{vuln_id}] gen{gen_num}: Processing...")

                _, _, ok, msg = generate_test(case_dir, gen_num, validate_fn=validate_fn)

                if ok:
                    logger.info(f"[✅][{vuln_id}] gen{gen_num}: VALID")
                    valid_gen_files.append((gen_num, gen_file))
                    (output_dir / f"dev:gen{gen_num}.valid").touch()
                else:
                    logger.warning(f"[{vuln_id}] gen{gen_num}: FAILED - {msg}")

        except (BuilderProcessError, BuilderTimeoutError) as e:
            logger.error(f"[🚨][{vuln_id}] Failed to build with developer patch: {e}")
            return

    if not valid_gen_files:
        logger.warning(f"[{vuln_id}] No valid generated tests found")
        return

    # Load AI-generated patches
    patches: List[tuple] = []
    for agent in ["patchagent", "san2patch", "mswe-agent"]:
        agent_dir = ARCHIVE / agent
        if not agent_dir.is_dir():
            continue
        for post_file in agent_dir.glob(f"{vuln_id}:*:post.json"):
            try:
                data = json.loads(post_file.read_text())
                patch = data.get("patch")
                if patch:
                    parts = post_file.stem.replace(":post", "").split(":")
                    source = f"{agent}:{parts[1]}:{parts[2]}" if len(parts) >= 3 else f"{agent}:{post_file.stem}"
                    patches.append((source, patch))
            except Exception as e:
                logger.warning(f"Failed to load {post_file}: {e}")

    if not patches:
        logger.info(f"[{vuln_id}] No AI patches found")
        return

    logger.info(f"[{vuln_id}] Testing {len(valid_gen_files)} valid tests x {len(patches)} AI patches")

    total_patches = len(patches)
    skipped_count = 0

    for patch_idx, (patch_source, patch) in enumerate(patches, 1):
        gen_files_to_test = []
        for gen_num, gen_file in valid_gen_files:
            result_file = output_dir / f"{patch_source}:gen{gen_num}.json"
            build_err_file = output_dir / f"{patch_source}:gen{gen_num}{SUFFIX_BUILD_ERR}.json"

            if result_file.exists() or build_err_file.exists():
                skipped_count += 1
                continue
            gen_files_to_test.append((gen_num, gen_file))

        if not gen_files_to_test:
            continue

        logger.info(f"[{vuln_id}] [{patch_idx}/{total_patches}] Processing {patch_source} ({len(gen_files_to_test)} tests)")

        try:
            builder = ColdBuilder(vuln_id)

            try:
                builder.build(patch)
            except (BuilderProcessError, BuilderTimeoutError) as e:
                logger.warning(f"[{vuln_id}] [{patch_idx}/{total_patches}] {patch_source}: BUILD_ERR")
                for gen_num, _ in gen_files_to_test:
                    err_file = output_dir / f"{patch_source}:gen{gen_num}{SUFFIX_BUILD_ERR}.json"
                    err_file.write_text(json.dumps({"patch": patch, "result": False, "error": str(e)}))
                continue

            vim_binary = builder.build_path / "src" / "vim"
            if not vim_binary.exists():
                vim_binary = builder.build_path / "vim"
            if not vim_binary.exists():
                logger.warning(f"[{vuln_id}] [{patch_idx}/{total_patches}] {patch_source}: No vim binary")
                continue

            for gen_num, gen_file in gen_files_to_test:
                result_file = output_dir / f"{patch_source}:gen{gen_num}.json"

                try:
                    env = os.environ | builder.replay_env
                    env["TERM"] = "xterm"
                    cmd = [str(vim_binary), "-e", "-s", "-N", "-u", "NONE", "-S", str(gen_file)]
                    run_result = subprocess.run(
                        cmd,
                        capture_output=True,
                        timeout=30,
                        cwd=str(builder.build_path),
                        env=env
                    )

                    if run_result.returncode == 0:
                        result_file.write_text(json.dumps({"patch": patch, "result": True}))
                        logger.info(f"[✅][{vuln_id}] [{patch_idx}/{total_patches}] {patch_source} gen{gen_num}: PASS")
                    else:
                        stderr_msg = run_result.stderr.decode(errors='replace') if run_result.stderr else ""
                        result_file.write_text(json.dumps({
                            "patch": patch,
                            "result": False,
                            "error": stderr_msg[:4000] or f"Exit code {run_result.returncode}"
                        }))
                        logger.info(f"[❌][{vuln_id}] [{patch_idx}/{total_patches}] {patch_source} gen{gen_num}: FAIL")

                except subprocess.TimeoutExpired:
                    result_file.write_text(json.dumps({"patch": patch, "result": False, "error": "Timeout"}))
                    logger.warning(f"[{vuln_id}] [{patch_idx}/{total_patches}] {patch_source} gen{gen_num}: TIMEOUT")

        except Exception as e:
            logger.error(f"[🚨][{vuln_id}] [{patch_idx}/{total_patches}] {patch_source}: {e}")

    if skipped_count > 0:
        logger.info(f"[{vuln_id}] Skipped {skipped_count} already completed tests")


# List of C/C++ projects that use the compile-based gentest
CC_PROJECTS = {"icu", "hdf5", "pcapplusplus", "libtiff"}
# List of Python projects that use simple python execution
PYTHON_PROJECTS = {"cpython"}
# List of script-based projects (Ruby, JavaScript, Vimscript)
RUBY_PROJECTS = {"mruby"}
QUICKJS_PROJECTS = {"quickjs"}
V8_PROJECTS = {"v8"}
VIM_PROJECTS = {"vim"}


def gentest_internal(id_path: Path) -> None:
    """Dispatch gentest to appropriate handler based on project type.

    - cpython: Uses gentest_internal_cpython (python generated_N.py)
    - mruby: Uses gentest_internal_mruby (mruby generated_N.rb)
    - quickjs: Uses gentest_internal_quickjs (qjs generated_N.js)
    - v8: Uses gentest_internal_v8 (d8 generated_N.js)
    - vim: Uses gentest_internal_vim (vim -e -s -S generated_N.vim)
    - C/C++ projects: Uses gentest_internal_cc (compile and run)
    """
    config_file = id_path / "config.yaml"
    if not config_file.is_file():
        logger.warning(f"[{id_path.name}] No config.yaml found")
        return

    config_data = yaml.safe_load(config_file.read_text())
    project = config_data.get("project", "")

    if project in PYTHON_PROJECTS:
        gentest_internal_cpython(id_path)
    elif project in RUBY_PROJECTS:
        gentest_internal_mruby(id_path)
    elif project in QUICKJS_PROJECTS:
        gentest_internal_quickjs(id_path)
    elif project in V8_PROJECTS:
        gentest_internal_v8(id_path)
    elif project in VIM_PROJECTS:
        gentest_internal_vim(id_path)
    elif project in CC_PROJECTS:
        gentest_internal_cc(id_path)
    else:
        logger.warning(f"[{id_path.name}] Unknown project type: {project}")


def gentest() -> None:
    """Run generated test cases against patches."""
    logger.info("[🔍] Cold Patch CLI Starting (gentest)")

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_proc) as executor:
        future_to_id = {}
        for id_path in SOURCE.iterdir():
            config = id_path / "config.yaml"
            if config.is_file() and (args.id is None or id_path.name == args.id):
                future = executor.submit(gentest_internal, id_path)
                future_to_id[future] = id_path.name

        for future in concurrent.futures.as_completed(future_to_id):
            id = future_to_id[future]
            try:
                future.result()
            except Exception as e:
                logger.error(f"[🚨][{id}] {e}")


if __name__ == "__main__":
    match ACTION:
        case "check":
            check()
        case "double-check":
            double_check()
        case "patchagent":
            patchagent()
        case "san2patch":
            san2patch()
        case "swe-agent":
            swe_agent()
        case "gentest":
            gentest()
        case _:
            raise CLIException(f"Unknown action: {ACTION}")
