import pytest
from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_app_modules_import():
    import importlib
    for m in ["src.analytics.metrics", "src.analytics.kpis", "src.process_mining.analysis", "src.simulation.model", "src.reporting.recommendations", "src.data.validation"]:
        importlib.import_module(m)


def test_app_all_pages_render_without_exception():
    if not (ROOT / "data/processed/pharmaflow.db").exists():
        pytest.fail("Database missing: run `python scripts/generate_data.py` (or bash scripts/run_pipeline.sh) first.")
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=240).run()
    assert not at.exception
    for name in list(at.sidebar.radio[0].options):
        at.sidebar.radio[0].set_value(name).run()
        assert not at.exception, f"{name}: {[e.value for e in at.exception]}"


def test_simulator_controls_change_results():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=240).run()
    at.sidebar.radio[0].set_value("Scenario Simulator").run()
    before = [d.value.copy() for d in at.dataframe][0]
    key = [s for s in at.slider if "demand_growth" in str(s.key)][0]
    key.set_value(0.5).run()
    after = [d.value.copy() for d in at.dataframe][0]
    assert not before.equals(after)
