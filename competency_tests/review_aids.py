"""Output-vs-output review aids -- competency tests CT-23 to CT-28.

These six are not registry checks and could not be: every one of them is a
question about *two* graphs, and every check the suite runs is a pattern over
one. ``version-diff`` compares two ontologies (a TBox question); nothing in
the suite compares two triplified outputs. So this module supplies them,
built on the suite's own loaders and reporting in its own ResultRow shape so
the findings merge into the same report as everything else.

    CT-23  compare_prefixes             prefix/namespace declarations differ
    CT-24  compare_predicates           predicate usage differs
    CT-25  compare_class_populations    class populations differ
    CT-26  compare_subject_values       subject-predicate values changed
    CT-27  normalise                    representation-only differences suppressed
    CT-28  compare_identifiers          "global" identifiers not stable

CT-27 is not a finding type of its own. It is the normalisation CT-24 and
CT-26 apply *before* comparing, and it is reported as the list of candidate
differences it suppressed -- which is what shows a reviewer it ran at all.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, SKOS

from ontology_suite.checks.merge import ResultRow

PREFIX_LINE = re.compile(r"^\s*@prefix\s+([A-Za-z0-9_.-]*):\s*<([^>]*)>\s*\.", re.MULTILINE)

# Geometry and other measured literals rarely round-trip bit-for-bit through a
# pipeline change. Comparing them at full precision buries the real changes.
DECIMAL_PLACES = 6

# A class population that moves by at least this fraction is worth a
# reviewer's attention rather than a line in a list.
MATERIAL_POPULATION_CHANGE = 0.2


def _row(check_id: str, severity: str, focus: str, message: str,
         path: Optional[str] = None, value: Optional[str] = None) -> ResultRow:
    return ResultRow(
        check_id=check_id, category="review-aid", title=None, severity=severity,
        focus_node=focus, path=path, value=value, message=message,
        remediation=None, sources=["review-aids"],
    )


# --------------------------------------------------------------------------
# CT-27: normalisation, applied before every value comparison below.
# --------------------------------------------------------------------------
def normalise(term) -> str:
    """Canonical form of a term for comparison purposes.

    Numerically equal literals compare equal however they are written and
    whatever datatype they carry: ``"12.50"^^xsd:decimal``, ``"12.5"^^xsd:decimal``
    and a plain ``"12.5"`` are one value. Non-numeric literals compare on
    their lexical form with datatype and language tag dropped, so a value
    that gained or lost an explicit ``xsd:string`` is not a change either.
    """
    if isinstance(term, Literal):
        try:
            quantum = Decimal(1).scaleb(-DECIMAL_PLACES)
            return "num:" + str(Decimal(str(term)).quantize(quantum).normalize())
        except (InvalidOperation, ValueError):
            return "lit:" + str(term)
    return "iri:" + str(term)


def _objects(graph: Graph, subject, predicate) -> Set[str]:
    return {normalise(o) for o in graph.objects(subject, predicate)}


def _raw_objects(graph: Graph, subject, predicate) -> Set[str]:
    """The terms as written -- n3() rather than str(), so a datatype that was
    added or dropped is a visible difference. str() returns the lexical form
    alone, under which "8.0"^^xsd:decimal and a plain "8.0" look identical
    and CT-27 would under-report what it suppressed."""
    return {o.n3() for o in graph.objects(subject, predicate)}


# --------------------------------------------------------------------------
# CT-23: prefix and namespace declarations
# --------------------------------------------------------------------------
def compare_prefixes(baseline_path, candidate_path) -> List[ResultRow]:
    """Read the two files' own @prefix declarations -- not rdflib's bound
    namespaces, which include a large default set neither document wrote."""
    def declared(path) -> Dict[str, str]:
        return dict(PREFIX_LINE.findall(Path(path).read_text(encoding="utf-8")))

    base, cand = declared(baseline_path), declared(candidate_path)
    rows: List[ResultRow] = []

    for prefix in sorted(set(base) - set(cand)):
        rows.append(_row("RVW-023", "Info", prefix,
                         "Prefix '{}:' (<{}>) is declared in the baseline only.".format(prefix, base[prefix]),
                         value=base[prefix]))
    for prefix in sorted(set(cand) - set(base)):
        rows.append(_row("RVW-023", "Info", prefix,
                         "Prefix '{}:' (<{}>) is declared in the candidate only.".format(prefix, cand[prefix]),
                         value=cand[prefix]))

    by_ns_base: Dict[str, Set[str]] = defaultdict(set)
    by_ns_cand: Dict[str, Set[str]] = defaultdict(set)
    for prefix, ns in base.items():
        by_ns_base[ns].add(prefix)
    for prefix, ns in cand.items():
        by_ns_cand[ns].add(prefix)

    for ns in sorted(set(by_ns_base) & set(by_ns_cand)):
        if by_ns_base[ns] != by_ns_cand[ns]:
            rows.append(_row(
                "RVW-023", "Warning", ns,
                "Namespace <{}> is bound to {} in the baseline but {} in the candidate. The IRIs are "
                "identical; only the serialisation differs, so a textual diff of the two files "
                "overstates the change.".format(ns, sorted(by_ns_base[ns]), sorted(by_ns_cand[ns])),
                value=", ".join(sorted(by_ns_cand[ns]))))
    return rows


# --------------------------------------------------------------------------
# CT-24: predicate usage
# --------------------------------------------------------------------------
def compare_predicates(baseline: Graph, candidate: Graph) -> List[ResultRow]:
    base = {p: len(list(baseline.triples((None, p, None)))) for p in set(baseline.predicates())}
    cand = {p: len(list(candidate.triples((None, p, None)))) for p in set(candidate.predicates())}
    rows: List[ResultRow] = []

    for p in sorted(set(base) - set(cand), key=str):
        rows.append(_row("RVW-024", "Warning", str(p),
                         "Predicate {} is used {}x in the baseline and never in the candidate.".format(p, base[p]),
                         value=str(base[p])))
    for p in sorted(set(cand) - set(base), key=str):
        rows.append(_row("RVW-024", "Warning", str(p),
                         "Predicate {} is used {}x in the candidate and never in the baseline.".format(p, cand[p]),
                         value=str(cand[p])))
    for p in sorted(set(base) & set(cand), key=str):
        if base[p] != cand[p]:
            rows.append(_row("RVW-024", "Info", str(p),
                             "Predicate {} is used {}x in the baseline and {}x in the candidate.".format(
                                 p, base[p], cand[p]),
                             value="{} -> {}".format(base[p], cand[p])))
    return rows


# --------------------------------------------------------------------------
# CT-25: class populations
# --------------------------------------------------------------------------
def compare_class_populations(baseline: Graph, candidate: Graph) -> List[ResultRow]:
    def populations(graph: Graph) -> Dict[URIRef, int]:
        counts: Dict[URIRef, int] = defaultdict(int)
        for _subject, cls in graph.subject_objects(RDF.type):
            counts[cls] += 1
        return counts

    base, cand = populations(baseline), populations(candidate)
    rows: List[ResultRow] = []
    for cls in sorted(set(base) | set(cand), key=str):
        before, after = base.get(cls, 0), cand.get(cls, 0)
        if before != after:
            largest = max(before, after)
            material = 0 in (before, after) or abs(before - after) / largest >= MATERIAL_POPULATION_CHANGE
            severity = "Warning" if material else "Info"
            rows.append(_row("RVW-025", severity, str(cls),
                             "Class {} has {} instance(s) in the baseline and {} in the candidate.".format(
                                 cls, before, after),
                             value="{} -> {}".format(before, after)))
    return rows


# --------------------------------------------------------------------------
# CT-26 (+ CT-27): subject-predicate values and relationship targets
# --------------------------------------------------------------------------
@dataclass
class ValueComparison:
    rows: List[ResultRow] = field(default_factory=list)
    suppressed: List[str] = field(default_factory=list)
    """Differences present in the raw lexical forms that vanish under
    normalise() -- CT-27's whole job, recorded so that it is visible."""


