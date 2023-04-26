from typing import List
from dagster import asset, RetryRequested
import pandas as pd

from c3d3.domain.d3.adhoc.nodes.http.adhoc import HTTPNode
from c3d3.infrastructure.d3.abstract.factory import D3AbstractFactory
from c3d3.infrastructure.d3.bridge.bridge import D3Bridge
from c3d3.infrastructure.d3.factories.dex_erc_screener.factory import DexERCScreenerFactory
from c3d3.infrastructure.d3.interfaces.dex_erc_screener.interface import iDexERCScreenerHandler
from c3d3.infrastructure.d3.handlers.dex_erc_screener.erc20.handler import ERC20DexERCScreenerHandler

from etl.resources.w3sleepy.resource import W3Sleepy, MAX_RETRIES


@asset(
    name='df',
    required_resource_keys={
        'logger',
        'fernet',
        'df_serializer'
    }
)
def get_overview(context, configs: dict) -> List[list]:
    def _formatting(raw: pd.DataFrame) -> pd.DataFrame:
        raw.rename(
            columns={
                iDexERCScreenerHandler._WALLET_ADDRESS_COLUMN: 'h_wallet_address',
                iDexERCScreenerHandler._LABEL_COLUMN: 'h_label_name',
                iDexERCScreenerHandler._TOKEN_ADDRESS_COLUMN: 'h_token_address',
                iDexERCScreenerHandler._CHAIN_NAME_COLUMN: 'h_network_name',
                iDexERCScreenerHandler._SYMBOL_COLUMN: 'pit_symbol',
                iDexERCScreenerHandler._CURRENT_PRICE_COLUMN: 'pit_price',
                iDexERCScreenerHandler._QTY_COLUMN: 'pit_qty',
                iDexERCScreenerHandler._TS_COLUMN: 'pit_ts'
            },
            inplace=True
        )
        return raw

    node = HTTPNode(uri=context.resources.fernet.decrypt(configs['network_rpc_node'].encode()).decode())
    handler = D3Bridge(
        abstract_factory=D3AbstractFactory,
        factory_key=DexERCScreenerFactory.key,
        object_key=ERC20DexERCScreenerHandler.key
    ).init_object(
        address=configs['token_address'],
        wallet_address=configs['wallet_address'],
        node=node,
        label=configs['label_name'],
        chain=configs['network_name']
    )
    try:
        overview = handler.do()
    except ValueError as exc:
        raise RetryRequested(max_retries=MAX_RETRIES, seconds_to_wait=.5) from exc

    df = _formatting(raw=overview)
    return context.resources.df_serializer.df_to_list(df)
