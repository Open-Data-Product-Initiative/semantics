import copy
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('semantics_validate', HERE / 'validate.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class SemanticsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        shutil.copytree(HERE / 'examples', self.root / 'examples')
        self.path = self.root / 'examples/product.yaml'
        self.product = yaml.safe_load(self.path.read_text())
        self.sem_path = self.root / 'examples/semantics/semantics.yaml'
        self.sem = yaml.safe_load(self.sem_path.read_text())

    def tearDown(self):
        self.temp.cleanup()

    def check(self):
        self.path.write_text(yaml.safe_dump(self.product, sort_keys=False))
        self.sem_path.write_text(yaml.safe_dump(self.sem, sort_keys=False))
        return validator.check(self.path)

    def test_example_resolves_external_semantics_and_profile(self):
        errors, unchecked = self.check()
        self.assertEqual(errors, [])
        self.assertTrue(any('operation selectors not checked' in x for x in unchecked))

    def test_schema_representations_match(self):
        self.assertEqual(json.loads((HERE / 'schema/odps.json').read_text()), yaml.safe_load((HERE / 'schema/odps.yaml').read_text()))

    def test_42_product_without_semantics_valid(self):
        base = yaml.safe_load((HERE.parents[1] / 'tests/fixtures/schema-conformance/valid-contract-access-target.yml').read_text())
        self.assertEqual(list(Draft202012Validator(validator.SCHEMA).iter_errors(base)), [])
        self.product = base
        self.assertEqual(self.check()[0], [])

    def test_product_only_and_single_binding(self):
        self.product['product'].pop('dataAccess')
        self.sem.pop('payloads')
        self.assertEqual(self.check()[0], [])
        self.sem['payloads'] = {'default': {'format': 'text/turtle', 'spec': '@prefix ex: <https://example.org/> .'}}
        self.product['product']['dataAccess'] = {'default': {'outputPortType': 'API', 'semantics': {'$ref': '#/product/semantics/payloads/default'}}}
        self.assertEqual(self.check()[0], [])

    def test_invalid_shapes(self):
        cases = [
            {'payloads': {'other': {'format': 'text/turtle', 'spec': 'x'}}},
            {'payloads': {'default': {'format': 'text/turtle', 'spec': 'x', 'file': 'x'}}},
            {'payloads': {'default': {'format': 'text/turtle', 'file': 'x'}}},
            {'sources': {'a': {'name': 'A'}}},
            {'product': {'format': 'text/turtle', 'spec': 'x'}},
            {'payloads': {'default': {'$ref': 'x', 'format': 'text/turtle'}}},
        ]
        for sem in cases:
            with self.subTest(sem=sem):
                self.sem = sem
                self.assertTrue(self.check()[0])

    def test_unknown_source_missing_artifact_and_target(self):
        self.sem['productSemantics']['sources'] = ['unknown']
        self.sem['payloads']['transactions']['$ref'] = 'missing.ttl'
        self.product['product']['dataAccess']['default']['semantics']['bindings'][0]['semantics']['$ref'] = '#/product/semantics/payloads/missing'
        errors, _ = self.check()
        for phrase in ('unknown source', 'cannot read semantic artifact', 'profile not found'):
            self.assertTrue(any(phrase in e for e in errors), errors)

    def test_spec_is_optional_and_content_not_checked(self):
        self.sem['productSemantics'].pop('spec')
        errors, unchecked = self.check()
        self.assertEqual(errors, [])
        self.assertTrue(any('semantic content not provided' in x for x in unchecked))

    def test_turtle_and_unsupported_format(self):
        self.sem['productSemantics']['spec'] = 'this is not Turtle ;'
        self.assertTrue(any('invalid Turtle' in e for e in self.check()[0]))
        self.sem['productSemantics']['format'] = 'application/json'
        errors, unchecked = self.check()
        self.assertEqual(errors, [])
        self.assertTrue(any('content parsing not performed' in x for x in unchecked))

    def test_format_options_are_enforced(self):
        for media_type in ('text/turtle', 'application/rdf+xml', 'application/ld+json',
                           'application/n-triples', 'application/trig', 'application/n-quads',
                           'application/json', 'application/yaml'):
            with self.subTest(media_type=media_type):
                self.sem['productSemantics']['format'] = media_type
                self.assertEqual(self.check()[0], [])
        self.sem['productSemantics']['format'] = 'application/example'
        self.assertTrue(self.check()[0])

    def test_direct_turtle_reference_and_malformed_turtle(self):
        self.assertEqual(self.check()[0], [])
        (self.root / 'examples/semantics/transactions.ttl').write_text('invalid turtle ;')
        self.assertTrue(any('invalid Turtle' in e for e in self.check()[0]))

    def test_json_and_yaml_artifact_references_report_not_checked(self):
        for extension, content in [('json', '{"concept": "Account"}'), ('yaml', 'concept: Account\n')]:
            with self.subTest(extension=extension):
                artifact = self.root / 'examples/semantics' / ('meaning.' + extension)
                artifact.write_text(content)
                self.sem['payloads']['transactions'] = {'$ref': './' + artifact.name}
                errors, unchecked = self.check()
                self.assertEqual(errors, [])
                self.assertTrue(any('content not checked' in x for x in unchecked))

    def test_cycle_and_unresolved_remote(self):
        profile = self.root / 'examples/semantics/account-profile.yaml'
        profile.write_text('$ref: ./account-profile.yaml\n')
        self.assertTrue(any('cycle' in e for e in self.check()[0]))
        self.sem['payloads']['default'] = {'$ref': 'https://example.org/profile.yaml'}
        errors, unchecked = self.check()
        self.assertEqual(errors, [])
        self.assertTrue(any('remote reference' in x for x in unchecked))

    def test_overlapping_operation_selectors_rejected(self):
        bindings = self.product['product']['dataAccess']['default']['semantics']['bindings']
        duplicate = copy.deepcopy(bindings[0])
        duplicate.pop('status')
        bindings.append(duplicate)
        self.assertTrue(any('overlapping' in e for e in self.check()[0]))

    def test_no_semantics_with_binding_fails(self):
        self.product['product'].pop('semantics')
        self.assertTrue(any('requires product.semantics' in e for e in self.check()[0]))

    def test_assessment_scores_and_optional_values(self):
        wrapper = {'artifact': {'$ref': './transactions.ttl'}, 'assessment': {}}
        self.sem['payloads']['transactions'] = wrapper
        self.assertEqual(self.check()[0], [])
        for field in ('overallScore', 'coverage', 'mappingConfidence', 'semanticCompleteness', 'consistency', 'traceability'):
            for value in (0, 100):
                with self.subTest(field=field, value=value):
                    wrapper['assessment'] = {field: value}
                    self.assertEqual(self.check()[0], [])
            for value in (-1, 101, 1.5, '50', None, True):
                with self.subTest(field=field, value=value):
                    wrapper['assessment'] = {field: value}
                    self.assertTrue(self.check()[0])
        wrapper.pop('assessment')
        self.assertEqual(self.check()[0], [])

    def test_assessment_structure_and_references(self):
        wrapper = {'artifact': {'$ref': './transactions.ttl'}, 'assessment': {}}
        self.sem['payloads']['transactions'] = wrapper
        for value in ('valid', 'invalid', 'notEvaluated'):
            wrapper['assessment'] = {'structuralValidity': value}
            self.assertEqual(self.check()[0], [])
        for assessment in ({'structuralValidity': 'unknown'}, {'structuralValidity': None},
                           {'assessedAt': 'yesterday'}, {'method': 'not a uri'},
                           {'report': {'$ref': 'report.json', 'description': 'bad'}},
                           {'reportUrl': 'report.json'}, {'unknown': 1}):
            with self.subTest(assessment=assessment):
                wrapper['assessment'] = assessment
                self.assertTrue(self.check()[0])
        wrapper['assessment'] = {'method': 'urn:example:method:1', 'assessedAt': '2026-11-28T10:00:00Z', 'report': {'$ref': 'report.json'}}
        self.assertEqual(self.check()[0], [])
        wrapper['artifact']['assessment'] = {}
        self.assertTrue(self.check()[0])
        self.sem['productSemantics']['assessment'] = {}
        self.assertTrue(self.check()[0])

    def test_assessment_external_wrapper_resolves_relative_artifact(self):
        profile = self.root / 'examples/semantics/assessed-profile.yaml'
        profile.write_text(yaml.safe_dump({'artifact': {'$ref': './transactions.ttl'}, 'artifactVersion': '1.0', 'assessment': {'coverage': 80}}))
        self.sem['payloads']['transactions'] = {'$ref': './assessed-profile.yaml'}
        self.assertEqual(self.check()[0], [])
        (self.root / 'examples/semantics/transactions.ttl').write_text('invalid turtle ;')
        self.assertTrue(any('invalid Turtle' in e for e in self.check()[0]))

    def test_assessment_inline_artifact_and_missing_artifact(self):
        self.sem['payloads']['transactions'] = {'artifact': {'format': 'text/turtle', 'version': '1', 'spec': '@prefix ex: <https://example.org/> .'}, 'assessment': {'coverage': 50}}
        self.assertEqual(self.check()[0], [])
        self.sem['payloads']['transactions']['artifactVersion'] = '2'
        self.assertTrue(any('artifactVersion does not match' in e for e in self.check()[0]))
        self.sem['payloads']['transactions']['artifactVersion'] = '1'
        self.assertEqual(self.check()[0], [])
        self.sem['payloads']['transactions'].pop('artifact')
        self.assertTrue(self.check()[0])


if __name__ == '__main__':
    unittest.main()
