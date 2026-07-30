"""Markdown corpus dumper — rendering and resumability (no network)."""
import os

from pyerowid import dataset
from pyerowid.parse import parse_experience, parse_page

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _read(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as fh:
        return fh.read()


def test_experience_markdown_front_matter():
    exp = parse_experience(_read("experience.html"), 1)
    md = dataset.experience_markdown(exp)
    assert md.startswith("---\n")
    assert "kind: experience" in md
    assert "exp_id: 1" in md
    assert "# An Unforgettable Ride!" in md
    assert "## Report" in md
    assert "## Dosage" in md
    assert "| oral |" in md
    assert exp.text.split("\n")[0][:30] in md


def test_substance_markdown():
    url = "https://erowid.org/pharms/acetaminophen/acetaminophen.shtml"
    info = parse_page(_read("substance.html"), url)
    md = dataset.substance_markdown(info)
    assert "kind: substance" in md
    assert "other_names:" in md
    assert "chem_name:" in md
    assert info.description.strip()[:20] in md


def test_yaml_scalar_quoting():
    assert dataset._yaml_scalar("plain") == "plain"
    assert dataset._yaml_scalar("has: colon").startswith('"')
    assert dataset._yaml_scalar("") == '""'


def test_dump_substances_resumable(tmp_path, monkeypatch):
    url = "https://erowid.org/pharms/acetaminophen/acetaminophen.shtml"
    info = parse_page(_read("substance.html"), url)
    listing = dataset.SubstanceListing(name="acetaminophen", url=url)

    calls = {"n": 0}

    def fake_parse(u, transport=None):
        calls["n"] += 1
        return info

    monkeypatch.setattr(dataset, "parse_substance_page", fake_parse)

    out = str(tmp_path)
    n1 = dataset.dump_substances(out, [listing], delay=0, verbose=False)
    assert n1 == 1
    assert os.path.exists(os.path.join(out, "substances", "acetaminophen.md"))
    # second run skips the already-written file (resumable)
    n2 = dataset.dump_substances(out, [listing], delay=0, verbose=False)
    assert n2 == 0
    assert calls["n"] == 1


def test_dump_experiences_skips_existing(tmp_path, monkeypatch):
    exp = parse_experience(_read("experience.html"), 1)

    calls = {"n": 0}

    def fake_get(exp_id, transport=None):
        calls["n"] += 1
        return exp

    monkeypatch.setattr(dataset, "get_experience", fake_get)

    out = str(tmp_path)
    assert dataset.dump_experiences(out, [1], delay=0, verbose=False) == 1
    assert dataset.dump_experiences(out, [1], delay=0, verbose=False) == 0
    assert calls["n"] == 1
