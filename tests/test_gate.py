"""Assertions about gate.py's one job: turning a config file into suite argv.

The gate runs nothing here. What can break in a wrapper like this is the
mapping -- a key silently ignored, a path resolved against the wrong
directory, a command-line flag not overriding the file -- and each of those
fails quietly in CI as "the gate passed", which is the worst way for a gate
to be wrong. So the argv is asserted directly.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import gate


def write_config(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "ontology-suite.yml"
    path.write_text(text, encoding="utf-8")
    return path


def test_every_flag_is_a_real_suite_flag():
    """The mapping is only trustworthy if the suite still accepts each flag.

    Asserted against the suite's own parser rather than a copied list, so a
    renamed or dropped flag fails here instead of at the next release.
    """
    import argparse

    from ontology_suite import cli

    parser = cli.build_arg_parser()
    subcommands = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    run_parser = subcommands.choices["run"]
    known = {option for action in run_parser._actions for option in action.option_strings}
    missing = sorted(flag for flag in gate.FLAGS.values() if flag not in known)
    assert not missing, f"gate.py maps flags the suite's `run` no longer has: {missing}"


def test_config_becomes_argv(tmp_path):
    config = gate.load_config(write_config(tmp_path, """
ontology: model/integration.ttl
queries: mappings
query_pattern: "**/*.rq"
engine: sparql
fail_on: Violation
"""))
    argv = gate.to_argv(config)

    assert argv[:4] == [sys.executable, "-m", "ontology_suite", "run"]
    assert "--query-pattern" in argv and "**/*.rq" in argv
    assert argv[argv.index("--engine") + 1] == "sparql"
    assert argv[argv.index("--fail-on") + 1] == "Violation"


def test_paths_resolve_against_the_config_not_the_cwd(tmp_path):
    """A committed config describes the project's layout. Running the gate
    from a subdirectory, or from a hook, must not change what it checks."""
    config = gate.load_config(write_config(tmp_path, "ontology: model/integration.ttl\n"))
    assert config["ontology"] == str((tmp_path / "model" / "integration.ttl").resolve())


def test_repeatable_and_boolean_flags(tmp_path):
    config = gate.load_config(write_config(tmp_path, """
data:
  - out/a.ttl
  - out/b.ttl
profile:
  - EL
  - RL
allow_network: true
exclude_imports: false
"""))
    argv = gate.to_argv(config)

    assert argv.count("--data") == 2
    assert [argv[i + 1] for i, a in enumerate(argv) if a == "--profile"] == ["EL", "RL"]
    assert "--allow-network" in argv
    assert "--exclude-imports" not in argv, "a false boolean must not pass the flag"


def test_command_line_overrides_the_file(tmp_path):
    write_config(tmp_path, "ontology: model/integration.ttl\nfail_on: Violation\n")
    args = gate.parse_args(["--config", str(tmp_path / "ontology-suite.yml"),
                            "--fail-on", "never", "--dry-run"])
    config = gate.load_config(Path(args.config))
    for key in gate.FLAGS:
        given = getattr(args, key, None)
        if given is not None:
            config[key] = given

    assert config["fail_on"] == "never"
    assert config["ontology"].endswith("integration.ttl"), "overriding one key must not drop the rest"


def test_an_unknown_setting_is_refused(tmp_path):
    """Silently ignoring a typo'd key would mean a gate quietly not checking
    what its config says it checks."""
    path = write_config(tmp_path, "ontology: model/integration.ttl\nfail_onn: Violation\n")
    with pytest.raises(SystemExit) as raised:
        gate.load_config(path)
    assert "fail_onn" in str(raised.value)


def test_a_missing_config_is_refused(tmp_path):
    with pytest.raises(SystemExit) as raised:
        gate.load_config(tmp_path / "nope.yml")
    assert "no config file" in str(raised.value)


def test_the_repos_own_example_config_is_valid():
    """The committed ontology-suite.yml is the worked example people copy."""
    config = gate.load_config(gate.ROOT / gate.DEFAULT_CONFIG)
    assert Path(config["ontology"]).is_file()
    assert Path(config["queries"]).is_dir()
    assert gate.to_argv(config)[3] == "run"
