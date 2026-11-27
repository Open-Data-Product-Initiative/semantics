#!/usr/bin/env python3
"""Prepare a 4.3 development site in a disposable checkout for Middleman."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'source'
DRAFT = ROOT / 'drafts/semantics'
index = SOURCE / 'index.html.md'
text = index.read_text(encoding='utf-8')
text = text.replace('title: Open Data Product Specification 4.2 | Linux Foundation', 'title: Open Data Product Specification 4.3 Development version | Linux Foundation')
text = text.replace('  - contributors\n', '  - contributors\n  - semantics\n', 1)
text = text.replace('content: ODPS 4.2 is the final specification for interoperable, machine-readable data product metadata.', 'content: ODPS 4.3 development version; an unreleased draft based on ODPS 4.2.')
text = text.replace('## Version 4.2\n\n> **Final release.** ODPS 4.2 defines the stable schemas, examples, migration guidance, and conformance fixtures for this version of the specification.', '## Version 4.3 — Development version\n\n> **Development version — not a released standard.** This draft builds on the released ODPS 4.2 specification and adds a proposed semantics object. Its schema, examples and requirements may change. [View the released 4.2 specification](https://opendataproducts.org/v4.2/).')
text = text.replace('https://opendataproducts.org/v4.2/schema/odps.yaml', 'schema/odps.yaml').replace('https://opendataproducts.org/v4.2/schema/odps.json', 'schema/odps.json')
text = text.replace('Machine-readable ODPS 4.2 schema definition', 'Unreleased ODPS 4.3 development schema definition')
index.write_text(text, encoding='utf-8')
layout = SOURCE / 'layouts/layout.erb'
text = layout.read_text(encoding='utf-8').replace('Open Data Product Specification 4.2', 'Open Data Product Specification 4.3 Development version').replace('ODPS 4.2 is the final specification for interoperable, machine-readable data product metadata.', 'ODPS 4.3 development version; not a released standard.').replace('https://opendataproducts.org/v4.2"', 'https://opendataproducts.org/semantics/"')
layout.write_text(text, encoding='utf-8')
semantics = (DRAFT / 'README.md').read_text(encoding='utf-8')
semantics = semantics.replace('# ODPS 4.3 semantics specification — Development version', '# Semantics — ODPS 4.3 Development version').replace('(examples/product.yaml)', '(semantics-examples/product.yaml)')
(SOURCE / 'includes/_semantics.md').write_text(semantics, encoding='utf-8')
for name in ('odps.json', 'odps.yaml'):
    shutil.copyfile(DRAFT / 'schema' / name, SOURCE / 'schema' / name)
shutil.copytree(DRAFT / 'examples', SOURCE / 'semantics-examples', dirs_exist_ok=True)
