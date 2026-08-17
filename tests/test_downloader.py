from pathlib import Path

import main
from downloader import DOWNLOADS, missing_files


def test_four_files_are_declared():
    names = {spec.filename for spec in DOWNLOADS}

    assert "Lexique383.tsv" in names
    assert "frWiki_no_phrase_no_postag_1000_skip_cut200.bin" in names
    assert "XMLittre.dict.dz" in names
    assert "XMLittre.idx" in names


def test_download_shares_sum_to_one_hundred():
    assert sum(spec.share for spec in DOWNLOADS) == 100


def test_missing_files_lists_absent_ones(tmp_path):
    (tmp_path / "Lexique383.tsv").write_text("x")

    missing = missing_files(tmp_path)

    assert "Lexique383.tsv" not in missing
    assert "frWiki_no_phrase_no_postag_1000_skip_cut200.bin" in missing


def test_data_dir_migrates_orquantix_to_procrastinator(tmp_path, monkeypatch):
    support = tmp_path / "Library" / "Application Support"
    legacy = support / "Orquantix"
    legacy.mkdir(parents=True)
    (legacy / "Lexique383.tsv").write_text("données")

    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    result = main.get_data_dir()

    assert result.name == "Procrastinator"
    assert (result / "Lexique383.tsv").read_text() == "données"
    assert not legacy.exists()


def test_data_dir_prefers_existing_procrastinator(tmp_path, monkeypatch):
    support = tmp_path / "Library" / "Application Support"
    (support / "Procrastinator").mkdir(parents=True)
    (support / "Orquantix").mkdir(parents=True)

    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    assert main.get_data_dir().name == "Procrastinator"


def test_data_dir_migrates_semantix_to_procrastinator(tmp_path, monkeypatch):
    support = tmp_path / "Library" / "Application Support"
    legacy = support / "Semantix"
    legacy.mkdir(parents=True)
    (legacy / "Lexique383.tsv").write_text("données")

    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    result = main.get_data_dir()

    assert result.name == "Procrastinator"
    assert (result / "Lexique383.tsv").read_text() == "données"
    assert not legacy.exists()


def test_data_dir_fresh_install_has_no_legacy_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    result = main.get_data_dir()

    assert result.name == "Procrastinator"
    assert not result.exists()


def test_data_dir_returns_legacy_path_when_rename_is_refused(tmp_path, monkeypatch):
    support = tmp_path / "Library" / "Application Support"
    legacy = support / "Orquantix"
    legacy.mkdir(parents=True)

    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    def refuse_rename(self, target):
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "rename", refuse_rename)

    result = main.get_data_dir()

    assert result == legacy
    assert legacy.exists()
