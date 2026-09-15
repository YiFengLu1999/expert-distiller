#!/usr/bin/env python3
"""Local corpus preparation and structural evidence checks; no model or network calls."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def extract(path):
    if path.suffix.lower() in {".txt", ".md", ".markdown"}:
        return [("text", path.read_text(encoding="utf-8-sig"))]
    if path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ValueError("PDF requires optional pypdf; install it or convert to UTF-8 Markdown.") from exc
        reader = PdfReader(str(path))
        return [(f"PDF file page {n}", page.extract_text() or "")
                for n, page in enumerate(reader.pages, 1)]
    raise ValueError(f"Unsupported format: {path.suffix}. Convert to UTF-8 Markdown with source mapping.")


def make_corpus(paths, chunk_chars=2400):
    if chunk_chars < 100:
        raise ValueError("chunk_chars must be at least 100")
    sources, chunks, seen = [], [], set()
    for value in paths:
        path = Path(value)
        sha = digest(path.read_bytes())
        if sha in seen:
            continue
        seen.add(sha)
        sid = "S" + sha[:16]
        units = extract(path)
        source = {"id": sid, "filename": path.name, "sha256": sha,
                  "format": path.suffix.lower(), "empty_units": []}
        for location, body in units:
            if not body.strip():
                source["empty_units"].append(location)
                continue
            # Fixed character windows bound even very long single lines.
            for start in range(0, len(body), chunk_chars):
                content = body[start:start + chunk_chars]
                if not content.strip():
                    continue
                line_start = body.count("\n", 0, start) + 1
                line_end = line_start + content.count("\n")
                locator = f"{location}; lines {line_start}-{line_end}; chars {start + 1}-{start + len(content)}"
                cid = sid + "-" + digest((locator + "\0" + content).encode())[:12]
                chunks.append({"id": cid, "source_id": sid, "locator": locator,
                               "text": content, "sha256": digest(content.encode())})
        sources.append(source)
    if not chunks:
        raise ValueError("No readable text. Check encoding, encryption or OCR; no corpus written.")
    return {"schema_version": 1, "chunk_chars": chunk_chars,
            "sources": sources, "chunks": chunks}


def terms(text):
    latin = re.findall(r"[a-z0-9]+", text.lower())
    chinese = re.findall(r"[\u3400-\u9fff]+", text)
    return set(latin + [run[i:i+2] for run in chinese for i in range(max(1, len(run)-1))])


def search(corpus, query, limit=5):
    query_terms = terms(query)
    hits = []
    for chunk in corpus["chunks"]:
        score = len(query_terms & terms(chunk["text"]))
        if score:
            hits.append({"score": score, **chunk})
    return sorted(hits, key=lambda c: (-c["score"], c["id"]))[:limit]


def validate(folder):
    folder = Path(folder)
    errors = []
    for required in ("SKILL.md", "scripts/corpus.py", "references/reasoning.md",
                     "references/coverage.md", "references/evaluations.md"):
        if not (folder / required).is_file():
            errors.append(f"Missing {required}")
    skill = folder / "SKILL.md"
    if skill.is_file():
        text = skill.read_text(encoding="utf-8")
        if "{{" in text:
            errors.append("Unfilled skill template")
        front = text.split("---", 2)
        if not text.startswith("---\n") or len(front) < 3:
            errors.append("Missing YAML frontmatter")
        else:
            match = re.search(r"^name: *([a-z0-9-]+) *$", front[1], re.M)
            if not match or match[1] != folder.name or len(match[1]) > 64:
                errors.append("Invalid or mismatched skill name")
            if not re.search(r"^description: *\S", front[1], re.M):
                errors.append("Missing description")
    corpus = read_json(folder / "references/corpus.json")
    knowledge = read_json(folder / "references/knowledge.json")
    if corpus.get("schema_version") != 1:
        errors.append("Unsupported corpus schema")
    sources = {s["id"]: s for s in corpus["sources"]}
    chunks = {c["id"]: c for c in corpus["chunks"]}
    if not sources or not chunks:
        errors.append("Empty corpus")
    if len(sources) != len(corpus["sources"]):
        errors.append("Duplicate source ID")
    if len(chunks) != len(corpus["chunks"]):
        errors.append("Duplicate chunk ID")
    for source in sources.values():
        sha = source.get("sha256", "")
        if not re.fullmatch(r"[0-9a-f]{64}", sha) or source["id"] != "S" + sha[:16]:
            errors.append(f"Invalid source hash: {source['id']}")
    for chunk in chunks.values():
        expected = chunk["source_id"] + "-" + digest((chunk["locator"] + "\0" + chunk["text"]).encode())[:12]
        if chunk["source_id"] not in sources:
            errors.append(f"Unknown source: {chunk['id']}")
        if chunk["sha256"] != digest(chunk["text"].encode()) or chunk["id"] != expected:
            errors.append(f"Changed chunk content or locator: {chunk['id']}")
    rules = knowledge.get("rules", [])
    if not rules:
        errors.append("No evidence-backed rules")
    ids = set()
    for rule in rules:
        rid = rule.get("id", "")
        if not rid or rid in ids:
            errors.append(f"Missing/duplicate rule ID: {rid}")
        ids.add(rid)
        for field in ("claim", "when", "action", "limits"):
            if not isinstance(rule.get(field), str) or not rule[field].strip():
                errors.append(f"{rid}: missing {field}")
        questions = rule.get("questions")
        if not isinstance(questions, list) or not questions or not all(isinstance(q, str) and q.strip() for q in questions):
            errors.append(f"{rid}: missing questions")
        if rule.get("kind") not in {"source", "inference"}:
            errors.append(f"{rid}: invalid kind")
        if rule.get("kind") == "inference" and not str(rule.get("rationale", "")).strip():
            errors.append(f"{rid}: missing inference rationale")
        if not rule.get("evidence"):
            errors.append(f"{rid}: missing evidence")
        for evidence in rule.get("evidence", []):
            chunk = chunks.get(evidence.get("chunk_id"))
            quote = evidence.get("quote", "")
            if chunk is None:
                errors.append(f"{rid}: unknown evidence chunk")
            elif not isinstance(quote, str) or not quote.strip() or quote not in chunk["text"]:
                errors.append(f"{rid}: quote not found in cited chunk")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("ingest")
    p.add_argument("files", nargs="+")
    p.add_argument("--out", required=True)
    p.add_argument("--chunk-chars", type=int, default=2400)
    p = sub.add_parser("search")
    p.add_argument("corpus")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=5)
    p = sub.add_parser("show")
    p.add_argument("corpus")
    p.add_argument("chunk_id")
    p = sub.add_parser("validate")
    p.add_argument("folder")
    args = parser.parse_args()
    try:
        if args.command == "ingest":
            corpus = make_corpus(args.files, args.chunk_chars)
            dest = Path(args.out)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("x", encoding="utf-8") as handle:
                json.dump(corpus, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            print(f"Created {len(corpus['sources'])} sources, {len(corpus['chunks'])} chunks. Reading coverage is not yet assessed.")
        elif args.command in {"search", "show"}:
            corpus = read_json(args.corpus)
            if args.command == "search":
                if args.limit < 1:
                    raise ValueError("limit must be positive")
                result = search(corpus, args.query, args.limit)
            else:
                result = [c for c in corpus["chunks"] if c["id"] == args.chunk_id]
                if not result:
                    raise ValueError("Unknown chunk ID")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            errors = validate(args.folder)
            print(json.dumps({"passed": not errors, "errors": errors,
                              "scope": "Structural checks only; semantic support and behavior need review."}, ensure_ascii=False, indent=2))
            return int(bool(errors))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
