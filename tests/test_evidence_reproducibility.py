"""Do not publish synthetic study JSON from an older execution model."""
import hashlib
import json
from pathlib import Path
import unittest

from queue_research.experiment import study
from queue_research.synthetic import generate

ROOT = Path(__file__).resolve().parents[1]


class ReproducibilityTests(unittest.TestCase):
    def test_committed_seed11_reports_match_current_code(self):
        for predictive, label in ((False, 'null'), (True, 'predictive')):
            with self.subTest(label=label):
                expected = json.loads((ROOT / f'evidence/synthetic-{label}-seed11.json').read_text())
                generated = study(generate(16000, 11, predictive=predictive),
                                  source=f'synthetic:{label}:seed=11', seed=11)
                self.assertEqual(expected, generated)

    def test_evidence_manifest_covers_all_audited_source(self):
        manifest = ROOT / 'evidence/SHA256SUMS'
        seen = set()
        for line in manifest.read_text().splitlines():
            digest, name = line.split('  ', 1)
            self.assertNotIn(name, seen, name)
            seen.add(name)
            file = ROOT / name
            self.assertTrue(file.is_file(), name)
            self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(), digest, name)
        # The manifest excludes itself to avoid a recursive digest, but it must
        # include every source/test file, including new audit code.
        for folder in ('src', 'tests', 'scripts', 'docs'):
            for file in (ROOT / folder).rglob('*'):
                if file.is_file() and file.suffix in ('.py', '.md'):
                    self.assertIn(str(file.relative_to(ROOT)), seen)


if __name__ == '__main__':
    unittest.main()
