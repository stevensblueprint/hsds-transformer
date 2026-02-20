from click.testing import CliRunner
from src.cli.maintenance import main
from pathlib import Path
from unittest.mock import patch

def test_generate_relations_command(tmp_path):
    # Mock the JSON schema response
    mock_schema = {
        "type": "object",
        "properties": {
            "organization": {
                "type": "object",
                "properties": {
                    "services": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "capacities": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "unit": {"type": "object"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    url = "https://raw.githubusercontent.com/test/schema.json"
    
    out_file = tmp_path / "relations.py"
    
    runner = CliRunner()
    with patch("src.cli.maintenance.fetch_json_from_url", return_value=mock_schema):
        result = runner.invoke(main, [
            "generate-relations",
            "--github-url", url,
            "--out-file", str(out_file)
        ])
    
    assert result.exit_code == 0
    assert out_file.exists()
    
    content = out_file.read_text()
    assert "HSDS_RELATIONS" in content
    assert '"service": [' in content
    assert '"service_capacity": [' in content
    assert '"unit": [' in content
