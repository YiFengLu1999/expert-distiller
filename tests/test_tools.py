import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


corpus = module("corpus", ROOT / "skills/expert-distiller/scripts/corpus.py")
installer = module("installer", ROOT / "scripts/install.py")


class ToolsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.example = self.base / "workshop-expert"
        shutil.copytree(ROOT / "examples/workshop-expert", self.example)

    def test_example_integrity(self):
        self.assertEqual(corpus.validate(self.example), [])

    def test_changed_chunk_is_detected(self):
        path = self.example / "references/corpus.json"
        data = corpus.read_json(path)
        data["chunks"][0]["text"] += "tampered"
        path.write_text(json.dumps(data))
        self.assertTrue(any("Changed chunk" in e for e in corpus.validate(self.example)))

    def test_wrong_quote_and_unknown_citation_are_detected(self):
        path = self.example / "references/knowledge.json"
        data = corpus.read_json(path)
        data["rules"][0]["evidence"][0]["quote"] = "虚构的逐字引文"
        data["rules"][1]["evidence"][0]["chunk_id"] = "missing"
        path.write_text(json.dumps(data))
        errors = corpus.validate(self.example)
        self.assertTrue(any("quote not found" in e for e in errors))
        self.assertTrue(any("unknown evidence" in e for e in errors))

    def test_inference_requires_rationale(self):
        path = self.example / "references/knowledge.json"
        data = corpus.read_json(path)
        del data["rules"][-1]["rationale"]
        path.write_text(json.dumps(data))
        self.assertTrue(any("rationale" in e for e in corpus.validate(self.example)))

    def test_chunking_keeps_long_lines_and_stable_ids(self):
        path = self.base / "book.md"
        text = "first\n" + "材料证据" * 300 + "\nlast"
        path.write_text(text)
        result = corpus.make_corpus([path], 100)
        self.assertEqual("".join(c["text"] for c in result["chunks"]), text)
        self.assertTrue(all(len(c["text"]) <= 100 for c in result["chunks"]))
        self.assertEqual(result, corpus.make_corpus([path], 100))
        self.assertEqual(len(corpus.make_corpus([path, path])["sources"]), 1)

    def test_chinese_english_search_and_no_hit(self):
        data = {"chunks": [{"id": "a", "text": "满意度不能单独证明技能"},
                           {"id": "b", "text": "Independent practice improves observability"}]}
        self.assertEqual(corpus.search(data, "满意度")[0]["id"], "a")
        self.assertEqual(corpus.search(data, "INDEPENDENT")[0]["id"], "b")
        self.assertEqual(corpus.search(data, "galaxy"), [])

    def test_empty_and_unsupported_inputs_fail(self):
        path = self.base / "empty.md"
        path.write_text(" \n")
        with self.assertRaises(ValueError):
            corpus.make_corpus([path])
        path = self.base / "book.epub"
        path.write_bytes(b"not an epub")
        with self.assertRaises(ValueError):
            corpus.make_corpus([path])

    def test_cli_never_overwrites_corpus(self):
        out = self.base / "protected.json"
        out.write_text("keep me")
        script = ROOT / "skills/expert-distiller/scripts/corpus.py"
        result = subprocess.run([sys.executable, str(script), "ingest", str(ROOT / "examples/workshop-notes.md"), "--out", str(out)], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(out.read_text(), "keep me")

    def test_install_is_portable_and_preserves_existing(self):
        target = installer.install(self.example, self.base / "installed")
        shutil.rmtree(self.example)
        run = subprocess.run([sys.executable, str(target / "scripts/corpus.py"), "search", str(target / "references/corpus.json"), "满意度"], cwd=self.base, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertTrue(json.loads(run.stdout))
        with self.assertRaises(FileExistsError):
            installer.install(ROOT / "examples/workshop-expert", self.base / "installed")
        self.assertEqual(corpus.validate(target), [])

    def test_install_rejects_recursive_destination_and_symlinks(self):
        with self.assertRaises(ValueError):
            installer.install(self.example, self.example / "child")
        (self.example / "outside").symlink_to(ROOT / "README.md")
        with self.assertRaises(ValueError):
            installer.install(self.example, self.base / "installed")


if __name__ == "__main__":
    unittest.main()
