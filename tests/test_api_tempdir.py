from pathlib import Path

import pytest

from src.api import tempdir


def test_get_writable_temp_dir_prefers_env_var(monkeypatch, tmp_path: Path) -> None:
    custom_temp = tmp_path / "custom-temp-root"
    monkeypatch.setenv("HSDS_TMP_DIR", str(custom_temp))

    resolved = tempdir.get_writable_temp_dir()

    assert resolved == str(custom_temp)
    assert custom_temp.exists()
    assert custom_temp.is_dir()


def test_get_writable_temp_dir_falls_back_to_first_writable_candidate(
    monkeypatch, tmp_path: Path
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"

    monkeypatch.delenv("HSDS_TMP_DIR", raising=False)
    monkeypatch.setattr(tempdir, "_default_temp_candidates", lambda: [first, second])
    monkeypatch.setattr(tempdir, "_is_writable_dir", lambda p: p == second)

    resolved = tempdir.get_writable_temp_dir()

    assert resolved == str(second)


def test_get_writable_temp_dir_raises_when_no_candidates_writable(monkeypatch) -> None:
    monkeypatch.delenv("HSDS_TMP_DIR", raising=False)
    monkeypatch.setattr(tempdir, "_default_temp_candidates", lambda: [Path("/tmp/a"), Path("/tmp/b")])
    monkeypatch.setattr(tempdir, "_is_writable_dir", lambda _p: False)

    with pytest.raises(RuntimeError) as exc:
        tempdir.get_writable_temp_dir()

    assert "HSDS_TMP_DIR" in str(exc.value)
