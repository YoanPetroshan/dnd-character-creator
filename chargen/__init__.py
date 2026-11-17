"""chargen: what is left of the first-generation engine, the data side only.

The SRD JSON datasets (`chargen/data/srd/`, read by `server/catalog/loader.py`), the data paths (`chargen.sources`) and the
refresh tool for the official data (`python -m chargen.sync`). The rules engine that once lived here was removed (audit
MAINT-02, slice S18): the app's engine is `server/engine/`.
"""
