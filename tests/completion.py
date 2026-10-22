"""Run a TRUSTED pytest suite with fresh, complete execution evidence.

This is a completion gate, not a sandbox. Tests must invoke candidate code in a
separate restricted process. Never import candidate code into this worker.
freeze executes trusted collection; run executes trusted tests. Neither belongs
in a model's writable environment. pytest is required in this interpreter.
"""
import argparse
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import tempfile
from pathlib import PurePosixPath


class GateError(ValueError):
    """A bounded public error; never include arbitrary exception text."""
    def __init__(self, category, detail):
        super().__init__(detail)
        self.category = category
        self.detail = detail[:240]


def fail(category, detail):
    raise GateError(category, detail)


def protected_skill_root():
    """Protect an installed skill without treating standalone /tests as /."""
    entry = Path(__file__).resolve()
    root = entry.parent.parent
    return root if entry.parent.name == "scripts" and (root / "SKILL.md").is_file() else None


def no_links(path):
    path = Path(os.path.abspath(path))
    for item in (path, *path.parents):
        if item.is_symlink() or (hasattr(item, "is_junction") and item.is_junction()):
            fail("linked_path_rejected", "A required trusted path is a symlink or junction.")
    return path


def read_json(path, exact_numbers=False):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                fail("invalid_json", "JSON contains a duplicate object key.")
            result[key] = value
        return result
    path = no_links(path)
    if not path.is_file() or path.stat().st_size > 8_000_000:
        fail("missing_or_oversized_json", "A required JSON file is missing or exceeds the 8 MB limit.")
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=pairs,
                      parse_float=Decimal if exact_numbers else float)


