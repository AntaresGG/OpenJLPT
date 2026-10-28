import csv
import json
from pathlib import Path

import pytest

from openjlpt import find_word, get_grammar, get_vocab, query, search_vocab, search_grammar
from openjlpt._data import data_root


def test_nested_cached_values_are_read_only():
    word = find_word("食べる")
    before = list(word.meanings)
    with pytest.raises(TypeError):
        word.meanings.append("bad")
    with pytest.raises(TypeError):
        word.meanings[0] = "bad"
    with pytest.raises(TypeError):
        word.examples.clear()
    with pytest.raises(TypeError):
        word.zh["meanings"].append("bad")
    with pytest.raises(TypeError):
        word.zh.update({"status": "reviewed"})
    assert find_word("食べる").meanings == before
    assert find_word("食べる") is word


def test_chinese_lookup_and_fallback():
    assert search_vocab("肥皂")[0].word == "せっけん"
    assert search_vocab("接待")[0].word == "受付"
    assert search_vocab("eat")[0].word == "食べる"
    assert any(g.id == "te-oku" for g in search_grammar("事先"))
    assert len([v for v in get_vocab() if v.zh]) == 300
    assert len([g for g in get_grammar() if g.zh]) == 40
    assert all(e.zh['status'] == 'reviewed' and e.zh['review_method'] == 'ai' for e in [*get_vocab(), *get_grammar()] if e.zh)


def test_json_csv_sqlite_agree():
    root = Path(data_root())
    for kind, items in (("vocab", get_vocab()), ("grammar", get_grammar())):
        sql = {r["id"]: r for r in query(f"SELECT * FROM {kind}")}
        for level in ("n5", "n4", "n3", "n2", "n1"):
            with (root / "csv" / f"{kind}-{level}.csv").open(encoding="utf-8", newline="") as f:
                csv_rows = {r["id"]: r for r in csv.DictReader(f)}
            for item in (i for i in items if i.level.lower() == level):
                assert json.loads(sql[item.id]["zh"]) == item.zh if item.zh else sql[item.id]["zh"] is None
                expected = "; ".join(item.zh["meanings"]) if item.zh and item.zh["status"] != "stale" else ""
                assert csv_rows[item.id]["meanings_zh"] == expected
                if kind == "vocab":
                    assert json.loads(sql[item.id]["meanings"]) == item.meanings
                    assert csv_rows[item.id]["meanings"] == "; ".join(item.meanings)


def test_anki_chinese_and_source_attribution():
    pytest.importorskip("genanki")
    import importlib.util
    spec = importlib.util.spec_from_file_location("exports", Path(__file__).parents[1] / "scripts" / "build_exports.py")
    exports = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exports)
    word = next(v for v in json.loads((Path(data_root()) / "json/vocab/n5.json").read_text(encoding="utf-8")) if v["word"] == "せっけん")
    note = exports.vocab_note(word, {})
    assert "肥皂" in note.fields[4]
    assert note.fields[4] == "肥皂 / soap"
    word["zh"]["status"] = "stale"
    assert "肥皂" not in exports.vocab_note(word, {}).fields[4]
