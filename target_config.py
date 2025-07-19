#!/usr/bin/env python3
"""
КОНФИГУРАЦИЯ ЦЕЛЕВЫХ АДРЕСОВ
Список целей для тестирования эксплойтов
"""

from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class TradingPair:
    """Торговая пара токенов для тестирования"""
    token_a: str
    token_b: str
    description: str = ""
    pool_type: str = ""

# Торговые пары для тестирования эксплойтов
# token_a - пул ликвидности Raydium, token_b - контракт токена
TRADING_PAIRS = [
    TradingPair(
        token_a="J333LZ5UhEjwxb64dcD756viUFXr164dVNxQpXuMPH9V",  
        token_b="9wK8yN6iz1ie5kEJkvZCTxyN1x5sTdNfx8yeMY8Ebonk",  
        description="Raydium ликвидность пул с токеном",
        pool_type="raydium_amm"
    ),
    TradingPair(
        token_a="9d9mb8kooFfaD3SctgZtkxQypkshx6ezhbKio89ixyy2",
        token_b="6p6xgHyF7AeE6TZkSmFsko444wqoP15icUSqi2jfGiPN",
        description="Trading Pair 2"
    ),
    TradingPair(
        token_a="Bzc9NZfMqkXR6fz1DBph7BDf9BroyEf6pnzESP7v5iiw",
        token_b="9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump",
        description="Trading Pair 3"
    ),
    TradingPair(
        token_a="FRhB8L7Y9Qq41qZXYLtC2nw8An1RJfLLxRF2x9RwLLMo",
        token_b="7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr",
        description="Trading Pair 4"
    ),
    TradingPair(
        token_a="22WrmyTj8x2TRVQen3fxxi2r4Rn619cAucfRsmhVJffodSp",
        token_b="ED5nyyWEzpPPiWimP8vYm7sD7TD3LAt3Q3gRTWHzPJBY",
        description="Trading Pair 5"
    ),
    TradingPair(
        token_a="Q2sPHPdUWFMg7M7wwrQKLrn619cAucfRsmhVJffodSp",
        token_b="Dz9mQ9NzkBcCsuGPFJ3r1bS4wgqKMHBPiVuniW8Mbonk",
        description="Trading Pair 6"
    ),
    TradingPair(
        token_a="4qQM2x2pfhU3ToscAqkQxTfhTm7DmJe8LGWU9kvqeNH4",
        token_b="FtUEW73K6vEYHfbkfpdBZfWpxgQar2HipGdbutEhpump",
        description="Trading Pair 7"
    ),
    TradingPair(
        token_a="5wNu5QhdpRGrL37ffcd6TMMqZugQgxwafgz477rShtHy",
        token_b="Ce2gx9KGXJ6C9Mp5b5x1sn9Mg87JwEbrQby4Zqo3pump",
        description="Trading Pair 8"
    )
]

def get_all_pairs() -> List[TradingPair]:
    """Получить все торговые пары"""
    return TRADING_PAIRS

def get_pair_by_index(index: int) -> TradingPair:
    """Получить торговую пару по индексу"""
    if 0 <= index < len(TRADING_PAIRS):
        return TRADING_PAIRS[index]
    raise IndexError(f"Trading pair index {index} out of range")

def get_all_token_a() -> List[str]:
    """Получить все токены A"""
    return [pair.token_a for pair in TRADING_PAIRS]

def get_all_token_b() -> List[str]:
    """Получить все токены B"""
    return [pair.token_b for pair in TRADING_PAIRS]

def get_all_unique_tokens() -> List[str]:
    """Получить все уникальные токены"""
    tokens = set()
    for pair in TRADING_PAIRS:
        tokens.add(pair.token_a)
        tokens.add(pair.token_b)
    return list(tokens)