def atomic_write(path, value):
    path = no_links(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(value)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def suite_digest(suite, expected):
    digest = hashlib.sha256()
    count = 0
    for path in sorted(suite.rglob("*"), key=lambda p: p.relative_to(suite).as_posix()):
        no_links(path)
        if path.suffix in (".pyc", ".pyo") or any(p in ("__pycache__", ".pytest_cache") for p in path.relative_to(suite).parts):
            # -B prevents writing bytecode, not loading old timestamp caches.
            # Never silently omit executable bytes from the frozen suite.
            fail("suite_contains_cache_artifacts", "Legacy manifests reject bytecode and pytest caches.")
        if path == expected:
            continue
        if not path.is_file():
            continue
        count += 1
        name = path.relative_to(suite).as_posix().encode()
        digest.update(len(name).to_bytes(8, "big") + name)
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    if count == 0:
        raise ValueError("empty trusted suite")
    return digest.hexdigest()


BUILD_METADATA = frozenset({".dockerignore", "Dockerfile", "docker-compose.yaml", "docker-compose.yml"})
CACHE_DIRECTORIES = frozenset({"__pycache__", ".pytest_cache", ".git"})


def inventory_path(value):
    if (not isinstance(value, str) or not value or "\\" in value or ":" in value
            or any(ord(char) < 32 for char in value)):
        fail("invalid_suite_inventory", "Inventory paths must be canonical relative POSIX file paths.")
    path = PurePosixPath(value)
    if (not path.parts or path.is_absolute() or str(path) != value
            or any(part in (".", "..") for part in path.parts)):
        fail("invalid_suite_inventory", "Inventory paths must be canonical relative POSIX file paths.")
    if (path.name == "conftest.py" or path.suffix in (".pyc", ".pyo")
            or any(part in CACHE_DIRECTORIES for part in path.parts)):
        fail("unsafe_suite_inventory", "Conftest files, bytecode, and cache directories cannot be staged.")
    return value


def validate_inventory(value):
    if not isinstance(value, list) or not value:
        fail("invalid_suite_inventory", "The manifest must declare a nonempty trusted file inventory.")
    names = []
    for item in value:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            fail("invalid_suite_inventory", "Each inventory entry requires only path and sha256.")
        names.append(inventory_path(item["path"]))
        sha = item["sha256"]
        if (not isinstance(sha, str) or len(sha) != 64
                or any(char not in "0123456789abcdef" for char in sha)):
            fail("invalid_suite_inventory", "Inventory hashes must be lowercase SHA-256 values.")
    if len({name.casefold() for name in names}) != len(names) or names != sorted(names):
        fail("invalid_suite_inventory", "Inventory paths must be sorted and unique across platforms.")
    if not any(PurePosixPath(name).suffix == ".py" for name in names):
        fail("invalid_suite_inventory", "The trusted inventory must include Python test source.")
    return value


def inventory_digest(inventory):
    digest = hashlib.sha256()
    for item in validate_inventory(inventory):
        name = item["path"].encode()
        digest.update(len(name).to_bytes(8, "big") + name)
        digest.update(bytes.fromhex(item["sha256"]))
    return digest.hexdigest()


def build_inventory(suite, expected_path, selected=None):
    if selected is None:
        names = []
        for path in suite.rglob("*"):
            relative = path.relative_to(suite)
            if (path == expected_path or any(part in CACHE_DIRECTORIES for part in relative.parts)
                    or path.name in BUILD_METADATA or path.name == "conftest.py"
                    or path.suffix in (".pyc", ".pyo")):
                continue
            no_links(path)
            if path.is_file():
                names.append(relative.as_posix())
    else:
        if not isinstance(selected, list) or not selected:
            fail("invalid_suite_inventory", "--suite-files must contain a nonempty JSON list of relative file paths.")
        names = [inventory_path(name) for name in selected]
    runner = Path(__file__).resolve()
    if runner.is_relative_to(suite) and runner.relative_to(suite).as_posix() not in names:
        fail("runner_not_in_inventory", "The gate entry script inside the suite must be declared in its inventory.")
    inventory = []
    for name in sorted(names):
        path = no_links(suite / name)
        if path == expected_path:
            fail("invalid_suite_inventory", "The generated manifest cannot be a declared suite dependency.")
        if not path.is_file():
            fail("declared_suite_file_missing", "A declared trusted suite file is missing: " + name[:160])
        inventory.append(dict(path=name, sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    return validate_inventory(inventory)


def verify_inventory(suite, inventory):
    for item in validate_inventory(inventory):
        path = no_links(suite / item["path"])
        if not path.is_file():
            fail("declared_suite_file_missing", "A declared trusted suite file is missing: " + item["path"][:160])
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            fail("declared_suite_file_changed", "A declared trusted suite file changed: " + item["path"][:160])
    return inventory_digest(inventory)


def manifest_binding(expected):
    payload = {key: value for key, value in expected.items() if key != "manifest_sha256"}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def stage_suite(suite, directory, inventory, runner_sha256):
    staging = directory / "trusted-suite"
    staging.mkdir(mode=0o700)
    for item in inventory:
        source = no_links(suite / item["path"])
        if not source.is_file():
            fail("declared_suite_file_missing", "A declared trusted suite file is missing: " + item["path"][:160])
        contents = source.read_bytes()
        if hashlib.sha256(contents).hexdigest() != item["sha256"]:
            fail("declared_suite_file_changed", "A declared trusted suite file changed: " + item["path"][:160])
        target = staging / item["path"]
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        target.write_bytes(contents)
    runner_bytes = no_links(Path(__file__).resolve()).read_bytes()
    if hashlib.sha256(runner_bytes).hexdigest() != runner_sha256:
        fail("trusted_runner_changed", "The gate entry script does not match the frozen runner hash.")
    staged_runner = directory / "trusted-runner.py"
    staged_runner.write_bytes(runner_bytes)
    verify_inventory(staging, inventory)
    return staging, staged_runner


def nodeids(value):
    return (isinstance(value, list) and bool(value)
            and all(isinstance(v, str) and bool(v.strip()) for v in value)
            and len(set(value)) == len(value))


def validate_scoring(value, collected):
    """Freeze one weighted item per test and canonical integer weight ratios.

    The definition is trusted author input, never candidate-produced evidence.
    Decimal JSON numbers are read before conversion so normalization does not
    lose a small item's weight next to a much larger one.
    Prerequisites are empty unless explicitly supplied by the trusted author.
    """
    if (not isinstance(value, dict) or type(value.get("schema_version")) is not int
            or value["schema_version"] != 1
            or set(value) not in ({"schema_version", "items"},
                                  {"schema_version", "prerequisites", "items"})
            or not nodeids(collected)):
        raise ValueError("invalid scoring definition")
    prerequisites = value.get("prerequisites", [])
    items = value["items"]
    if (not isinstance(prerequisites, list)
            or (prerequisites and not nodeids(prerequisites))
            or not isinstance(items, list) or not items):
        raise ValueError("invalid scoring items")
    assigned, identifiers, weights, normalized = list(prerequisites), set(), [], []
    for item in items:
        if (not isinstance(item, dict) or set(item) != {"id", "weight", "nodeids", "rationale"}
                or not isinstance(item["id"], str) or not item["id"].strip()
                or item["id"] in identifiers or not nodeids(item["nodeids"])
                or not isinstance(item["rationale"], str) or not item["rationale"].strip()):
            raise ValueError("invalid or duplicate scoring item")
        if len(item["nodeids"]) != 1:
            raise ValueError("each scoring item must name exactly one collected test")
        weight = item["weight"]
        if (type(weight) not in (int, float, Decimal)
                or (isinstance(weight, Decimal) and not weight.is_finite())
                or (isinstance(weight, float) and not math.isfinite(weight)) or weight <= 0):
            raise ValueError("weights must be positive finite numbers")
        weight = Fraction(Decimal(str(weight)))
        identifiers.add(item["id"])
        weights.append(weight)
        assigned.extend(item["nodeids"])
        normalized.append(dict(item))
    if len(set(weights)) < 2:
        raise ValueError("weighted scoring requires at least two distinct weights")
    if len(set(assigned)) != len(assigned) or set(assigned) != set(collected):
        raise ValueError("every collected test must have exactly one scoring item or explicit prerequisite")
    denominator = math.lcm(*(weight.denominator for weight in weights))
    integers = [weight.numerator * (denominator // weight.denominator) for weight in weights]
    common = math.gcd(*integers)
    for item, weight in zip(normalized, integers):
        item["weight"] = weight // common
    return dict(schema_version=1, prerequisites=prerequisites.copy(), items=normalized)


def validate_completion(report, expected, run_id, digest, returncode):
    """Validate only structural completion; trust must come from isolation."""
    reasons = []
    if (not isinstance(expected, dict) or type(expected.get("schema_version")) is not int
            or expected["schema_version"] not in (1, 2) or not nodeids(expected.get("nodeids"))):
        return ["invalid_expected_manifest"]
    if expected.get("suite_sha256") != digest:
        reasons.append("suite_not_frozen_version")
    if returncode != 0:
        reasons.append("worker_nonzero_or_timeout")
    if not isinstance(report, dict):
        return reasons + ["missing_completion_report"]
    if report.get("schema_version") != 1 or report.get("run_id") != run_id or report.get("suite_sha256") != digest:
        reasons.append("report_identity_mismatch")
    if report.get("finished") is not True or type(report.get("exitstatus")) is not int or report["exitstatus"] != 0:
        reasons.append("session_not_successfully_finished")
    if report.get("collection_errors") != []:
        reasons.append("collection_errors_or_missing_evidence")
    collected = report.get("collected")
    if not nodeids(collected) or set(collected) != set(expected["nodeids"]):
        reasons.append("collected_set_mismatch")
    records = report.get("outcomes")
    seen = set()
    if not isinstance(records, list):
        return reasons + ["missing_phase_reports"]
    for record in records:
        if not isinstance(record, dict):
            reasons.append("invalid_phase_report")
            continue
        key = (record.get("nodeid"), record.get("when"))
        if not all(isinstance(v, str) for v in key):
            reasons.append("invalid_phase_identity")
            continue
        if key in seen:
            reasons.append("duplicate_phase_report")
        seen.add(key)
        if record.get("outcome") != "passed" or record.get("wasxfail") is not False:
            reasons.append("failed_skipped_or_xfail_phase")
    required = {(case, stage) for case in expected["nodeids"] for stage in ("setup", "call", "teardown")}
    if seen != required:
        reasons.append("executed_phase_set_mismatch")
    return sorted(set(reasons))


def validate_weighted_completion(report, expected, run_id, digest, returncode):
    """Require a complete trustworthy run, allowing ordinary call failures.

    Failed setup/teardown, skips and xfails invalidate the entire run: these
    cannot establish that the frozen behavioral checks actually executed.
    This separate protocol deliberately leaves the binary gate unchanged.
    """
    reasons = []
    if (not isinstance(expected, dict) or type(expected.get("schema_version")) is not int
            or expected["schema_version"] not in (1, 2) or not nodeids(expected.get("nodeids"))):
        return ["invalid_expected_manifest"]
    try:
        validate_scoring(expected.get("scoring"), expected["nodeids"])
    except (ValueError, TypeError, OverflowError):
        return ["invalid_scoring_definition"]
    if expected.get("suite_sha256") != digest:
        reasons.append("suite_not_frozen_version")
    if type(returncode) is not int or returncode not in (0, 1):
        reasons.append("worker_nonzero_or_timeout")
    if not isinstance(report, dict):
        return reasons + ["missing_completion_report"]
    if report.get("schema_version") != 1 or report.get("run_id") != run_id or report.get("suite_sha256") != digest:
        reasons.append("report_identity_mismatch")
    if (report.get("finished") is not True or type(report.get("exitstatus")) is not int
            or report["exitstatus"] not in (0, 1) or report["exitstatus"] != returncode):
        reasons.append("session_not_successfully_finished")
    if report.get("collection_errors") != []:
        reasons.append("collection_errors_or_missing_evidence")
    collected = report.get("collected")
    if not nodeids(collected) or set(collected) != set(expected["nodeids"]):
        reasons.append("collected_set_mismatch")
    records, seen, failed_calls = report.get("outcomes"), set(), 0
    if not isinstance(records, list):
        return sorted(set(reasons + ["missing_phase_reports"]))
    for record in records:
        if not isinstance(record, dict):
            reasons.append("invalid_phase_report")
            continue
        key = (record.get("nodeid"), record.get("when"))
        if not all(isinstance(part, str) for part in key):
            reasons.append("invalid_phase_identity")
            continue
        if key in seen:
            reasons.append("duplicate_phase_report")
        seen.add(key)
        outcome = record.get("outcome")
        if record.get("wasxfail") is not False or outcome not in ("passed", "failed"):
            reasons.append("skipped_xfail_or_invalid_phase")
        if key[1] != "call" and outcome != "passed":
            reasons.append("setup_or_teardown_not_passed")
        if key[1] == "call" and outcome == "failed":
            failed_calls += 1
            if record.get("failure_kind") != "assertion":
                reasons.append("non_assertion_call_failure")
    required = {(case, stage) for case in expected["nodeids"] for stage in ("setup", "call", "teardown")}
    if seen != required:
        reasons.append("executed_phase_set_mismatch")
    if (returncode == 1 and not failed_calls) or (returncode == 0 and failed_calls):
        reasons.append("exitstatus_outcome_mismatch")
    return sorted(set(reasons))


def score_execution(expected, report, accepted):
    """Return exact score evidence plus a safe numeric reward representation."""
    weighted = isinstance(expected, dict) and "scoring" in expected
    result = dict(scoring_mode="weighted" if weighted else "binary", score=0,
                  score_fraction="0/1", full_success=False,
                  prerequisites_passed=None, items=[])
    if not weighted:
        if accepted:
            result.update(score=1, score_fraction="1/1", full_success=True)
        return result
    try:
        scoring = validate_scoring(expected["scoring"], expected["nodeids"])
    except (ValueError, TypeError, KeyError, OverflowError):
        return result
    # Do not derive any earned credit from an incomplete or rejected report.
    passed = {record["nodeid"] for record in report["outcomes"]
              if record["when"] == "call" and record["outcome"] == "passed"} if accepted else set()
    prerequisites_passed = accepted and all(case in passed for case in scoring["prerequisites"])
    earned, total = 0, sum(item["weight"] for item in scoring["items"])
    for item in scoring["items"]:
        item_passed = accepted and item["nodeids"][0] in passed
        credit = item["weight"] if prerequisites_passed and item_passed else 0
        earned += credit
        result["items"].append(dict(item, passed=item_passed, earned_weight=credit))
    exact = Fraction(earned, total)
    full_success = prerequisites_passed and all(item["passed"] for item in result["items"])
    numeric = float(exact)
    if exact < 1 and numeric == 1:
        # A tiny failed item's weight must never round to a full reward, even
        # when the reward consumer parses this text as an IEEE-754 float.
        numeric = math.nextafter(1.0, 0.0)
    result.update(score=1 if full_success else numeric,
                  score_fraction=f"{exact.numerator}/{exact.denominator}",
                  prerequisites_passed=prerequisites_passed, full_success=full_success)
    return result


class CompletionPlugin:
    def __init__(self, run_id, digest):
        self.failures = {}
        self.data = dict(schema_version=1, run_id=run_id, suite_sha256=digest,
                         collected=[], outcomes=[], collection_errors=[], finished=False, exitstatus=None)

    def pytest_collection_finish(self, session):
        self.data["collected"] = [item.nodeid for item in session.items]

    def pytest_collectreport(self, report):
        if report.failed:
            self.data["collection_errors"].append(report.nodeid)

    def pytest_runtest_logreport(self, report):
        record = dict(nodeid=report.nodeid, when=report.when,
                      outcome=report.outcome, wasxfail=hasattr(report, "wasxfail"))
        if report.failed:
            record["failure_kind"] = self.failures.get((report.nodeid, report.when), "pytest_failure")
        self.data["outcomes"].append(record)

    def pytest_runtest_makereport(self, item, call):
        # This hook runs before pytest's first-result report producer. The
        # exception comes from the trusted pytest call, never parsed stdout.
        if call.excinfo is not None:
            self.failures[(item.nodeid, call.when)] = (
                "assertion" if isinstance(call.excinfo.value, AssertionError) else "exception")

    def pytest_sessionfinish(self, session, exitstatus):
        self.data["finished"] = True
        self.data["exitstatus"] = int(exitstatus)


def worker(suite, directory, run_id, digest, collect):
    try:
        import pytest
    except ModuleNotFoundError as exc:
        category = "pytest_dependency_missing" if exc.name == "pytest" else "pytest_dependency_broken"
        atomic_write(directory / "worker-error.json", json.dumps(dict(category=category,
                     detail="The isolated worker interpreter cannot import the trusted pytest installation.")) + "\n")
        return 3
    pytest.hookimpl(tryfirst=True)(CompletionPlugin.pytest_runtest_makereport)
    plugin = CompletionPlugin(run_id, digest)
    arguments = [str(suite), "--rootdir", str(suite), "-c", str(directory / "pytest.ini"),
                 "--noconftest", "--import-mode=importlib", "-p", "no:cacheprovider", "-q"]
    if collect:
        arguments.append("--collect-only")
    code = int(pytest.main(arguments, plugins=[plugin]))
    atomic_write(directory / "completion.json", json.dumps(plugin.data, allow_nan=False) + "\n")
    return code


def launch(suite, directory, run_id, digest, timeout, collect=False, runner=None):
    # Credentials and user-controlled Python/pytest settings are not inherited.
    env = {k: v for k, v in os.environ.items() if k.upper() in {
        "PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "LANG", "LC_ALL", "TZ"}}
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    (directory / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    command = [sys.executable, "-I", "-B", str(runner or Path(__file__).resolve()), "_worker",
               str(suite), str(directory), run_id, digest, "collect" if collect else "run"]
    with (directory / "pytest-output.txt").open("wb") as log:
        proc = subprocess.Popen(command, cwd=directory, env=env, stdin=subprocess.DEVNULL,
                                stdout=log, stderr=subprocess.STDOUT, start_new_session=os.name == "posix")
        def stop():
            if os.name == "posix":
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            elif proc.poll() is None:
                proc.kill()  # Windows smoke tests only; no descendant-isolation claim.
            proc.wait()
        try:
            return proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            stop()
            return None
        except BaseException:
            stop()
            raise


def validate_manifest(expected):
    if (not isinstance(expected, dict) or type(expected.get("schema_version")) is not int
            or expected["schema_version"] not in (1, 2) or not nodeids(expected.get("nodeids"))):
        fail("invalid_expected_manifest", "The expected manifest has an unsupported schema or invalid nodeids.")
    if "scoring" in expected:
        try:
            canonical = validate_scoring(expected["scoring"], expected["nodeids"])
        except (ValueError, TypeError, OverflowError):
            fail("invalid_scoring_definition", "Frozen scoring must cover each test once, use one nodeid per item and positive unequal weights.")
        if expected["scoring"] != canonical:
            fail("invalid_scoring_definition", "Frozen scoring weights must use their canonical integer ratios.")
    if expected["schema_version"] == 2:
        required = {"schema_version", "suite_sha256", "suite_files", "runner_sha256", "nodeids", "manifest_sha256"}
        if set(expected) not in (required, required | {"scoring"}):
            fail("invalid_expected_manifest", "The inventory manifest has missing or unknown fields.")
        if expected["manifest_sha256"] != manifest_binding(expected):
            fail("manifest_binding_mismatch", "The frozen inventory, nodeids, scoring, or runner binding changed.")
        if expected["suite_sha256"] != inventory_digest(expected["suite_files"]):
            fail("suite_inventory_digest_mismatch", "The frozen suite digest does not match its declared file inventory.")
        if expected["runner_sha256"] != hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest():
            fail("trusted_runner_changed", "The gate entry script does not match the frozen runner hash.")
    return expected


def _input_json(path, category, exact_numbers=False):
    try:
        return read_json(path, exact_numbers)
    except (OSError, ValueError):
        fail(category, "The required author JSON is missing, malformed, linked, or oversized.")


def _run_gate(suite, expected_path, output, timeout, collect=False, weights=None,
              suite_files=None, manifest_version=2):
    # Establish a safe output location first, then clear the score even if the
    # suite, manifest or timeout subsequently turns out to be invalid.
    output = no_links(output)
    suite, expected_path = (Path(os.path.abspath(p)) for p in (suite, expected_path))
    skill = protected_skill_root()
    if (output.is_relative_to(suite) or (skill is not None and output.is_relative_to(skill))
            or expected_path.is_relative_to(output)):
        fail("output_not_isolated", "Run output must be outside the trusted suite, manifest, and installed skill.")
    if collect and (expected_path.exists() or (skill is not None and expected_path.is_relative_to(skill))):
        fail("manifest_destination_not_new", "Freeze requires a new manifest path outside the installed skill.")
    output.mkdir(parents=True, exist_ok=True)
    reward = output / "reward.txt"
    no_links(reward)
    if not collect:
        atomic_write(reward, "0\n")  # In this explicitly selected run output, never reuse an old score.
    run_id = secrets.token_hex(24)
    directory = output / ("completion-" + run_id)
    directory.mkdir(mode=0o700)
    reasons, errors, code, report = [], [], None, None
    digest = None
    expected = None
    inventory, runner_hash, execution_suite = None, None, suite
    runner = None
    try:
        suite, expected_path = no_links(suite), no_links(expected_path)
        if not suite.is_dir():
            fail("trusted_suite_missing", "The trusted suite directory does not exist.")
        if not math.isfinite(timeout) or timeout <= 0:
            fail("invalid_timeout", "The worker timeout must be a positive finite number.")
        if not collect and (weights is not None or suite_files is not None):
            fail("run_override_rejected", "Run uses only frozen scoring and inventory; overrides are freeze-only.")
        if type(manifest_version) is not int or manifest_version not in (1, 2):
            fail("invalid_manifest_version", "Only manifest versions 1 and 2 are supported.")
        definition = _input_json(weights, "scoring_json_invalid", True) if weights is not None else None
        if collect:
            if manifest_version == 1 and suite_files is not None:
                fail("invalid_suite_inventory", "Explicit inventories require manifest version 2.")
            if manifest_version == 2:
                selected = _input_json(suite_files, "suite_files_json_invalid") if suite_files is not None else None
                inventory = build_inventory(suite, expected_path, selected)
                digest = inventory_digest(inventory)
                runner_hash = hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest()
            else:
                digest = suite_digest(suite, expected_path)
        else:
            expected = validate_manifest(_input_json(expected_path, "expected_manifest_json_invalid"))
            if expected["schema_version"] == 2:
                inventory, runner_hash = expected["suite_files"], expected["runner_sha256"]
                gate_entry = Path(__file__).resolve()
                if (gate_entry.is_relative_to(suite) and gate_entry.relative_to(suite).as_posix()
                        not in {item["path"] for item in inventory}):
                    fail("runner_not_in_inventory", "The gate entry script inside the suite must be declared in its inventory.")
                digest = verify_inventory(suite, inventory)
            else:
                digest = suite_digest(suite, expected_path)
                if expected.get("suite_sha256") != digest:
                    fail("suite_not_frozen_version", "The legacy manifest does not match the entire current suite.")
        if inventory is not None:
            execution_suite, runner = stage_suite(suite, directory, inventory, runner_hash)
        code = launch(execution_suite, directory, run_id, digest, timeout, collect, runner)
        if code is None:
            reasons.append("worker_timeout")
            errors.append(dict(category="worker_timeout", detail="The trusted pytest worker exceeded its configured timeout."))
        if (directory / "completion.json").exists():
            report = _input_json(directory / "completion.json", "completion_report_invalid")
        if (directory / "worker-error.json").exists():
            worker_error = _input_json(directory / "worker-error.json", "worker_error_report_invalid")
            category = worker_error.get("category") if isinstance(worker_error, dict) else None
            if category not in ("pytest_dependency_missing", "pytest_dependency_broken"):
                fail("worker_error_report_invalid", "The worker emitted an invalid dependency error report.")
            reasons.append(category)
            errors.append(dict(category=category, detail="The isolated worker cannot import its trusted pytest dependency."))
        if inventory is None:
            if suite_digest(suite, expected_path) != digest:
                reasons.append("suite_changed_during_execution")
        else:
            verify_inventory(suite, inventory)
            verify_inventory(execution_suite, inventory)
            if (hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest() != runner_hash
                    or hashlib.sha256(runner.read_bytes()).hexdigest() != runner_hash):
                fail("trusted_runner_changed", "The trusted runner changed during execution.")
        if collect:
            if (code != 0 or not isinstance(report, dict) or report.get("finished") is not True
                    or report.get("exitstatus") != 0 or report.get("collection_errors") != []
                    or not nodeids(report.get("collected")) or report.get("run_id") != run_id
                    or report.get("schema_version") != 1 or report.get("suite_sha256") != digest):
                reasons.append("collection_not_complete")
            if not reasons:
                expected = dict(schema_version=manifest_version, suite_sha256=digest, nodeids=report["collected"])
                if weights is not None:
                    try:
                        expected["scoring"] = validate_scoring(definition, expected["nodeids"])
                    except (ValueError, TypeError, OverflowError):
                        fail("invalid_scoring_definition", "Scoring must cover each collected test once, use one nodeid per item and positive unequal weights.")
                if inventory is not None:
                    expected.update(suite_files=inventory, runner_sha256=runner_hash)
                    expected["manifest_sha256"] = manifest_binding(expected)
                expected_path.parent.mkdir(parents=True, exist_ok=True)
                # Exclusive creation prevents accidental replacement of a frozen list.
                with expected_path.open("x", encoding="utf-8", newline="\n") as stream:
                    json.dump(expected, stream, indent=2)
                    stream.write("\n")
        else:
            validator = validate_weighted_completion if "scoring" in expected else validate_completion
            reasons += validator(report, expected, run_id, digest, code)
    except GateError as exc:
        reasons.append(exc.category)
        errors.append(dict(category=exc.category, detail=exc.detail))
    except KeyboardInterrupt:
        reasons.append("execution_interrupted")
        errors.append(dict(category="execution_interrupted", detail="The gate was interrupted before validating complete execution."))
    except OSError as exc:
        category = "trusted_permission_denied" if isinstance(exc, PermissionError) else "trusted_io_error"
        reasons.append(category)
        errors.append(dict(category=category, detail="A trusted file, staging directory, or worker process could not be accessed. OS error: " + str(exc.errno)))
    except (ValueError, TypeError, OverflowError):
        reasons.append("invalid_configuration_or_evidence")
        errors.append(dict(category="invalid_configuration_or_evidence", detail="Trusted configuration or execution evidence is invalid."))
    result = dict(schema_version=1, operation="freeze" if collect else "run", run_id=run_id,
                  suite_sha256=digest, worker_returncode=code, accepted=not reasons,
                  reasons=sorted(set(reasons)), errors=errors[:8], evidence_directory=str(directory),
                  execution_suite=str(execution_suite),
                  scope="trusted pytest completion only; sandbox and scientific correctness not certified")
    result.update(score_execution(expected, report, not reasons and not collect))
    atomic_write(directory / "gate-result.json", json.dumps(result, indent=2) + "\n")
    if not collect and not reasons:
        atomic_write(reward, str(result["score"]) + "\n")
    return result


def run_gate(suite, expected_path, output, timeout, collect=False, weights=None,
             suite_files=None, manifest_version=2):
    output = no_links(output)
    suite_absolute = Path(os.path.abspath(suite))
    manifest_absolute = Path(os.path.abspath(expected_path))
    skill = protected_skill_root()
    if (output.is_relative_to(suite_absolute)
            or (skill is not None and output.is_relative_to(skill))
            or manifest_absolute.is_relative_to(output)):
        fail("output_not_isolated", "Run output must be outside the trusted suite, manifest, and installed skill.")
    output.mkdir(parents=True, exist_ok=True)
    lock = no_links(output / ".completion.lock")
    # A directory is owned by one trial. Refuse concurrent writers, never
    # clear another active trial's score or delete its lock on contention.
    try:
        with lock.open("x", encoding="ascii") as stream:
            stream.write(str(os.getpid()))
    except FileExistsError:
        fail("output_in_use", "The output has an active or stale gate lock; use a new trial directory.")
    try:
        return _run_gate(suite, expected_path, output, timeout, collect, weights, suite_files, manifest_version)
    finally:
        lock.unlink()


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "_worker":
        _, suite, directory, run_id, digest, mode = args
        return worker(Path(suite), Path(directory), run_id, digest, mode == "collect")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("freeze", "run"))
    parser.add_argument("--suite", required=True, type=Path)
    parser.add_argument("--expected", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--timeout", type=float, default=270)
    parser.add_argument("--weights", type=Path, help="author scoring JSON; freeze only, embedded in the new manifest")
    parser.add_argument("--suite-files", type=Path,
                        help="freeze-only JSON list of relative trusted files; default includes every non-build, non-cache file")
    parser.add_argument("--manifest-version", type=int, choices=(1, 2), default=2,
                        help="freeze manifest version; 2 stages its explicit inventory, 1 keeps legacy strict whole-directory validation")
    parsed = parser.parse_args(args)
    if parsed.weights is not None and parsed.operation != "freeze":
        parser.error("--weights is only allowed for freeze; run uses the frozen manifest")
    if parsed.suite_files is not None and parsed.operation != "freeze":
        parser.error("--suite-files is only allowed for freeze; run uses the frozen manifest")
    def interrupted(signum, frame):
        raise KeyboardInterrupt
    for name in ("SIGTERM", "SIGHUP"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), interrupted)
    try:
        result = run_gate(parsed.suite, parsed.expected, parsed.out_dir, parsed.timeout,
                          parsed.operation == "freeze", parsed.weights, parsed.suite_files, parsed.manifest_version)
    except (OSError, ValueError) as exc:
        category = exc.category if isinstance(exc, GateError) else "invalid_paths_or_configuration"
        detail = exc.detail if isinstance(exc, GateError) else "The output, input paths, or active-run lock is invalid."
        print(json.dumps(dict(accepted=False, reasons=[category], errors=[dict(category=category, detail=detail)])))
        return 2
    print(json.dumps(result))
    return 0 if result["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
