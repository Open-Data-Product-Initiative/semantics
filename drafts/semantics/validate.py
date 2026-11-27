#!/usr/bin/env python3
"""Validate the development envelope and local semantics references without network access."""
import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit
import yaml
from jsonschema import Draft202012Validator, FormatChecker

HERE = Path(__file__).resolve().parent
SCHEMA = json.loads((HERE / 'schema/odps.json').read_text())
FORMAT_CHECKER = FormatChecker()


@FORMAT_CHECKER.checks('uri-reference')
def valid_uri_reference(value):
    if not isinstance(value, str) or re.search(r'[\s\x00-\x1f\x7f]|%(?![0-9A-Fa-f]{2})', value):
        return False
    try:
        parsed = urlsplit(value)
        _ = parsed.hostname
        return True
    except ValueError:
        return False


def pointer(value, fragment):
    if not fragment:
        return value
    if not fragment.startswith('/'):
        raise ValueError('fragment must be a JSON Pointer')
    for part in fragment[1:].split('/'):
        if '~' in part and re.search(r'~(?![01])', part):
            raise ValueError('invalid JSON Pointer escape')
        part = part.replace('~1', '/').replace('~0', '~')
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def check(path):
    errors, unchecked = [], []
    path = path.resolve()
    def load(p):
        return yaml.safe_load(p.read_text(encoding='utf-8'))
    try:
        root = load(path)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [f'cannot read product: {exc}'], []
    def shape(value, name=None):
        schema = SCHEMA if name is None else {'$schema': SCHEMA['$schema'], '$defs': SCHEMA['$defs'], '$ref': '#/$defs/' + name}
        for e in Draft202012Validator(schema, format_checker=FORMAT_CHECKER).iter_errors(value):
            errors.append(f"schema {name or 'product'} /{'/'.join(map(str, e.absolute_path))}: {e.message}")
    shape(root)
    if errors:
        return errors, unchecked
    def resolve(value, base, document, stack=(), allow_artifact=False):
        while isinstance(value, dict) and set(value) == {'$ref'}:
            ref = value['$ref']
            parsed = urlsplit(ref)
            if parsed.scheme or parsed.netloc:
                unchecked.append(f'remote reference not checked: {ref}')
                return None, base, document
            target = (base.parent / unquote(parsed.path)).resolve() if parsed.path else base
            marker = (str(target), parsed.fragment)
            if marker in stack:
                errors.append(f'reference cycle: {ref}')
                return None, base, document
            if allow_artifact and parsed.path and target.suffix.lower() not in ('.yaml', '.yml', '.json'):
                if parsed.fragment:
                    errors.append(f'semantic artifact reference cannot have a fragment: {ref}')
                    return None, base, document
                try:
                    content = target.read_text(encoding='utf-8')
                except (OSError, UnicodeError) as exc:
                    errors.append(f'cannot read semantic artifact {ref}: {exc}')
                    return None, base, document
                fmt = {'.ttl': 'text/turtle', '.jsonld': 'application/ld+json'}.get(target.suffix.lower())
                return ('semantic-artifact', content, fmt, ref), target, document
            try:
                target_doc = document if target == base else load(target)
                value = pointer(target_doc, unquote(parsed.fragment))
                if allow_artifact and parsed.path and target.suffix.lower() in ('.yaml', '.yml', '.json'):
                    is_profile = isinstance(value, dict) and (set(value) == {'$ref'} or ('format' in value and set(value) <= {'format', 'spec', 'version', 'description', 'sources'}))
                    if not is_profile:
                        unchecked.append(f'cannot determine whether {ref} is a semantic document or ODPS profile; content not checked')
                        return None, target, target_doc
            except (OSError, ValueError, KeyError, IndexError, TypeError, yaml.YAMLError) as exc:
                errors.append(f'cannot resolve {ref}: {exc}')
                return None, base, document
            base, document, stack = target, target_doc, stack + (marker,)
        return value, base, document
    product = root.get('product', {})
    if 'semantics' not in product:
        access = product.get('dataAccess', {})
        if isinstance(access, dict) and any(isinstance(item, dict) and 'semantics' in item for item in access.values()):
            errors.append('dataAccess semantics binding requires product.semantics payloads')
        return errors, unchecked
    sem, sem_base, sem_doc = resolve(product['semantics'], path, root)
    if sem is None:
        return errors, unchecked
    shape(sem, 'SemanticObject')
    if errors:
        return errors, unchecked
    sources = sem.get('sources', {})
    profiles = sem.get('payloads', {})
    def parse_content(content, fmt, label):
        if fmt != "text/turtle":
            unchecked.append(f"{label}: content parsing not performed ({fmt})")
            return
        try:
            import rdflib
        except ImportError:
            unchecked.append(f"{label}: Turtle parser unavailable")
            return
        try:
            rdflib.Graph().parse(data=content, format="turtle")
        except Exception as exc:
            errors.append(f"{label}: invalid Turtle: {exc}")

    def document(value, base, container, label):
        value, base, container = resolve(value, base, container, allow_artifact=True)
        if value is None:
            return
        if isinstance(value, tuple) and value[0] == 'semantic-artifact':
            parse_content(value[1], value[2] or 'unknown', label)
            return
        previous_errors = len(errors)
        shape(value, 'SemanticDocument')
        if len(errors) != previous_errors or not isinstance(value, dict):
            return
        for source in value.get('sources', []):
            if source not in sources:
                errors.append(f'{label}: unknown source {source}')
        if 'spec' in value:
            parse_content(value['spec'], value['format'], label)
        else:
            unchecked.append(f'{label}: semantic content not provided')
    if 'productSemantics' in sem:
        document(sem['productSemantics'], sem_base, sem_doc, 'product semantics')
    for name, value in profiles.items():
        document(value, sem_base, sem_doc, f'payload {name}')
    access = product.get('dataAccess', {})
    if '$ref' in access:
        unchecked.append('external dataAccess package bindings not checked')
    else:
        for name, item in access.items():
            if '$ref' in item:
                unchecked.append(f'external dataAccess profile {name} bindings not checked')
                continue
            value = item.get('semantics')
            if not value:
                continue
            entries = [value] if '$ref' in value else value['bindings']
            if '$ref' not in value:
                unchecked.append(f'dataAccess {name}: operation selectors not checked against API specification')
            seen = set()
            for entry in entries:
                target = entry['$ref'] if '$ref' in entry else entry['semantics']['$ref']
                if '$ref' not in entry:
                    key = (entry['operationId'], entry.get('status'), entry.get('mediaType'))
                    for previous in seen:
                        if all(a == b or a is None or b is None for a, b in zip(key, previous)):
                            errors.append(f'dataAccess {name}: overlapping bindings {previous} and {key}')
                    seen.add(key)
                prefix = '#/product/semantics/payloads/'
                if not target.startswith(prefix):
                    errors.append(f'dataAccess {name}: binding must target a named payload profile')
                    continue
                try:
                    token = unquote(target[len(prefix):])
                    if '/' in token or re.search(r'~(?![01])', token):
                        raise ValueError('invalid profile pointer')
                    key = token.replace('~1', '/').replace('~0', '~')
                    if key not in profiles:
                        raise ValueError('profile not found')
                except ValueError as exc:
                    errors.append(f'dataAccess {name}: {target}: {exc}')
    return errors, unchecked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('product', type=Path)
    args = parser.parse_args()
    errors, unchecked = check(args.product)
    for message in errors:
        print('ERROR:', message)
    for message in unchecked:
        print('NOT CHECKED:', message)
    print('INVALID' if errors else ('ENVELOPE VALID; CHECKS INCOMPLETE' if unchecked else 'VALID'))
    return 1 if errors else 0

if __name__ == '__main__':
    sys.exit(main())
