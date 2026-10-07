import pytest

from src.lib.transform.mapper import nested_map


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param("", {}, id="empty-string"),
        pytest.param(None, {}, id="null"),
        pytest.param(" \t\n", {}, id="whitespace"),
        pytest.param(", ,", {}, id="delimiters-only"),
        pytest.param(
            "English,Spanish",
            {"languages": [{"name": "English"}, {"name": "Spanish"}]},
            id="languages",
        ),
        pytest.param(0, {"languages": [0]}, id="zero"),
        pytest.param(False, {"languages": [False]}, id="false"),
    ],
)
def test_split_array_omits_blank_values_and_preserves_nonblank_values(value, expected):
    mapping = {"languages": [{"name": {"path": "s.languages", "split": ","}}]}

    assert nested_map({"s": {"languages": value}}, mapping) == expected


@pytest.mark.parametrize("transformed", [None, "", " \t", [], {}])
def test_split_array_omits_blank_transform_results(transformed):
    class Registry:
        def get_transform(self, name):
            assert name == "blank"
            return lambda value: transformed

    mapping = {
        "languages": [
            {"name": {"path": "s.languages", "split": ",", "transform": "blank"}}
        ]
    }

    assert nested_map(
        {"s": {"languages": "English,Spanish"}}, mapping, transreg=Registry()
    ) == {}
