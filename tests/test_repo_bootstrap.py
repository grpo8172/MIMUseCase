from pathlib import Path


def test_expected_seed_files_exist():
    assert Path("payloads/mim-demo-001.json").exists()
    assert Path("data/input/incidents.csv").exists()
    assert Path("data/kbas/kba_seed.json").exists()
