from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Sequence


@dataclass(frozen=True)
class RealmCoinSpec:
    realm_id: str
    currency_code: str
    currency_name: str
    backing: str


@dataclass(frozen=True)
class RealmMarketSpec:
    realm_id: str
    market_id: str
    display_name: str
    volatility_bp: int
    spread_bp: int
    fee_bp: int
    stock: Mapping[str, int]


REALM_COINS: Dict[str, RealmCoinSpec] = {
    "lapidus": RealmCoinSpec("lapidus", "LAP", "Lapidus Silver Coin", "Silver"),
    "mercurie": RealmCoinSpec("mercurie", "MER", "Mercurie Water Mark", "Water"),
    "sulphera": RealmCoinSpec("sulphera", "SUL", "Sulphera Despair Shard", "Despair"),
}

REALM_MARKETS: Dict[str, RealmMarketSpec] = {
    "lapidus": RealmMarketSpec(
        realm_id="lapidus",
        market_id="lapidus_exchange",
        display_name="Lapidus Exchange",
        volatility_bp=120,
        spread_bp=80,
        fee_bp=45,
        stock={"iron_ingot": 1200, "herb": 900, "water": 1500},
    ),
    "mercurie": RealmMarketSpec(
        realm_id="mercurie",
        market_id="mercurie_tide_market",
        display_name="Mercurie Tide Market",
        volatility_bp=260,
        spread_bp=120,
        fee_bp=60,
        stock={"iron_ingot": 220, "herb": 1800, "water": 3200},
    ),
    "sulphera": RealmMarketSpec(
        realm_id="sulphera",
        market_id="sulphera_royal_bazaar",
        display_name="Sulphera Royal Bazaar",
        volatility_bp=420,
        spread_bp=180,
        fee_bp=90,
        stock={"iron_ingot": 450, "herb": 140, "water": 80},
    ),
}


def normalize_realm_id(realm_id: str) -> str:
    normalized = (realm_id or "").strip().lower() or "lapidus"
    if normalized not in REALM_COINS:
        raise ValueError("unknown_realm_market")
    return normalized


def get_realm_coin(realm_id: str) -> RealmCoinSpec:
    return REALM_COINS[normalize_realm_id(realm_id)]


def list_realm_coins(realm_id: str | None = None) -> Sequence[RealmCoinSpec]:
    if realm_id is not None and realm_id.strip() != "":
        return [get_realm_coin(realm_id)]
    return [REALM_COINS[key] for key in sorted(REALM_COINS.keys())]


def get_realm_market(realm_id: str) -> RealmMarketSpec:
    return REALM_MARKETS[normalize_realm_id(realm_id)]


def list_realm_markets(realm_id: str | None = None) -> Sequence[RealmMarketSpec]:
    if realm_id is not None and realm_id.strip() != "":
        return [get_realm_market(realm_id)]
    return [REALM_MARKETS[key] for key in sorted(REALM_MARKETS.keys())]
