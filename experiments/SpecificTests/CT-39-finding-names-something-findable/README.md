# CT-39 — A finding names something a reader can find

```bash
./run.sh          # verdict only
./run.sh --show   # verdict plus every finding
```

| Path | What it is |
|---|---|
| `ontologies/model.ttl` | two untagged labels, identical but for what carries them |
| `out/` | `findings.txt` and `full_results.csv`, via `--reports minimal` |

## The two sets

Both are meant to be **reported**. What separates them is whether the message
survives — which is a different question from every other folder here, and the
reason this one exists.

| | Carries the untagged label | Reported | Message must |
|---|---|---|---|
| **error** | an anonymous `owl:Restriction` | **yes** | name something, not an internal identifier |
| **control** | `:Chassis`, a named class | **yes** | name `:Chassis` in full |

## The defect it was written for

`STY-003` built its `sh:resultMessage` with `STR(?e)`. SPARQL 1.1 §17.4.2.5
defines `STR()` for literals and IRIs only, so `STR()` of a blank node is a type
error: `CONCAT` errors, `BIND` leaves the message variable unbound, and a
`CONSTRUCT` template drops a triple whose object is unbound.

The check went on firing. Right count, right severity, right focus node — and
no message at all for **60 of 65 findings** on the suite's own stress fixture.
Nothing on this board asserted anything about a message, so nothing failed. The
defect reached users through the VS Code extension, which runs the portable
queries through oxigraph and has no SHACL formulation to fall back on: measured
on its own bundled engine, 1 message for 2 findings.

`EFF-001` had the same defect in its own message, interpolating the far end of a
`subClassOf` chain that is often an anonymous class expression. It was found by
this assertion within minutes of the assertion existing, on a fixture that had
been in the repo all along.

## Why `--engine sparql`

Not a detail — the point. With both formulations running, `checks/merge.py`
fills a missing message from whichever source still has one, so the portable
layer can stop producing messages entirely and the merged report looks healthy.
It is also the configuration the extension uses, which is where the defect
shipped.

## Why the fix is `IF` and not `COALESCE`

`COALESCE(STR(?x), "…")` catches the *error*, so it only helps where `STR()`
errors. rdflib does not raise on `STR()` of a blank node — it returns the
internal identifier — so under rdflib the message stayed present and named
something meaningless that differed on every run. `IF(isBlank(?x), "[a blank
node]", STR(?x))` evaluates only the branch it takes, so `STR()` is never
reached for a blank node and every engine produces the same text.

That is why the run asserts both halves: a message must be **present**, and it
must not be **built out of an internal identifier**. The first alone passes
under rdflib with a useless message; the second alone passes under a conformant
engine with no message at all.

## What it does not check

The `focus_node` column. A blank node's identifier is the only handle it has, so
carrying it there is correct — it is the prose a person reads that must not be
built out of it. Scanning the whole CSV row rather than the message column
failed a run whose message was already right, which is how the assertion came
to be scoped.
