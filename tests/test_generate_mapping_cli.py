from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from src.cli import maintenance


def _sample_schema(name: str = "Organization") -> dict:
    return {
        "name": name,
        "type": "object",
        "required": ["id"],
        "properties": {
            "id": {"type": "string", "description": "Identifier"},
            "name": {"type": "string", "description": "Display name"},
        },
    }


def test_generate_mapping_writes_to_current_directory(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(maintenance, "fetch_json_from_url", lambda _url: _sample_schema())

    runner = CliRunner()
    result = runner.invoke(
        maintenance.main,
        [
            "generate-mapping",
            "--github-url",
            "https://raw.githubusercontent.com/org/repo/refs/heads/main/schema.json",
        ],
    )

    assert result.exit_code == 0
    out_file = tmp_path / "organization_mapping_template.csv"
    assert out_file.exists()
    contents = out_file.read_text(encoding="utf-8").splitlines()
    assert contents[0] == "path,input_files_field,split,strip,description,required"
    assert contents[1] == ",,,,,"


def test_generate_mapping_sanitizes_schema_name(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        maintenance,
        "fetch_json_from_url",
        lambda _url: _sample_schema("../../etc/passwd"),
    )

    runner = CliRunner()
    result = runner.invoke(
        maintenance.main,
        [
            "generate-mapping",
            "--github-url",
            "https://raw.githubusercontent.com/org/repo/refs/heads/main/schema.json",
        ],
    )

    assert result.exit_code == 0
    generated = list(tmp_path.glob("*_mapping_template.csv"))
    assert len(generated) == 1
    assert generated[0].parent.resolve() == tmp_path.resolve()


def test_generate_mapping_fails_for_empty_schema(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(maintenance, "fetch_json_from_url", lambda _url: {})

    runner = CliRunner()
    result = runner.invoke(
        maintenance.main,
        [
            "generate-mapping",
            "--github-url",
            "https://raw.githubusercontent.com/org/repo/refs/heads/main/schema.json",
        ],
    )

    assert result.exit_code != 0
    assert "Schema produced no mapping fields" in result.output


def test_generate_mapping_wraps_fetch_errors(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    def _raise(_url: str) -> dict:
        raise RuntimeError("boom")

    monkeypatch.setattr(maintenance, "fetch_json_from_url", _raise)

    runner = CliRunner()
    result = runner.invoke(
        maintenance.main,
        [
            "generate-mapping",
            "--github-url",
            "https://raw.githubusercontent.com/org/repo/refs/heads/main/schema.json",
        ],
    )

    assert result.exit_code != 0
    assert "Error: boom" in result.output
    assert "Traceback" not in result.output


def test_generate_mapping_refuses_to_overwrite_existing_file(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(maintenance, "fetch_json_from_url", lambda _url: _sample_schema())
    (tmp_path / "organization_mapping_template.csv").write_text("existing", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        maintenance.main,
        [
            "generate-mapping",
            "--github-url",
            "https://raw.githubusercontent.com/org/repo/refs/heads/main/schema.json",
        ],
    )

    assert result.exit_code != 0
    assert "Output file already exists" in result.output


def test_generate_mapping_accepts_allowed_host_with_port(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(maintenance, "fetch_json_from_url", lambda _url: _sample_schema())

    runner = CliRunner()
    result = runner.invoke(
        maintenance.main,
        [
            "generate-mapping",
            "--github-url",
            "https://raw.githubusercontent.com:443/org/repo/refs/heads/main/schema.json",
        ],
    )

    assert result.exit_code == 0


def test_generate_mapping_rejects_invalid_hostname(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(maintenance, "fetch_json_from_url", lambda _url: _sample_schema())

    runner = CliRunner()
    result = runner.invoke(
        maintenance.main,
        [
            "generate-mapping",
            "--github-url",
            "https://github.com.evil.com/org/repo/schema.json",
        ],
    )

    assert result.exit_code != 0
    assert "Invalid URL Provided" in result.output


def test_generate_mapping_wraps_flatten_errors(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(maintenance, "fetch_json_from_url", lambda _url: _sample_schema())

    def _raise(_schema: dict):
        raise ValueError("flatten failed")

    monkeypatch.setattr(maintenance, "flatten_schema", _raise)

    runner = CliRunner()
    result = runner.invoke(
        maintenance.main,
        [
            "generate-mapping",
            "--github-url",
            "https://raw.githubusercontent.com/org/repo/refs/heads/main/schema.json",
        ],
    )

    assert result.exit_code != 0
    assert "Error: flatten failed" in result.output


def test_generate_mapping_wraps_write_errors(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(maintenance, "fetch_json_from_url", lambda _url: _sample_schema())

    def _raise(_rows, _path):
        raise OSError("disk full")

    monkeypatch.setattr(maintenance, "write_mapping_template_csv", _raise)

    runner = CliRunner()
    result = runner.invoke(
        maintenance.main,
        [
            "generate-mapping",
            "--github-url",
            "https://raw.githubusercontent.com/org/repo/refs/heads/main/schema.json",
        ],
    )

    assert result.exit_code != 0
    assert "Error: disk full" in result.output
