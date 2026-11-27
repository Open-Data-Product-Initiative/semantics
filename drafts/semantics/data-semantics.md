# Data Semantics

> **Development version.** This proposed ODPS 4.3 component may change before release.

The OPTIONAL `product.semantics` object describes the meaning of the data product and its payloads. It is a top-level product component alongside Data Access and Data SLA. Semantic descriptions can be included as text or stored in separate files. Named payload profiles let Data Access interfaces identify the description that applies to the data they deliver.

A semantics object MUST contain a `product` description, `payloads`, or both. `sources` MAY identify the systems used to create those descriptions. If `payloads` is present, it MUST include a profile named `default`. A product description can be used on its own, without payloads, Data Access or source systems.

## Optional attributes and elements

> Example of Data Semantics with product and payload descriptions:

```yml
product:
  semantics:
    sources:
      enterpriseGlossary:
        name: Enterprise glossary
        type: vocabulary-service
        url: https://example.org/glossary
    product:
      format: text/turtle
      sources: [enterpriseGlossary]
      spec: |
        @prefix ex: <https://example.org/> .
        ex:Accounts a ex:DataProduct .
    payloads:
      default:
        format: text/turtle
        version: '1.0'
        sources: [enterpriseGlossary]
        file: ./semantics/account.ttl
      transactions:
        format: text/turtle
        file: ./semantics/transactions.ttl
```

The `product` and each payload profile contain a semantic document description. A description MUST include `format` and exactly one of `spec` or `file`. The optional `sources` list refers to names defined in the top-level `product.semantics.sources` object.

> Example of an external Data Semantics object:

```yml
product:
  semantics:
    $ref: ./semantics/semantics.yaml
```

The external file contains the complete `sources`, `product` and/or `payloads` object. A reference object MUST contain only `$ref`.

> Example of an external payload profile:

```yml
product:
  semantics:
    payloads:
      default:
        $ref: ./semantics/account-profile.yaml
```

> Contents of `account-profile.yaml`:

```yml
format: text/turtle
file: ./account.ttl
```

The profile's `$ref` identifies an ODPS semantic description, while its `file` identifies the semantic document itself. `./account.ttl` is resolved relative to `account-profile.yaml`. See the [complete external profile example](semantics-examples/product.yaml).

| Element name | Type | Options | Description |
|---|---|---|---|
| **semantics** | object or reference object | OPTIONAL | Top-level product component. Contains `product`, `payloads`, or both, and optionally `sources`; alternatively, `$ref` identifies an external complete semantics object. |
| **sources** | object | OPTIONAL | Named source systems shared by the descriptions. Each key is a source identifier, such as `enterpriseGlossary`. The object MUST contain at least one entry when present. |
| **product** | object or reference object | OPTIONAL | Semantic document describing the product as a whole. Uses the semantic document fields below, or `$ref` to a complete document description. |
| **payloads** | object | OPTIONAL | Named payload semantic profiles. MUST include `default`; additional profiles MAY describe other payloads. Each value uses the semantic document fields below or a reference to a complete profile. |
| **default** | object or reference object | REQUIRED when `payloads` is present | The default payload profile. The same requirement applies to an externally loaded semantics object. |
| **$ref** | URI-reference | REQUIRED in a reference object | References an external semantics object or a complete product or payload description. A reference object has no sibling fields. |

### Semantic source fields

A source describes a system used to create or support a semantic description. It is not a list of all concepts or vocabularies, and it does not assert approval or conformance. Avoid credentials in metadata.

| Element name | Type | Options | Description |
|---|---|---|---|
| **name** | string | REQUIRED | Human-readable source system name. |
| **type** | string | OPTIONAL | Extensible description of the system type, such as `vocabulary-service` or `semantic-repository`. |
| **url** | URI-reference | OPTIONAL | Location of a human-readable service or repository. |
| **apiURL** | URI-reference | OPTIONAL | Machine-readable service endpoint. |
| **description** | string | OPTIONAL | Explanation of the source system's role. |

### Semantic document fields

