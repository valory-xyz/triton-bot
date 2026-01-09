"""Triton Service Module.
This module defines the TritonService class, which handles the operations of the Triton bot service.
"""

import logging
import os
import traceback
from typing import List, Optional, Tuple, cast

import dotenv
from operate.cli import OperateApp
from operate.data import DATA_DIR
from operate.data.contracts.mech_activity.contract import MechActivityContract
from operate.data.contracts.requester_activity_checker.contract import (
    RequesterActivityCheckerContract,
)
from operate.ledger import get_default_ledger_api
from operate.ledger.profiles import OLAS, get_staking_contract
from operate.operate_types import Chain, LedgerType
from operate.utils.gnosis import transfer_erc20_from_safe

from triton.chain import (
    get_native_balance,
    get_olas_balance,
    get_staking_status,
    get_wrapped_native_balance,
)

dotenv.load_dotenv(override=True)


class TritonService:
    """Trader"""

    def __init__(self, operate: OperateApp, service_config_id: str) -> None:
        """Constructor"""
        self.service_manager = operate.service_manager()
        self.master_wallet = operate.wallet_manager.load(
            ledger_type=LedgerType.ETHEREUM
        )
        self.service = self.service_manager.load(service_config_id=service_config_id)
        self.logger = logging.getLogger(self.service.name)
        self.withdrawal_address = os.getenv("WITHDRAWAL_ADDRESS", None)

    @property
    def service_id(self) -> int:
        """Get the service id"""
        return self.service.chain_configs[self.service.home_chain].chain_data.token

    @property
    def agent_address(self) -> str:
        """Get the agent address"""
        if (
            len(
                self.service.chain_configs[self.service.home_chain].chain_data.instances
            )
            == 0
        ):
            raise ValueError("No agent instances found in the chain configuration")
        return self.service.chain_configs[self.service.home_chain].chain_data.instances[
            0
        ]

    @property
    def service_safe(self) -> str:
        """Get the service safe address"""
        return self.service.chain_configs[self.service.home_chain].chain_data.multisig

    @property
    def staking_contract_address(self) -> str:
        """Get the staking contract address"""
        try:
            current_staking_program = self.service_manager._get_current_staking_program(  # pylint: disable=protected-access  # noqa: E501
                service=self.service, chain=self.service.home_chain
            )
            staking_contract_address = get_staking_contract(
                chain=self.service.home_chain,
                staking_program_id=current_staking_program,
            )
            if not staking_contract_address:
                raise ValueError(
                    f"Staking contract address not found for {current_staking_program=}."
                )

            return staking_contract_address
        except KeyError as e:
            raise ValueError("Failed to get staking contract address.") from e

    def get_staking_status(self) -> dict:
        """Get the staking status"""
        self.logger.info("Checking staking status")
        try:
            staking_contract_address = self.staking_contract_address
            sftxb = self.service_manager.get_eth_safe_tx_builder(
                ledger_config=self.service.chain_configs[
                    self.service.home_chain
                ].ledger_config,
            )
            staking_params = sftxb.get_staking_params(
                staking_contract=staking_contract_address
            )
            activity_checker_contract_address = staking_params["activity_checker"]
        except KeyError as e:
            raise ValueError("Failed to get staking status.") from e

        try:
            requester_activity_checker = cast(
                RequesterActivityCheckerContract,
                RequesterActivityCheckerContract.from_dir(
                    directory=str(DATA_DIR / "contracts" / "requester_activity_checker")
                ),
            )
            mech = (
                requester_activity_checker.get_instance(
                    ledger_api=sftxb.ledger_api,
                    contract_address=activity_checker_contract_address,
                )
                .functions.mechMarketplace()
                .call()
            )
        except Exception:  # pylint: disable=broad-except
            try:
                mech_activity_contract = cast(
                    MechActivityContract,
                    MechActivityContract.from_dir(
                        directory=str(DATA_DIR / "contracts" / "mech_activity")
                    ),
                )
                mech = (
                    mech_activity_contract.get_instance(
                        ledger_api=sftxb.ledger_api,
                        contract_address=activity_checker_contract_address,
                    )
                    .functions.agentMech()
                    .call()
                )
            except Exception:  # pylint: disable=broad-except
                mech = "0x77af31De935740567Cf4fF1986D04B2c964A786a"

        return get_staking_status(
            mech_contract_address=mech,
            staking_token_address=staking_contract_address,
            activity_checker_address=activity_checker_contract_address,
            service_id=self.service_id,
            safe_address=self.service_safe,
        )

    def check_balance(self) -> dict:
        """Check the native balance"""
        chain_config = self.service.chain_configs[self.service.home_chain]
        if len(chain_config.chain_data.instances) == 0:
            raise ValueError("No agent instances found in the chain configuration")

        if self.master_wallet.safes is None:
            raise ValueError("Master wallet safes not found")

        agent_eoa_native_balance = get_native_balance(self.agent_address)
        service_safe_native_balance = get_native_balance(self.service_safe)
        service_safe_wrapped_native_balance = get_wrapped_native_balance(
            self.service_safe,
            Chain.from_string(self.service.home_chain),  # type: ignore[attr-defined]
        )
        master_eoa_native_balance = get_native_balance(
            self.master_wallet.crypto.address
        )
        master_safe_address = self.master_wallet.safes[
            Chain.from_string(self.service.home_chain)  # type: ignore[attr-defined]
        ]
        master_safe_native_balance = get_native_balance(master_safe_address)
        master_safe_olas_balance = get_olas_balance(master_safe_address) / 1e18
        service_safe_olas_balance = get_olas_balance(self.service_safe) / 1e18

        self.logger.info(
            "Agent EOA balance = %.2f xDAI "
            "| Service Safe balance: %.2f xDAI  %.2f wxDAI  %.2f OLAS "
            "| Master EOA balance: %.2f xDAI "
            "| Master Safe balance: %.2f xDAI",
            agent_eoa_native_balance,
            service_safe_native_balance,
            service_safe_wrapped_native_balance,
            service_safe_olas_balance,
            master_eoa_native_balance,
            master_safe_native_balance,
        )

        return {
            "agent_eoa_native_balance": agent_eoa_native_balance,
            "service_safe_native_balance": service_safe_native_balance,
            "service_safe_wrapped_native_balance": service_safe_wrapped_native_balance,
            "master_eoa_native_balance": master_eoa_native_balance,
            "master_safe_native_balance": master_safe_native_balance,
            "master_safe_olas_balance": master_safe_olas_balance,
            "service_safe_olas_balance": service_safe_olas_balance,
        }

    def claim_rewards(self) -> int:
        """Claim staking rewards"""

        self.logger.info("Claiming rewards")
        try:
            return self.service_manager.claim_on_chain_from_safe(
                service_config_id=self.service.service_config_id,
                chain=self.service.home_chain,
            )
        except Exception:  # pylint: disable=broad-except
            self.logger.error("Failed to claim rewards. %s", traceback.format_exc())

        return 0

    def withdraw_rewards(self) -> List[Tuple[Optional[str], float, str]]:
        """Withdraw staking rewards"""

        if not self.withdrawal_address:
            return []

        home_chain = Chain.from_string(self.service.home_chain)  # type: ignore[attr-defined]
        master_safe = self.master_wallet.safes[home_chain]

        try:
            master_safe_olas_balance = get_olas_balance(master_safe)
        except Exception:  # pylint: disable=broad-except
            self.logger.error("Failed to get OLAS balance. %s", traceback.format_exc())
            master_safe_olas_balance = 0

        withdrawals: List[Tuple[Optional[str], float, str]] = []
        if master_safe_olas_balance:
            self.logger.info(
                "Withdrawing %.2f OLAS rewards", master_safe_olas_balance / 1e18
            )
            olas_address = OLAS[home_chain]

            try:
                tx_hash = self.master_wallet.transfer(
                    to=self.withdrawal_address,
                    amount=master_safe_olas_balance,
                    chain=home_chain,
                    asset=olas_address,
                )
                withdrawals.append(
                    (tx_hash, master_safe_olas_balance / 1e18, "Master Safe")
                )
            except Exception:  # pylint: disable=broad-except
                self.logger.error("Failed to withdraw OLAS. %s", traceback.format_exc())
        else:
            self.logger.info("No Master safe OLAS to withdraw")

        chain = Chain.from_string(self.service.home_chain)  # type: ignore[attr-defined]
        ledger_api = get_default_ledger_api(chain=chain)
        try:
            service_safe_olas_balance = get_olas_balance(self.service_safe) / 1e18
            if service_safe_olas_balance > 0:
                self.logger.info(
                    "Withdrawing %s OLAS from safe on %s to %s",
                    service_safe_olas_balance,
                    chain.value,
                    self.withdrawal_address,
                )
                ethereum_crypto = self.service_manager.keys_manager.get_crypto_instance(
                    self.service.agent_addresses[0]
                )
                tx_hash = transfer_erc20_from_safe(
                    ledger_api=ledger_api,
                    crypto=ethereum_crypto,
                    safe=self.service_safe,
                    token=OLAS[chain],
                    to=self.withdrawal_address,
                    amount=service_safe_olas_balance * 1e18,
                )
                withdrawals.append((tx_hash, service_safe_olas_balance, "Service Safe"))
        except Exception:  # pylint: disable=broad-except
            self.logger.error(
                "Failed to withdraw OLAS from service safe. %s", traceback.format_exc()
            )

        return withdrawals
