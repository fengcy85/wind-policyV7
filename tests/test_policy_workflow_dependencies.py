"""Prevent optional Argos/PyTorch downloads from blocking mandatory policy runs."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class WorkflowDependencyTests(unittest.TestCase):
    def test_mandatory_requirements_do_not_include_translation_or_gpu(self):
        lines = (ROOT / 'requirements.txt').read_text(encoding='utf-8').splitlines()
        packages = [re.split(r'[<>=!~]', line, maxsplit=1)[0].strip().lower()
                    for line in lines if line.strip() and not line.lstrip().startswith('#')]
        for dep in ('argostranslate', 'stanza', 'torch', 'triton'):
            self.assertNotIn(dep, packages, f'{dep} must remain optional')
        self.assertIn('beautifulsoup4', packages)
        self.assertIn('playwright', packages)
        optional = (ROOT / 'requirements-translation.txt').read_text(encoding='utf-8')
        self.assertIn('argostranslate>=1.9,<2', optional)

    def test_offline_translation_is_cpu_only_and_nonblocking(self):
        text = (ROOT / '.github/workflows/update.yml').read_text(encoding='utf-8')
        install_step = text.split('      - name: Install optional CPU-only offline translation\n', 1)[1]
        optional_part, news_part = install_step.split('      - name: Refresh industry news and weekly focus\n', 1)
        self.assertIn('        id: install_translation\n', optional_part)
        self.assertIn('        continue-on-error: true\n', optional_part)
        self.assertIn('        timeout-minutes: 8\n', optional_part)
        self.assertIn('--index-url https://download.pytorch.org/whl/cpu', optional_part)
        self.assertIn("'torch==2.13.0'", optional_part)
        self.assertIn('-r requirements-translation.txt', optional_part)
        self.assertIn('torch.version.cuda is None', optional_part)
        self.assertIn("ENABLE_TRANSLATION: ${{ steps.install_translation.outcome == 'success' && '1' || '0' }}", news_part)
        mandatory_part = text.split('      - name: Install dependencies\n', 1)[1].split('      - name: Run offline backend and frontend tests\n', 1)[0]
        self.assertIn('-r requirements.txt', mandatory_part)
        self.assertNotIn('requirements-translation.txt', mandatory_part)


if __name__ == '__main__':
    unittest.main()
