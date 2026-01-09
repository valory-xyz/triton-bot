"""Chain Module
This module provides functions to interact with the blockchain."""

import datetime
import json
import logging
import math
import os
from http import HTTPStatus
from pathlib import Path
from typing import cast
from urllib.parse import urlencode

import dotenv
import pytz
import requests
from operate.constants import IPFS_ADDRESS
from operate.ledger.profiles import WRAPPED_NATIVE_ASSET
from operate.operate_types import ChainType
from web3 import Web3
from web3.contract import Contract
from web3.exceptions import ABIFunctionNotFound, ContractLogicError

from triton.constants import (
    LOCAL_TIMEZONE,
    OLAS_TOKEN_ADDRESS_GNOSIS,
    STAKING_CONTRACTS,
)
from triton.tools import wei_to_olas

logger = logging.getLogger("chain")

dotenv.load_dotenv(override=True)

GNOSIS_RPC = os.getenv("GNOSIS_RPC")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")

# Instantiate the web3 provider and ethereum client
web3 = Web3(Web3.HTTPProvider(GNOSIS_RPC))


def get_native_balance(address: str):
    """Get the native balance"""
    balance_wei = web3.eth.get_balance(web3.to_checksum_address(address))
    balance_ether = web3.from_wei(balance_wei, "ether")
    return balance_ether


def load_contract(
    contract_address: str, abi_file: str, has_abi_key: bool = True
) -> Contract:
    """Load a smart contract"""
    with open(Path("abis", f"{abi_file}.json"), "r", encoding="utf-8") as f:
        contract_abi = json.load(f)
        if has_abi_key:
            contract_abi = contract_abi["abi"]

    contract = web3.eth.contract(
        address=web3.to_checksum_address(contract_address), abi=contract_abi
    )
    return contract


def get_wrapped_native_balance(address: str, chain: ChainType) -> float:
    """Get the wrapped native balance"""
    return (
        load_contract(WRAPPED_NATIVE_ASSET[chain], "erc20", has_abi_key=False)
        .functions.balanceOf(address)
        .call()
        / 10
        ** load_contract(WRAPPED_NATIVE_ASSET[chain], "erc20", has_abi_key=False)
        .functions.decimals()
        .call()
    )


def get_olas_balance(address: str):
    """ "Get OLAS balance"""
    olas_token_contract = load_contract(OLAS_TOKEN_ADDRESS_GNOSIS, "olas", False)
    olas_balance = olas_token_contract.functions.balanceOf(address).call()
    return olas_balance


def get_mech_request_count(
    mech_contract_address: str,
    requester_address: str,
) -> int:
    """Get the number of requests made by a requester to a mech"""
    mech_contract = load_contract(mech_contract_address, "mech", has_abi_key=False)
    try:
        mech_request_count = mech_contract.functions.mapRequestsCounts(
            requester_address
        ).call()
    except (ContractLogicError, ABIFunctionNotFound, ValueError):
        # Use mapRequestCounts for newer mechs
        mech_request_count = mech_contract.functions.mapRequestCounts(
            requester_address
        ).call()

    return mech_request_count


def get_staking_status(  # pylint: disable=too-many-locals
    mech_contract_address: str,
    staking_token_address: str,
    activity_checker_address: str,
    service_id: int,
    safe_address: str,
) -> dict:
    """Get the staking status"""
    staking_token_contract = load_contract(staking_token_address, "staking_token")
    activity_checker_contract = load_contract(activity_checker_address, "mech_activity")

    # Rewards
    service_info = staking_token_contract.functions.mapServiceInfo(service_id).call()
    accrued_rewards = wei_to_olas(service_info[3])

    # Request count (total)
    mech_request_count = get_mech_request_count(
        mech_contract_address=mech_contract_address,
        requester_address=safe_address,
    )

    # Request count (last checkpoint)
    service_info = (staking_token_contract.functions.getServiceInfo(service_id).call())[
        2
    ]
    mech_request_count_on_last_checkpoint = service_info[1] if service_info else 0

    # Request count (current epoch)
    mech_requests_this_epoch = (
        mech_request_count - mech_request_count_on_last_checkpoint
    )

    # Required requests
    liveness_ratio = activity_checker_contract.functions.livenessRatio().call()
    mech_requests_24h_threshold = math.ceil((liveness_ratio * 60 * 60 * 24) / 10**18)

    # Epoch end
    liveness_period = staking_token_contract.functions.livenessPeriod().call()
    checkpoint_ts = staking_token_contract.functions.tsCheckpoint().call()
    epoch_end = datetime.datetime.fromtimestamp(
        checkpoint_ts + liveness_period,
        pytz.timezone(LOCAL_TIMEZONE),
    )

    metadata_hash = staking_token_contract.functions.metadataHash().call().hex()
    ipfs_address = IPFS_ADDRESS.format(hash=metadata_hash)
    response = requests.get(ipfs_address, timeout=30)
    if response.status_code != HTTPStatus.OK:
        raise requests.RequestException(
            f"Failed to fetch data from {ipfs_address}: {response.status_code}"
        )
    metadata = response.json()

    return {
        "accrued_rewards": accrued_rewards,
        "mech_requests_this_epoch": mech_requests_this_epoch,
        "required_mech_requests": mech_requests_24h_threshold,
        "epoch_end": epoch_end.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "metadata": metadata,
    }


def get_olas_price() -> float | None:
    """Get OLAS price"""
    url = "https://api.coingecko.com/api/v3/simple/price?" + urlencode(
        {
            "ids": "autonolas",
            "vs_currencies": "usd",
            "x_cg_demo_api_key": COINGECKO_API_KEY,
        }
    )
    headers = {"accept": "application/json"}
    response = requests.get(url=url, headers=headers, timeout=30)
    if response.status_code != 200:
        logger.error(response)
        return None
    price = response.json()["autonolas"]["usd"]
    return price


def get_slots() -> dict:
    """Get the available slots in all staking contracts"""
    slots = {}

    for contract_name, contract_data in STAKING_CONTRACTS.items():
        staking_token_contract = load_contract(
            cast(str, contract_data["address"]), "staking_token"
        )
        ids = staking_token_contract.functions.getServiceIds().call()
        slots[contract_name] = cast(int, contract_data["slots"]) - len(ids)

    return slots
