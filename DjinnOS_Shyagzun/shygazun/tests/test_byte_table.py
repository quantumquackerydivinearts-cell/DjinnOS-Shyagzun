from __future__ import annotations

from shygazun.kernel.constants.byte_table import (
    SHYGAZUN_BYTE_ORDER,
    SHYGAZUN_BYTE_ROWS,
    SHYGAZUN_BYTE_TABLE,
    byte_entry,
    byte_rows,
    byte_table_snapshot,
    symbol_entry,
    symbol_entries,
    tongue_rows,
    tongues,
)


def test_byte_row_count_and_gaps() -> None:
    assert len(SHYGAZUN_BYTE_ROWS) == 210
    assert 124 not in SHYGAZUN_BYTE_TABLE
    assert 125 not in SHYGAZUN_BYTE_TABLE
    assert 126 not in SHYGAZUN_BYTE_TABLE
    assert 127 not in SHYGAZUN_BYTE_TABLE


def test_first_and_last_rows_locked() -> None:
    first = byte_entry(0)
    assert first["binary"] == "00000000"
    assert first["tongue"] == "Lotus"
    assert first["symbol"] == "Ty"
    assert first["meaning"] == "Earth Initiator / material beginning"

    last = byte_entry(213)
    assert last["binary"] == "11010101"
    assert last["tongue"] == "Cannabis"
    assert last["symbol"] == "Suy"
    assert last["meaning"] == "Conscious temporal action / the act of mind deliberately moving through or shaping time"


def test_commas_in_meaning_are_preserved() -> None:
    zhuk = symbol_entry("Zhuk")
    assert zhuk["meaning"] == "Plasma (Fire,Fire)"


def test_order_is_decimal_ascending() -> None:
    assert SHYGAZUN_BYTE_ORDER[0] == 0
    assert SHYGAZUN_BYTE_ORDER[-1] == 213
    assert SHYGAZUN_BYTE_ORDER.index(123) < SHYGAZUN_BYTE_ORDER.index(128)


def test_snapshot_is_copy() -> None:
    snapshot = dict(byte_table_snapshot())
    snapshot[0] = {
        "decimal": 0,
        "binary": "11111111",
        "tongue": "Lotus",
        "symbol": "Ty",
        "meaning": "tampered",
    }
    assert byte_entry(0)["binary"] == "00000000"


def test_rows_accessor_is_stable() -> None:
    rows = byte_rows()
    assert rows[24]["tongue"] == "Rose"
    assert rows[24]["symbol"] == "Ru"


def test_tongue_grouping_is_stable() -> None:
    tongue_set = set(tongues())
    assert tongue_set == {
        "Lotus",
        "Rose",
        "Sakura",
        "Daisy",
        "AppleBlossom",
        "Aster",
        "Grapevine",
        "Cannabis",
    }
    lotus = tongue_rows("Lotus")
    assert lotus[0]["decimal"] == 0
    assert lotus[-1]["decimal"] == 23


def test_symbol_entries_preserve_declensional_surface() -> None:
    entries = symbol_entries("Ty")
    assert len(entries) == 1
    assert entries[0]["tongue"] == "Lotus"