def compare_subject_values(baseline: Graph, candidate: Graph) -> ValueComparison:
    shared = ({s for s in baseline.subjects() if isinstance(s, URIRef)} &
              {s for s in candidate.subjects() if isinstance(s, URIRef)})
    out = ValueComparison()

    for subject in sorted(shared, key=str):
        predicates = set(baseline.predicates(subject)) | set(candidate.predicates(subject))
        for predicate in sorted(predicates, key=str):
            before = _objects(baseline, subject, predicate)
            after = _objects(candidate, subject, predicate)
            if before == after:
                raw_before = _raw_objects(baseline, subject, predicate)
                raw_after = _raw_objects(candidate, subject, predicate)
                if raw_before != raw_after:
                    out.suppressed.append("{} {}: {} vs {}".format(
                        subject, predicate, sorted(raw_before), sorted(raw_after)))
                continue
            gone, added = sorted(before - after), sorted(after - before)
            if gone and added:
                what = "changed from {} to {}".format(gone, added)
            elif gone:
                what = "lost {}".format(gone)
            else:
                what = "gained {}".format(added)
            out.rows.append(_row("RVW-026", "Warning", str(subject),
                                 "{} {} {}.".format(subject, predicate, what),
                                 path=str(predicate), value=", ".join(added) or None))
    return out


