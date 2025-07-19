"""
Утилиты для работы с SPL токенами
"""

from typing import Optional, Dict, Any
from solders.pubkey import Pubkey as PublicKey
from solana.rpc.async_api import AsyncClient
from spl.token.constants import TOKEN_PROGRAM_ID


async def get_token_balance(
    client: AsyncClient,
    token_account: PublicKey,
    commitment: str = "confirmed"
) -> Optional[int]:
    """
    Получает баланс токенов для указанного токен-аккаунта
    
    Args:
        client: AsyncClient для подключения к Solana
        token_account: PublicKey токен-аккаунта
        commitment: Уровень подтверждения
        
    Returns:
        Баланс в минимальных единицах или None если аккаунт не найден
    """
    try:
        response = await client.get_token_account_balance(token_account, commitment)
        if response.value:
            return int(response.value.amount)
        return None
    except Exception:
        return None


async def get_token_supply(
    client: AsyncClient,
    mint: PublicKey,
    commitment: str = "confirmed"
) -> Optional[Dict[str, Any]]:
    """
    Получает информацию о supply токена
    
    Args:
        client: AsyncClient для подключения к Solana
        mint: PublicKey минта токена
        commitment: Уровень подтверждения
        
    Returns:
        Словарь с информацией о supply или None
    """
    try:
        response = await client.get_token_supply(mint, commitment)
        if response.value:
            return {
                "amount": response.value.amount,
                "decimals": response.value.decimals,
                "ui_amount": response.value.ui_amount,
                "ui_amount_string": response.value.ui_amount_string
            }
        return None
    except Exception:
        return None


async def get_token_accounts_by_owner(
    client: AsyncClient,
    owner: PublicKey,
    mint: Optional[PublicKey] = None,
    program_id: PublicKey = TOKEN_PROGRAM_ID,
    commitment: str = "confirmed"
) -> Optional[list]:
    """
    Получает все токен-аккаунты для указанного владельца
    
    Args:
        client: AsyncClient для подключения к Solana
        owner: PublicKey владельца
        mint: Опциональный фильтр по минту
        program_id: ID токен-программы
        commitment: Уровень подтверждения
        
    Returns:
        Список токен-аккаунтов или None
    """
    try:
        if mint:
            response = await client.get_token_accounts_by_owner(
                owner,
                {"mint": mint},
                {"programId": program_id},
                commitment
            )
        else:
            response = await client.get_token_accounts_by_owner(
                owner,
                {"programId": program_id},
                commitment=commitment
            )
            
        if response.value:
            return response.value
        return None
    except Exception:
        return None


async def get_associated_token_address(
    owner: PublicKey,
    mint: PublicKey,
    token_program_id: PublicKey = TOKEN_PROGRAM_ID
) -> PublicKey:
    """
    Вычисляет associated token address
    
    Args:
        owner: Владелец токен-аккаунта
        mint: Минт токена
        token_program_id: ID токен-программы
        
    Returns:
        Associated token address
    """
    from spl.token.instructions import get_associated_token_address
    return get_associated_token_address(owner, mint, token_program_id)
