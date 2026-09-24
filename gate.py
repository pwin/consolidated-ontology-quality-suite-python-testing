"""A CI gate: run the Ontology Quality Suite over a project's own folders and
exit non-zero if it finds anything at or above a chosen severity.

    uv run python gate.py --config ontology-suite.yml
    uv run python gate.py --ontology model/integration.ttl --queries mappings/

The suite's own `run` subcommand already takes every path this needs, so this
is deliberately not a second implementation of anything: it reads a config
file, turns it into argv, and execs `python -m ontology_suite`. What it adds is
that the config file can be *committed*, so the run a developer does by hand,
the run in CI, and the run in a git hook are the same run rather than three
copies of a command line that drift apart.

Two rules keep it honest, and they are the whole design:

  * every key maps to exactly one CLI flag, with no computed or derived
    values -- if you want to know what a config does, read the flag's --help;
  * a flag given on the command line beats the file, so CI can override one
    value (`--fail-on never` on a draft branch, say) without a second file.

`--dry-run` prints the argv and stops, which is the fastest way to see what a
config actually means and the thing to paste into a bug report.

Scope: this gates a project. It does not run this repo's own fixtures -- that
is report.py and pytest.
"""
from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = "ontology-suite.yml"

# Config key -> CLI flag. The value's Python type decides how it is rendered:
# a list repeats the flag, a bool passes it bare, anything else passes it with
# its value. Keys are the flag names with the dashes swapped for underscores,
# so there is nothing to memorise and nothing to translate.
#
# Only the `run` stage's flags are here. A gate that needs `consistency` or
# `version-diff` is asking a question about two versions, which needs the
# other version as an input and belongs in its own job -- see COMMANDS.md.
FLAGS: Dict[str, str] = {
    "ontology": "--ontology",
    "queries": "--queries",
    "query_pattern": "--query-pattern",
    "csv_dir": "--csv-dir",
    "data": "--data",
    "data_pattern": "--data-pattern",
    "registry": "--registry",
    "sparql": "--sparql",
    "shapes": "--shapes",
    "import_dir": "--import-dir",
    "exclude_imports": "--exclude-imports",
    "allow_network": "--allow-network",
    "engine": "--engine",
    "reasoner": "--reasoner",
    "profile": "--profile",
    "own_namespace": "--own-namespace",
    "out_dir": "--out-dir",
    "fail_on": "--fail-on",
    "verbose": "--verbose",
}

# Paths are resolved relative to the config file rather than the working
# directory: a committed config describes the project's layout, and a gate
# invoked from a subdirectory or by a hook should not mean something else.
PATH_KEYS = {"ontology", "queries", "csv_dir", "data", "registry", "sparql",
             "shapes", "import_dir", "out_dir"}


def load_config(path: Path) -> Dict[str, Any]:
    """The config file as a dict, with its paths made absolute.

    A missing file is an error rather than an empty config: a gate that
    silently checks nothing because someone moved a file is the one failure
    mode this whole script exists to avoid.
    """
    if not path.is_file():
        raise SystemExit(f"gate: no config file at {path}")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise SystemExit(f"gate: {path} should hold a mapping of settings, not {type(loaded).__name__}")

    unknown = sorted(set(loaded) - set(FLAGS))
    if unknown:
        raise SystemExit(
            "gate: {} has settings that are not suite flags: {}\n"
            "      known settings: {}".format(
                path, ", ".join(unknown), ", ".join(sorted(FLAGS))))

    base = path.parent
    config: Dict[str, Any] = {}
    for key, value in loaded.items():
        if key in PATH_KEYS and value is not None:
            if isinstance(value, list):
                value = [_resolve(base, v) for v in value]
            else:
                value = _resolve(base, value)
        config[key] = value
    return config


# Values the suite resolves for itself, which must be passed through as
# written. `@builtin` is the suite's own query tree wherever this install put
# it -- the source checkout for an editable install, site-packages for a
# wheel. Resolving it here as a path produced `<repo>/@builtin`, a directory
# that does not exist, and the run then reported that it had skipped every
# built-in check. Which it had.
PASSTHROUGH = {"@builtin"}


def _resolve(base: Path, value: Any) -> str:
    """A config path, made absolute against the config file's directory."""
    text = str(value)
    if text in PASSTHROUGH:
        return text
    return str((base / text).resolve())


def to_argv(config: Dict[str, Any]) -> List[str]:
    """The suite invocation this config describes."""
    argv = [sys.executable, "-m", "ontology_suite", "run"]
    for key, flag in FLAGS.items():           # FLAGS order, so argv is stable
        if key not in config or config[key] is None:
            continue
        value = config[key]
        if isinstance(value, bool):
            if value:
                argv.append(flag)
        elif isinstance(value, list):
            for item in value:
                argv += [flag, str(item)]
        else:
            argv += [flag, str(value)]
    return argv


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Any setting below also works as a key in the config file, "
               "spelled with underscores. A flag given here wins.")
    parser.add_argument("--config", default=DEFAULT_CONFIG,
                        help=f"the gate's config file (default: {DEFAULT_CONFIG}). "
                             "Paths inside it are relative to it, not to the working directory")
    parser.add_argument("--no-config", action="store_true",
                        help="ignore the config file and use only the flags given here")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the suite command this would run, and stop")
    for key, flag in FLAGS.items():
        if key in ("exclude_imports", "allow_network", "verbose"):
            parser.add_argument(flag, dest=key, action="store_true", default=None)
        elif key in ("data", "profile"):
            parser.add_argument(flag, dest=key, action="append", default=None)
        else:
            parser.add_argument(flag, dest=key, default=None)
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    config: Dict[str, Any] = {}
    if not args.no_config:
        config = load_config(Path(args.config) if Path(args.config).is_absolute()
                             else (ROOT / args.config))

    # The command line wins, key by key, so overriding one setting does not
    # mean restating the rest.
    for key in FLAGS:
        given = getattr(args, key, None)
        if given is not None:
            config[key] = given

    if not config.get("ontology") and not config.get("queries") and not config.get("data"):
        raise SystemExit(
            "gate: nothing to check -- give at least one of --ontology, --queries or --data, "
            "in the config file or on the command line")

    suite_argv = to_argv(config)
    print("gate: " + " ".join(shlex.quote(a) for a in suite_argv))
    if args.dry_run:
        return 0

    completed = subprocess.run(suite_argv)
    # The suite's own exit code is the gate: 1 when a finding reaches
    # --fail-on, 0 otherwise. Passing it straight through means this script
    # never becomes a second opinion about what counts as a failure.
    verdict = "PASS" if completed.returncode == 0 else "FAIL"
    print(f"gate: {verdict} (suite exit {completed.returncode}, "
          f"--fail-on {config.get('fail_on', 'Violation (suite default)')})")
    return completed.returncode


if __name__ == "__main__":
    sys.exit(main())
