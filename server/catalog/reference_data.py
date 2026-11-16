"""Hand-kept rules facts and tables (the data that is not in the 5etools files).

Since slice S17 (audit MAINT-01) the tables live in `catalog/reference/` (one module per topic); this module re-exports
every name, including the private ones, with the last binding winning (as in the one big file it used to be), so
`catalog.reference_data.X` and the "catalog.reference_data:X" strings of DATA_OVERRIDES keep working.
"""
from __future__ import annotations

from .reference import core_tables, class_effects, species_tables, data_overrides, resource_tail_2024, resource_tail_2014, subclass_tail_2014_books, subclass_tail_2014_w8b, subclass_tail_2014_w8c, subclass_tail_2014_w8d, class_options, subclass_picks, species_weapons

for _module in (core_tables, class_effects, species_tables, data_overrides, resource_tail_2024, resource_tail_2014, subclass_tail_2014_books, subclass_tail_2014_w8b, subclass_tail_2014_w8c, subclass_tail_2014_w8d, class_options, subclass_picks, species_weapons,):
    globals().update({_k: _v for _k, _v in vars(_module).items() if not (_k.startswith("__") and _k.endswith("__"))})
del _module
