from __future__ import annotations

import ast
from pathlib import Path

from django.test import SimpleTestCase


class CoreAgentImportBoundaryTests(SimpleTestCase):
    def test_core_agent_imports_only_core_and_core_agent_modules(self):
        root = Path(__file__).resolve().parents[1]
        python_files = [
            path
            for path in root.rglob("*.py")
            if path.name != "__init__.py" and "tests" not in path.parts
        ]

        forbidden_imports: list[tuple[str, str]] = []

        for python_file in python_files:
            tree = ast.parse(python_file.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("apps."):
                    if not (
                        node.module.startswith("apps.core.")
                        or node.module == "apps.core"
                        or node.module.startswith("apps.core_agent.")
                        or node.module == "apps.core_agent"
                    ):
                        forbidden_imports.append((python_file.name, node.module))

        self.assertEqual(forbidden_imports, [])
