"""{@scaledamage base|levels|per-level} shows the per-level amount, not the base dice (Fireball upcast said 8d6)."""
from catalog.official.spells import _strip_tags


def test_scaledamage_shows_per_level_amount():
    assert _strip_tags("increases by {@scaledamage 8d6|3-9|1d6} for each") == "increases by 1d6 for each"


def test_scaledice_display_text_wins():
    assert _strip_tags("{@scaledice 2d4|2-9|1d4|one extra die}") == "one extra die"
