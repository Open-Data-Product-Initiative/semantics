# Data Semantics

> **Development version.** This proposed ODPS 4.3 component may change before release.

The OPTIONAL `product.semantics` object describes the meaning of the data product and its payloads. It is a top-level product component alongside Data Access and Data SLA. Semantic descriptions can be included under `spec` or referenced as separate files with `$ref`. Named payload profiles let Data Access interfaces identify the description that applies to the data they deliver.

A semantics object MUST contain `productSemantics`, `payloads`, or both. `sources` MAY identify the systems used to create those descriptions. If `payloads` is present, it MUST include a profile named `default`. A product description can be used on its own, without payloads, Data Access or source systems.

## Mandatory attributes and elements

Data Semantics is OPTIONAL for a product. The requirements below apply only when the relevant object is provided. A semantics object MUST contain a product description, payload profiles, or both.

> Example of the required fields in an inline payload profile:

```yml
product:
  semantics:
    payloads:
      default:
        format: text/turtle
        spec: |
          @prefix ex: <https://example.org/> .
          ex:Account a ex:Payload .
```

| <div style="width:150px">Element name</div> | Type | Options | Description |
|---|---|---|---|
| **default** | object or reference object | REQUIRED when `payloads` is present | The default named payload profile. The requirement also applies after an external semantics object is resolved. |
| **format** | string | REQUIRED in a document description | Format of the semantic document. Nonempty; no maximum length is specified. Use a media type such as `text/turtle` or `application/ld+json` where practical; see [RFC 6838](https://www.rfc-editor.org/rfc/rfc6838.html). The schema accepts other format identifiers. |
| **spec** | string | REQUIRED in an inline document description | Complete semantic document as text. Minimum 1 character; no maximum length is specified. To reference external content, use a standalone `$ref` instead. |

A product or payload description MAY instead be a standalone `$ref` to an external semantic document or a complete external profile. A reference object MUST contain only `$ref`; a referenced profile MUST meet the inline document requirements above.

## Optional attributes and elements

> Example of optional source systems and external payload profiles:

```yml
product:
  semantics:
    sources:
      enterpriseGlossary:
        name: Enterprise glossary
        type: vocabulary-service
        url: https://example.org/glossary
    productSemantics:
      format: text/turtle
      sources: [enterpriseGlossary]
      spec: |
        @prefix ex: <https://example.org/> .
        ex:Accounts a ex:DataProduct .
    payloads:
      default:
        $ref: ./semantics/account.ttl
      transactions:
        $ref: ./semantics/transactions.ttl
```

A product or payload description MAY be inline with `format` and `spec`, or use `$ref` to an external semantic document or profile. The optional `sources` list refers to names defined in the top-level `product.semantics.sources` object.

> Example of an external Data Semantics object:

```yml
product:
  semantics:
    $ref: ./semantics/semantics.yaml
```

The external file contains the complete `sources`, `productSemantics` and/or `payloads` object. A reference object MUST contain only `$ref`.

> Example of an external payload profile:

```yml
product:
  semantics:
    sources:
      enterpriseGlossary:
        name: Enterprise glossary
    payloads:
      default:
        $ref: ./semantics/account-profile.yaml
```

> Contents of `account-profile.yaml`:

```yml
format: text/turtle
version: '1.0'
sources: [enterpriseGlossary]
spec: |
  @prefix ex: <https://example.org/> .
  ex:Account a ex:Payload .
```

This profile's `$ref` identifies an external ODPS profile containing the inline semantic document. A `$ref` can instead identify a semantic document directly, as in the preceding example. See the [complete external profile example](semantics-examples/product.yaml).

| Element name | Type | Options | Description |
|---|---|---|---|
| **semantics** | object or reference object | OPTIONAL | Top-level product component. Contains `productSemantics`, `payloads`, or both, and optionally `sources`; alternatively, `$ref` identifies an external complete semantics object. |
| **sources** | object | OPTIONAL | Named source systems shared by the descriptions. Each key is a source identifier, such as `enterpriseGlossary`. The object MUST contain at least one entry when present; no maximum number or key length is specified. |
| **productSemantics** | object or reference object | OPTIONAL | Semantic document describing the product as a whole. Uses the document fields or `$ref` to a complete description. Include `productSemantics`, `payloads`, or both. |
| **payloads** | object | OPTIONAL | Named payload semantic profiles. No maximum number or profile-name length is specified. Include `productSemantics`, `payloads`, or both. MUST include `default`; additional profiles MAY describe other payloads. Each value uses inline semantic document fields or a reference to an external semantic document or profile. |
| **$ref** | URI-reference | REQUIRED in a reference object | References an external semantics object, semantic document or complete product or payload profile. A reference object has no sibling fields. Minimum 1 character; no maximum length is specified. URI references follow [RFC 3986](https://www.rfc-editor.org/rfc/rfc3986.html); internal JSON Pointer fragments follow [RFC 6901](https://www.rfc-editor.org/rfc/rfc6901.html). |

### Semantic source fields

A source describes a system used to create or support a semantic description. It is not a list of all concepts or vocabularies, and it does not assert approval or conformance. Avoid credentials in metadata.

| Element name | Type | Options | Description |
|---|---|---|---|
| **name** | string | REQUIRED for each source system | Human-readable source system name, when `sources` is provided. Minimum 1 character; no maximum length is specified. |
| **type** | string | OPTIONAL | Extensible description of the system type, such as `vocabulary-service` or `semantic-repository`. Minimum 1 character; no maximum length is specified. |
| **url** | URI-reference | OPTIONAL | Location of a human-readable service or repository. URI-reference per [RFC 3986](https://www.rfc-editor.org/rfc/rfc3986.html); minimum 1 character, no maximum length specified. |
| **apiURL** | URI-reference | OPTIONAL | Machine-readable service endpoint. URI-reference per [RFC 3986](https://www.rfc-editor.org/rfc/rfc3986.html); minimum 1 character, no maximum length specified. |
| **description** | string | OPTIONAL | Explanation of the source system's role. Minimum 1 character; no maximum length is specified. |

### Semantic document fields

The following fields apply to both `semantics.productSemantics` and each named `semantics.payloads` profile. A standalone `$ref` may be used instead of these fields.

| Element name | Type | Options | Description |
|---|---|---|---|
| **version** | string | OPTIONAL | Version of this semantic document, distinct from the product, vocabulary and source-system versions. Minimum 1 character; no maximum length or versioning standard is specified. |
| **description** | string | OPTIONAL | Human-readable summary of the document. Minimum 1 character; no maximum length is specified. |
| **sources** | array of strings | OPTIONAL | At least one unique identifier defined in `product.semantics.sources`; each identifier has at least 1 character. No maximum list or identifier length is specified. |

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

For interfaces with multiple payloads, `bindings` identifies each applicable profile by API operation and, where needed, response status and media type. Each binding MUST include an `operationId` unique within the API specification and a `semantics` reference to one named profile under `#/product/semantics/payloads/`. The API specification remains the authority for the operation and response definitions.

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
| **bindings** | array | REQUIRED for multiple selectors | List of at least one operation-to-payload binding; no maximum number is specified. Each entry contains `operationId` and `semantics` and may include `status` and `mediaType`. |
| **operationId** | string | REQUIRED in each access binding | Identifier of an operation in the interface's API specification. Minimum 1 character; no maximum length is specified. |
| **status** | string | OPTIONAL | Three-digit HTTP status in the range `100`–`599`, or `default` for the response named `default` in the API specification. HTTP status codes are defined by [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html#section-15). |
| **mediaType** | string | OPTIONAL | Media type of the response representation, such as `application/json`; see [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html#section-8.3). Minimum 1 character; no maximum length is specified. The schema does not validate media-type syntax. |
| **semantics** (binding) | reference object | REQUIRED in each access binding | Reference to one named semantic payload profile. |

An omitted `status` or `mediaType` selects all values of that dimension. Bindings for the same operation MUST NOT overlap: for example, a binding without `status` overlaps one for `'200'`. A profile that applies to several responses must describe each covered payload. Unlisted operations and responses make no semantic claim. Escape `~` as `~0` and `/` as `~1` in profile names used in JSON Pointer references.

## Reference resolution and validation

Resolve each relative `$ref` URI against the document containing it. Fragments in references to ODPS objects use JSON Pointer into the referenced or containing document. Resolution MUST detect cycles and preserve the base URI of each loaded document.

Data Access bindings are resolved against the **effective product document** after an external `product.semantics` object is loaded. Thus `#/product/semantics/payloads/default` targets the same effective location whether the semantics object is inline or external. Source names in external profiles are checked against that effective semantics object's `sources`.

A direct reference to a semantic document has no sibling fields: its format and other metadata must be determined from the referenced artifact or its transport. Use a referenced ODPS profile with `format`, `spec` and optional metadata when those details must be carried in ODPS. Structural validation does not require network access. When checked, malformed references, missing local files and unknown source names are errors. Unsupported formats, unavailable parsers and unreachable remote resources are reported as not checked or unresolved. Syntax validity does not establish semantic correctness, approval or conformance. Validation against the API specification is a separate check.

Include local semantic documents and profile files when creating a portable package, preserving or consistently rewriting relative paths. Identify unresolved external dependencies. The schema does not require a particular vocabulary service, RDF format, data contract or generation tool. The existing `product.details.<language>.standards` field retains its existing meaning and is not a conformity assertion.