def suppression_row(comparison: ValueComparison) -> ResultRow:
    detail = "; ".join(comparison.suppressed) if comparison.suppressed else "none"
    return _row("RVW-027", "Info", "review-aids",
                "Normalisation suppressed {} representation-only difference(s) before comparing: {}. "
                "Without it each would have been reported as a changed value.".format(
                    len(comparison.suppressed), detail),
                value=str(len(comparison.suppressed)))


# --------------------------------------------------------------------------
# CT-28: identifier stability
# --------------------------------------------------------------------------
def compare_identifiers(baseline: Graph, candidate: Graph,
                        identity_predicate: URIRef = SKOS.notation) -> List[ResultRow]:
    """Group each graph's subjects by the business key that is supposed to be
    globally stable, and report every key whose subject IRI moved."""
    def keyed(graph: Graph) -> Dict[str, Set[str]]:
        out: Dict[str, Set[str]] = defaultdict(set)
        for subject, key in graph.subject_objects(identity_predicate):
            out[str(key)].add(str(subject))
        return out

    base, cand = keyed(baseline), keyed(candidate)
    rows: List[ResultRow] = []
    for key in sorted(set(base) & set(cand)):
        if base[key] != cand[key]:
            rows.append(_row("RVW-028", "Violation", key,
                             "The subject identified by {} \"{}\" is {} in the baseline and {} in the "
                             "candidate. The identifier was expected to be globally stable.".format(
                                 identity_predicate, key, sorted(base[key]), sorted(cand[key])),
                             path=str(identity_predicate),
                             value=", ".join(sorted(cand[key]))))
    for key in sorted(set(base) - set(cand)):
        rows.append(_row("RVW-028", "Info", key,
                         "{} \"{}\" is present in the baseline only.".format(identity_predicate, key)))
    for key in sorted(set(cand) - set(base)):
        rows.append(_row("RVW-028", "Info", key,
                         "{} \"{}\" is present in the candidate only.".format(identity_predicate, key)))
    return rows


# --------------------------------------------------------------------------
def compare_outputs(baseline_path, candidate_path,
                    identity_predicate: URIRef = SKOS.notation) -> Tuple[List[ResultRow], ValueComparison]:
    """Run all six review aids over two triplified outputs."""
    baseline = Graph().parse(baseline_path)
    candidate = Graph().parse(candidate_path)

    rows: List[ResultRow] = []
    rows += compare_prefixes(baseline_path, candidate_path)
    rows += compare_predicates(baseline, candidate)
    rows += compare_class_populations(baseline, candidate)
    values = compare_subject_values(baseline, candidate)
    rows += values.rows
    rows.append(suppression_row(values))
    rows += compare_identifiers(baseline, candidate, identity_predicate)
    return rows, values
