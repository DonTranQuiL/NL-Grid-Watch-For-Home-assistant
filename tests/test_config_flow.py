"""Unit tests for postal-code helpers."""

from custom_components.nl_grid_watch.config_flow import normalize_postal_code


def test_normalize_postal_code_strips_spaces():
    assert normalize_postal_code("1012 js") == "1012JS"
    assert normalize_postal_code("1012JS") == "1012JS"
    assert normalize_postal_code(" 6211 aa ") == "6211AA"