The following fields apply to both `semantics.product` and each named `semantics.payloads` profile. A standalone `$ref` may be used instead of these fields.

| Element name | Type | Options | Description |
|---|---|---|---|
| **format** | string | REQUIRED | Format of the semantic document, preferably a media type such as `text/turtle` or `application/ld+json`. This is separate from the format of the delivered data. |
| **spec** | string | REQUIRED if `file` is absent | Complete inline semantic document as text. MUST NOT appear with `file`. |
| **file** | URI-reference | REQUIRED if `spec` is absent | Location of the semantic document. MUST NOT appear with `spec`. |
| **version** | string | OPTIONAL | Version of this semantic document, distinct from the product, vocabulary and source-system versions. |
| **description** | string | OPTIONAL | Human-readable summary of the document. |
| **sources** | array of strings | OPTIONAL | Nonempty list of unique source identifiers defined in `product.semantics.sources`. |

## Data Access bindings

A Data Access profile MAY refer to a named payload profile. Use one reference when the interface delivers a single payload; several access profiles may reference the same semantic profile.

> Example of a single payload binding:

```yml
product:
  dataAccess:
    default:
      outputPortType: API
      semantics:
        $ref: '#/product/semantics/payloads/default'
```

For interfaces with multiple payloads, `bindings` identifies each applicable profile by API operation and, where needed, response status and media type. The API specification remains the authority for the operation and response definitions.

> Example of bindings for two API responses:

```yml
product:
  dataAccess:
    default:
      outputPortType: API
      specsURL: https://example.org/openapi.yaml
      semantics:
        bindings:
          - operationId: getAccount
            status: '200'
            mediaType: application/json
            semantics:
              $ref: '#/product/semantics/payloads/default'
          - operationId: listTransactions
            status: '200'
            mediaType: application/json
            semantics:
              $ref: '#/product/semantics/payloads/transactions'
```

| Element name | Type | Options | Description |
|---|---|---|---|
| **semantics** | reference object or object | OPTIONAL | On a Data Access profile, either a single reference to a named payload profile or an object containing `bindings`. |
| **bindings** | array | REQUIRED for multiple selectors | Nonempty list of operation-to-payload bindings. Each entry contains `operationId` and `semantics` and may include `status` and `mediaType`. |
| **operationId** | string | REQUIRED | Identifier of an operation in the interface's API specification. It must be unique within that specification. |
| **status** | string | OPTIONAL | Three-digit HTTP response status such as `'200'`, or `default` for the response named `default` in the API specification. |
| **mediaType** | string | OPTIONAL | Media type of the response representation, such as `application/json`. |
| **semantics** | reference object | REQUIRED in each binding | `$ref` to exactly one named profile under `#/product/semantics/payloads/`. |

An omitted `status` or `mediaType` selects all values of that dimension. Bindings for the same operation MUST NOT overlap: for example, a binding without `status` overlaps one for `'200'`. A profile that applies to several responses must describe each covered payload. Unlisted operations and responses make no semantic claim. Escape `~` as `~0` and `/` as `~1` in profile names used in JSON Pointer references.

## Reference resolution and validation

Resolve each relative `$ref` or `file` URI against the document containing it. Fragments in ODPS references use JSON Pointer into the referenced or containing document. Resolution MUST detect cycles and preserve the base URI of each loaded document.

Data Access bindings are resolved against the **effective product document** after an external `product.semantics` object is loaded. Thus `#/product/semantics/payloads/default` targets the same effective location whether the semantics object is inline or external. Source names in external profiles are checked against that effective semantics object's `sources`.

Structural validation does not require network access. When checked, malformed references, missing local files and unknown source names are errors. Unsupported formats, unavailable parsers and unreachable remote resources are reported as not checked or unresolved. Syntax validity does not establish semantic correctness, approval or conformance. Validation against the API specification is a separate check.

Include local semantic documents and profile files when creating a portable package, preserving or consistently rewriting relative paths. Identify unresolved external dependencies. The schema does not require a particular vocabulary service, RDF format, data contract or generation tool. The existing `product.details.<language>.standards` field retains its existing meaning and is not a conformity assertion.
