import copy, sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data.db import load_config, build_database
from src.data.generator import generate


@pytest.fixture(scope="session")
def small_cfg():
    cfg = load_config()
    cfg = copy.deepcopy(cfg)
    cfg["data"].update(n_purchase_orders=150, n_customer_orders=400, n_production_requests=60, invalid_transitions=5, open_hold_rate=0.03)
    return cfg


@pytest.fixture(scope="session")
def tables(small_cfg):
    return generate(small_cfg)


@pytest.fixture(scope="session")
def db(tmp_path_factory, tables, small_cfg):
    import sqlite3
    p = tmp_path_factory.mktemp("db") / "t.db"
    build_database(tables, p)
    con = sqlite3.connect(p); con.execute("PRAGMA foreign_keys=ON")
    yield con
    con.close()
