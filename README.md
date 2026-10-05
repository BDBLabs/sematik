# sematik

**Semantic Conversion Engine** — governed, meaning-based data conversion.

Instead of `schema → schema`, sematik reasons across:

`Source representation → source business meaning → domain concept → temporal meaning → authority/provenance → canonical representation → transformation rule → target representation → validation → reconciliation → evidentiary record`

Migrations run through a canonical **Semantic Intermediate Representation (SIR)**:

`Legacy A → Semantic Canonical Model → Target B`

The first proving domain is California property assessment (CPASF). The
generic engine must not hard-code domain meaning — domain knowledge arrives
via versioned **Domain Packs**.

See [`docs/SPEC.md`](docs/SPEC.md) for the full requirements specification.

## Status

Pre-alpha — repository scaffolded 2026-10-05. Nothing implemented yet.
