"""Public surface is importable and stable."""
import pyerowid


def test_version():
    assert isinstance(pyerowid.__version__, str)


def test_exports():
    for name in [
        "Experience", "Report", "SubstanceInfo", "SubstanceListing", "DosageEntry",
        "Erowid", "Transport",
        "get_experience", "get_categories", "search_reports", "random_experience",
        "get_pharms", "get_chemicals", "get_plants", "get_herbs",
        "get_smarts", "get_animals", "parse_substance_page",
    ]:
        assert hasattr(pyerowid, name), name
