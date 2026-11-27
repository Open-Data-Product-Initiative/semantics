# ODPS 4.3 semantics specification — Development version

> **Development version — not a released standard.** This specification and its schemas are under development and may change.

Status: **unreleased development draft**. ODPS 4.2 under `source/` remains authoritative for that release. This isolated directory is the working location until the project promotes the draft into its 4.3 release branch and publishing workflow. The 4.3 schema URL in examples is deliberately illustrative, not a published endpoint. No release or deployment is implied.

## Purpose and scope

**Data Semantics** is a top-level product component, alongside Data Access and Data SLA. `product.semantics` optionally identifies semantic descriptions of the product and its payloads. Each description is an envelope containing a nonempty format identifier and exactly one of `spec` (a string containing the complete text) or `file` (a URI reference to the artifact). The format should be a media type; it is open to extensions. Optional `version` identifies the semantic document, not the product, vocabulary or source system. Neither syntax validity nor a source reference proves semantic correctness, review or approval.

`sources` is an optional named map at `product.semantics.sources`. Each entry requires `name`, and may have `type`, `url`, `apiURL` and `description`. A document's optional, nonempty `sources` array names the source systems used for it. Names are scoped to this semantics object and must exist in that map. They are not an exhaustive vocabulary inventory or a claim about every statement. Do not put credentials or sensitive sample data in metadata. Source-only and empty semantics objects are invalid: `product` and/or `payloads` must be present. Payload collections require `default`, including after external resolution. A product document can exist independently of payloads, access and sources.

## Access bindings

A data access profile may bind one payload using a reference object:

```yaml
semantics:
  $ref: '#/product/semantics/payloads/default'
```

For an API with multiple payloads use `semantics.bindings`, a nonempty array. Each entry has `operationId`, `semantics` (the reference object), and optionally `status` and `mediaType`. The [example](examples/product.yaml) shows two operations. `operationId` identifies an operation in the access profile's API specification, such as an OpenAPI operationId; it must be unique in that specification. `status` is a quoted three-digit HTTP status or `default`, where `default` means the response named `default` in the API specification, not all statuses. `mediaType` is the response representation's media type. When a selector is omitted the binding applies to every value of that dimension. For the same operation bindings must not overlap: for example, a binding with no status overlaps one for status `200`. If a single binding covers multiple responses, its semantic profile must correctly describe each covered payload. Unlisted operations or responses make no semantic claim. The access reference must point to exactly one named profile under the effective `product.semantics.payloads`; escape JSON Pointer tokens (`~` as `~0`, `/` as `~1`). Selectors do not reproduce the API definition. This proposal does not validate that operation IDs, status codes or media types exist in the API specification; consumers should report that check as not performed unless they inspect it.

## References and portability

An individual product or payload description may be a standalone `{$ref: ...}` to a complete envelope; `product.semantics` itself may likewise reference a complete semantics object. Reference objects have no siblings. The separate `file` field points to semantic bytes, not another ODPS envelope. Relative URIs resolve against the document containing that reference. Within a referenced profile, relative `file` and nested `$ref` values use that profile's document as their base. A fragment in an external `$ref` is a JSON Pointer into the referenced file; fragments in a local `$ref` refer to its containing file. Resolution must detect cycles and preserve each document's base URI.

Access bindings are a deliberate exception: their internal pointers resolve against the **effective ODPS document**, after the external `product.semantics` object is loaded at that location. This ensures that `#/product/semantics/payloads/default` works for inline and external semantics. Named source links in external profiles are checked against the effective parent semantics object. Reference resolution does not imply fetching remote resources during basic shape validation. Missing local artifacts are errors when artifact checking is requested; remote or unsupported content and unavailable checks must be reported as unresolved or not checked. Content parsing is separate from envelope validation.

A portable package should include local referenced profiles and artifacts with their relative paths preserved or consistently rewritten, and disclose unresolved external dependencies. Remote concepts can remain dependencies even when local files are included. The schema does not define a packaging implementation, semantic correctness, a mapping language, a data-contract dependency, a required vocabulary service, or a mandatory RDF format. Existing `product.details.<language>.standards` retains its existing meaning and is not a conformity assertion.

## Development and checks

`build_schema.py` derives `schema/odps.json` from the released 4.2 canonical JSON and generates its YAML representation. Rebuild with `python3 drafts/semantics/build_schema.py`; review both generated outputs. `validate.py` provides a local reference and cross-reference check without network access. It parses Turtle when RDFLib is installed, and reports unsupported formats, missing parsers and remote resolution as not checked; it is a development checker, not a production resolver or SDK feature. External Data Access packages/profiles are reported as not checked. It does not resolve API specifications or verify operation selectors against them. Run:

```sh
python3 -m unittest discover -s drafts/semantics/tests -v
python3 drafts/semantics/validate.py drafts/semantics/examples/product.yaml
python3 scripts/validate_spec_alignment.py
```

JSON-LD and other format parsing, remote resolution, SDK generation, package creation and validation of selectors against an API specification are follow-up work outside this repository's current tooling. The published schema and the project's normal generation and deployment scripts target 4.2; promoting 4.3 requires an explicit release integration and publishing decision.
