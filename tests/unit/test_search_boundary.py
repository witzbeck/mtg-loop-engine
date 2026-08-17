"""Search must not leak into the verifier module."""

import mtg_loop_engine.verify.verifier as verifier_mod


def test_verifier_module_does_not_import_search():
    assert not any(
        name.startswith("mtg_loop_engine.search")
        for name in verifier_mod.__dict__.values()
        if isinstance(name, str)
    )
    assert "mtg_loop_engine.search" not in getattr(verifier_mod, "__name__", "")
    import sys

    # Imported modules from verifier's file should not include search.
    import inspect

    src = inspect.getsource(verifier_mod)
    assert "mtg_loop_engine.search" not in src
    assert "from mtg_loop_engine.search" not in src
    _ = sys
