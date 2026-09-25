"""CT-23 to CT-28 -- what changed between two comparable outputs.

Six questions about one pair of files, which is why they are one folder. They
share their data, they share their parse, and a reviewer asks them together:
"the pipeline ran again, what moved?"

Self-contained by design: this imports rdflib and nothing from the repo it
sits in, so the folder can be copied into another project and still answer.

Every finding names the file it is about. A comparison finding that does not
say which side it came from leaves the reader to guess, and the guess is
wrong half the time.

    python compare.py data/baseline.ttl data/candidate.ttl
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, SKOS

PREFIX_LINE = re.compile(r"^\s*@prefix\s+([A-Za-z0-9_.-]*):\s*<([^>]*)>\s*\.", re.MULTILINE)

# A business key: the property a person uses to recognise the thing, rather
# than the IRI a pipeline minted for it. Project-specific, and stated here
# rather than guessed.
BUSINESS_KEY = SKOS.notation


def normalise(term) -> str:
    """The canonical form of a term, for comparison.

    "1.50" and "1.5" are the same number and a reviewer should not spend
    attention on the difference. Everything else compares as written.
    """
    if isinstance(term, Literal):
        try:
            return str(Decimal(str(term)).normalize())
        except (InvalidOperation, ValueError):
            return str(term)
    return str(term)


def finding(ct, check, detail, files):
    return (ct, check, detail, files)


# -- CT-23 ------------------------------------------------------------------
def compare_prefixes(a_path, b_path):
    def declared(path):
        return {p: ns for p, ns in PREFIX_LINE.findall(Path(path).read_text(encoding="utf-8"))}

    a, b = declared(a_path), declared(b_path)
    out = []
    for prefix in sorted(set(a) - set(b)):
        out.append(finding("CT-23", "RVW-023",
                           "prefix '%s:' (<%s>) is declared in the baseline only" % (prefix, a[prefix]),
                           [a_path]))
    for prefix in sorted(set(b) - set(a)):
        out.append(finding("CT-23", "RVW-023",
                           "prefix '%s:' (<%s>) is declared in the candidate only" % (prefix, b[prefix]),
                           [b_path]))
    for namespace in sorted({*a.values()} & {*b.values()}):
        left = sorted(p for p, ns in a.items() if ns == namespace)
        right = sorted(p for p, ns in b.items() if ns == namespace)
        if left != right:
            out.append(finding(
                "CT-23", "RVW-023",
                "<%s> is bound to %s in the baseline and %s in the candidate; the IRIs are "
                "identical, so a textual diff overstates the change" % (namespace, left, right),
                [a_path, b_path]))
    return out


# -- CT-24 ------------------------------------------------------------------
def compare_predicates(a, b, a_path, b_path):
    left = defaultdict(int)
    right = defaultdict(int)
    for _s, p, _o in a:
        left[p] += 1
    for _s, p, _o in b:
        right[p] += 1
    out = []
    for p in sorted(set(left) | set(right), key=str):
        if left[p] and not right[p]:
            out.append(finding("CT-24", "RVW-024",
                               "%s is used %dx in the baseline and never in the candidate"
                               % (p, left[p]), [a_path]))
        elif right[p] and not left[p]:
            out.append(finding("CT-24", "RVW-024",
                               "%s is used %dx in the candidate and never in the baseline"
                               % (p, right[p]), [b_path]))
    return out


# -- CT-25 ------------------------------------------------------------------
def compare_class_populations(a, b, a_path, b_path):
    def counts(graph):
        out = defaultdict(int)
        for _s, _p, cls in graph.triples((None, RDF.type, None)):
            out[cls] += 1
        return out

    left, right = counts(a), counts(b)
    return [finding("CT-25", "RVW-025",
                    "%s has %d instance(s) in the baseline and %d in the candidate"
                    % (cls, left[cls], right[cls]), [a_path, b_path])
            for cls in sorted(set(left) | set(right), key=str)
            if left[cls] != right[cls]]


# -- CT-26 and CT-27 --------------------------------------------------------
def compare_subject_values(a, b, a_path, b_path):
    """Values that changed for a subject both files describe.

    Normalisation runs first, and what it suppresses is reported in its own
    right: a reviewer who is told nothing changed should know whether that
    means "nothing" or "nothing once 1.50 and 1.5 were treated as equal".
    """
    def by_subject(graph):
        out = defaultdict(lambda: defaultdict(set))
        for s, p, o in graph:
            out[s][p].add(o)
        return out

    left, right = by_subject(a), by_subject(b)
    out, suppressed = [], 0
    for subject in sorted(set(left) & set(right), key=str):
        for predicate in sorted(set(left[subject]) | set(right[subject]), key=str):
            raw_l = {str(o) for o in left[subject][predicate]}
            raw_r = {str(o) for o in right[subject][predicate]}
            norm_l = {normalise(o) for o in left[subject][predicate]}
            norm_r = {normalise(o) for o in right[subject][predicate]}
            if norm_l == norm_r:
                if raw_l != raw_r:
                    suppressed += 1
                continue
            if norm_l and not norm_r:
                out.append(finding("CT-26", "RVW-026",
                                   "%s %s lost %s" % (subject, predicate, sorted(raw_l)), [a_path]))
            elif norm_r and not norm_l:
                out.append(finding("CT-26", "RVW-026",
                                   "%s %s gained %s" % (subject, predicate, sorted(raw_r)), [b_path]))
            else:
                out.append(finding("CT-26", "RVW-026",
                                   "%s %s changed from %s to %s"
                                   % (subject, predicate, sorted(raw_l), sorted(raw_r)),
                                   [a_path, b_path]))
    out.append(finding("CT-27", "RVW-027",
                       "normalisation suppressed %d representation-only difference(s) before "
                       "comparing -- reported even when it suppresses nothing, so the pass is "
                       "visible" % suppressed, [a_path, b_path]))
    return out


# -- CT-28 ------------------------------------------------------------------
def compare_identifiers(a, b, a_path, b_path):
    def keyed(graph):
        out = defaultdict(set)
        for s, _p, key in graph.triples((None, BUSINESS_KEY, None)):
            out[str(key)].add(str(s))
        return out

    left, right = keyed(a), keyed(b)
    return [finding("CT-28", "RVW-028",
                    "the subject identified by %s '%s' is %s in the baseline and %s in the "
                    "candidate" % (BUSINESS_KEY, key, sorted(left[key]), sorted(right[key])),
                    [a_path, b_path])
            for key in sorted(set(left) & set(right))
            if left[key] != right[key]]


def run(a_path, b_path):
    a, b = Graph(), Graph()
    a.parse(a_path)
    b.parse(b_path)
    return (compare_prefixes(a_path, b_path)
            + compare_predicates(a, b, a_path, b_path)
            + compare_class_populations(a, b, a_path, b_path)
            + compare_subject_values(a, b, a_path, b_path)
            + compare_identifiers(a, b, a_path, b_path))


def main(argv):
    if len(argv) != 3:
        print(__doc__.strip().splitlines()[-1].strip(), file=sys.stderr)
        return 2
    for ct, check, detail, files in run(argv[1], argv[2]):
        print("%-6s %-8s %s" % (ct, check, detail))
        print("%14s in: %s" % ("", ", ".join(Path(f).name for f in files)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
