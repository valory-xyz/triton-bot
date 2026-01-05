"""Tests for triton.service module"""
import logging
import os
import pytest
from unittest.mock import patch, MagicMock

from operate.operate_types import Chain
from triton.service import TritonService


class TestTritonService:
    """Tests for TritonService class"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_operate = MagicMock()
        self.mock_service_manager = MagicMock()
        self.mock_wallet_manager = MagicMock()
        self.mock_master_wallet = MagicMock()
        self.mock_service = MagicMock()
        
        # Setup mock chains
        self.mock_operate.service_manager.return_value = self.mock_service_manager
        self.mock_operate.wallet_manager = self.mock_wallet_manager
        self.mock_wallet_manager.load.return_value = self.mock_master_wallet
        self.mock_service_manager.load.return_value = self.mock_service
        
        # Setup mock service properties
        self.mock_service.name = "test_service"
        self.mock_service.service_config_id = "test_config_id"
        self.mock_service.home_chain = "gnosis"
        self.mock_service.keys = [MagicMock()]
        self.mock_service.keys[0].private_key = "test_private_key"
        
        # Setup mock chain configs
        mock_chain_config = MagicMock()
        mock_chain_data = MagicMock()
        mock_chain_data.multisig = "0x1234567890abcdef1234567890abcdef12345678"
        mock_chain_data.token = 123
        mock_chain_data.instances = ["0xabcdef1234567890abcdef1234567890abcdef12"]
        mock_chain_config.chain_data = mock_chain_data
        
        self.mock_service.chain_configs = {"gnosis": mock_chain_config}
    
    @patch.dict(os.environ, {"WITHDRAWAL_ADDRESS": "0x1111111111111111111111111111111111111111"})
    def test_init_with_withdrawal_address(self):
        """Test TritonService initialization with withdrawal address"""
        service = TritonService(self.mock_operate, "test_config_id")
        
        assert service.service_manager == self.mock_service_manager
        assert service.master_wallet == self.mock_master_wallet
        assert service.service == self.mock_service
        assert service.withdrawal_address == "0x1111111111111111111111111111111111111111"
        assert isinstance(service.logger, logging.Logger)
    
    @patch.dict(os.environ, {}, clear=True)
    def test_init_without_withdrawal_address(self):
        """Test TritonService initialization without withdrawal address"""
        service = TritonService(self.mock_operate, "test_config_id")
        
        assert service.withdrawal_address is None
    
    def test_service_id_property(self):
        """Test service_id property"""
        service = TritonService(self.mock_operate, "test_config_id")
        
        assert service.service_id == 123
    
    def test_agent_address_property(self):
        """Test agent_address property"""
        service = TritonService(self.mock_operate, "test_config_id")
        
        assert service.agent_address == "0xabcdef1234567890abcdef1234567890abcdef12"
    
    def test_agent_address_property_no_instances(self):
        """Test agent_address property when no instances exist"""
        self.mock_service.chain_configs["gnosis"].chain_data.instances = []
        
        with pytest.raises(ValueError, match="No agent instances found"):
            service = TritonService(self.mock_operate, "test_config_id")
            service.agent_address
    
    def test_service_safe_property(self):
        """Test service_safe property"""
        service = TritonService(self.mock_operate, "test_config_id")
        
        assert service.service_safe == "0x1234567890abcdef1234567890abcdef12345678"
    
    @patch('triton.service.get_staking_contract')
    def test_staking_contract_address_property(self, mock_get_staking_contract):
        """Test staking_contract_address property"""
        mock_get_staking_contract.return_value = "0x2222222222222222222222222222222222222222"
        self.mock_service_manager._get_current_staking_program.return_value = "program_1"
        
        service = TritonService(self.mock_operate, "test_config_id")
        
        assert service.staking_contract_address == "0x2222222222222222222222222222222222222222"
        mock_get_staking_contract.assert_called_once_with(
            chain="gnosis",
            staking_program_id="program_1"
        )
    
    def test_staking_contract_address_property_key_error(self):
        """Test staking_contract_address property with KeyError"""
        self.mock_service_manager._get_current_staking_program.side_effect = KeyError("Not found")
        
        service = TritonService(self.mock_operate, "test_config_id")
        
        with pytest.raises(ValueError, match="Failed to get staking contract address"):
            service.staking_contract_address
    
    @patch('triton.service.get_staking_status')
    @patch('triton.service.get_staking_contract')
    @patch('triton.service.RequesterActivityCheckerContract')
    def test_get_staking_status_success_with_mech_marketplace(self, mock_requester_contract, mock_get_staking_contract, mock_get_staking_status):
        """Test get_staking_status method success when mechMarketplace call works"""
        mock_get_staking_contract.return_value = "0x2222222222222222222222222222222222222222"
        mock_get_staking_status.return_value = {
            "accrued_rewards": "1.00 OLAS",
            "mech_requests_this_epoch": 5,
            "required_mech_requests": 10,
            "epoch_end": "2023-01-01 12:00:00 UTC"
        }
        self.mock_service_manager._get_current_staking_program.return_value = "program_1"
        
        # Mock the safe tx builder and staking params
        mock_sftxb = MagicMock()
        mock_sftxb.get_staking_params.return_value = {"activity_checker": "0xactivity123"}
        self.mock_service_manager.get_eth_safe_tx_builder.return_value = mock_sftxb
        
        # Mock RequesterActivityCheckerContract to succeed
        mock_contract_instance = MagicMock()
        mock_contract_instance.functions.mechMarketplace.return_value.call.return_value = "0xmech123"
        mock_requester_instance = MagicMock()
        mock_requester_instance.get_instance.return_value = mock_contract_instance
        mock_requester_contract.from_dir.return_value = mock_requester_instance
        
        service = TritonService(self.mock_operate, "test_config_id")
        result = service.get_staking_status()
        
        assert result["accrued_rewards"] == "1.00 OLAS"
        assert result["mech_requests_this_epoch"] == 5
        mock_get_staking_status.assert_called_once_with(
            mech_contract_address="0xmech123",
            staking_token_address="0x2222222222222222222222222222222222222222",
            activity_checker_address="0xactivity123",
            service_id=123,
            safe_address="0x1234567890abcdef1234567890abcdef12345678"
        )
    
    @patch('triton.service.get_staking_status')
    @patch('triton.service.get_staking_contract')
    @patch('triton.service.RequesterActivityCheckerContract')
    @patch('triton.service.MechActivityContract')
    def test_get_staking_status_success_with_agent_mech(self, mock_mech_contract, mock_requester_contract, mock_get_staking_contract, mock_get_staking_status):
        """Test get_staking_status method success when mechMarketplace fails but agentMech works"""
        mock_get_staking_contract.return_value = "0x2222222222222222222222222222222222222222"
        mock_get_staking_status.return_value = {
            "accrued_rewards": "2.00 OLAS",
            "mech_requests_this_epoch": 8,
            "required_mech_requests": 10,
            "epoch_end": "2023-01-01 12:00:00 UTC"
        }
        self.mock_service_manager._get_current_staking_program.return_value = "program_1"
        
        # Mock the safe tx builder and staking params
        mock_sftxb = MagicMock()
        mock_sftxb.get_staking_params.return_value = {"activity_checker": "0xactivity123"}
        self.mock_service_manager.get_eth_safe_tx_builder.return_value = mock_sftxb
        
        # Mock RequesterActivityCheckerContract to fail
        mock_requester_contract.from_dir.side_effect = Exception("RequesterActivityChecker failed")
        
        # Mock MechActivityContract to succeed
        mock_mech_instance = MagicMock()
        mock_mech_instance.functions.agentMech.return_value.call.return_value = "0xagentmech456"
        mock_mech_contract_instance = MagicMock()
        mock_mech_contract_instance.get_instance.return_value = mock_mech_instance
        mock_mech_contract.from_dir.return_value = mock_mech_contract_instance
        
        service = TritonService(self.mock_operate, "test_config_id")
        result = service.get_staking_status()
        
        assert result["accrued_rewards"] == "2.00 OLAS"
        assert result["mech_requests_this_epoch"] == 8
        mock_get_staking_status.assert_called_once_with(
            mech_contract_address="0xagentmech456",
            staking_token_address="0x2222222222222222222222222222222222222222",
            activity_checker_address="0xactivity123",
            service_id=123,
            safe_address="0x1234567890abcdef1234567890abcdef12345678"
        )
    
    @patch('triton.service.get_staking_status')
    @patch('triton.service.get_staking_contract')
    @patch('triton.service.RequesterActivityCheckerContract')
    @patch('triton.service.MechActivityContract')
    def test_get_staking_status_success_with_fallback_mech(self, mock_mech_contract, mock_requester_contract, mock_get_staking_contract, mock_get_staking_status):
        """Test get_staking_status method success when both contract calls fail and fallback is used"""
        mock_get_staking_contract.return_value = "0x2222222222222222222222222222222222222222"
        mock_get_staking_status.return_value = {
            "accrued_rewards": "0.50 OLAS",
            "mech_requests_this_epoch": 3,
            "required_mech_requests": 10,
            "epoch_end": "2023-01-01 12:00:00 UTC"
        }
        self.mock_service_manager._get_current_staking_program.return_value = "program_1"
        
        # Mock the safe tx builder and staking params
        mock_sftxb = MagicMock()
        mock_sftxb.get_staking_params.return_value = {"activity_checker": "0xactivity123"}
        self.mock_service_manager.get_eth_safe_tx_builder.return_value = mock_sftxb
        
        # Mock both contracts to fail
        mock_requester_contract.from_dir.side_effect = Exception("RequesterActivityChecker failed")
        mock_mech_contract.from_dir.side_effect = Exception("MechActivity failed")
        
        service = TritonService(self.mock_operate, "test_config_id")
        result = service.get_staking_status()
        
        assert result["accrued_rewards"] == "0.50 OLAS"
        assert result["mech_requests_this_epoch"] == 3
        mock_get_staking_status.assert_called_once_with(
            mech_contract_address="0x77af31De935740567Cf4fF1986D04B2c964A786a",  # Hardcoded fallback
            staking_token_address="0x2222222222222222222222222222222222222222",
            activity_checker_address="0xactivity123",
            service_id=123,
            safe_address="0x1234567890abcdef1234567890abcdef12345678"
        )
    
    @patch('triton.service.get_olas_balance')
    @patch('triton.service.get_native_balance')
    @patch('triton.service.get_wrapped_native_balance')
    def test_check_balance_success(self, mock_get_wrapped_native_balance, mock_get_native_balance, mock_get_olas_balance):
        """Test check_balance method success"""
        mock_get_native_balance.side_effect = [1.0, 2.0, 3.0, 4.0]  # agent, service, master eoa, master safe
        mock_get_wrapped_native_balance.return_value = 1.0
        mock_get_olas_balance.return_value = 5000000000000000000  # 5 OLAS in wei
        
        # Mock master wallet properties
        self.mock_master_wallet.crypto.address = "0x3333333333333333333333333333333333333333"
        self.mock_master_wallet.safes = {Chain.GNOSIS: "0x4444444444444444444444444444444444444444"}
        
        service = TritonService(self.mock_operate, "test_config_id")
        result = service.check_balance()
        
        assert result["agent_eoa_native_balance"] == 1.0
        assert result["service_safe_native_balance"] == 2.0
        assert result["service_safe_wrapped_native_balance"] == 1.0
        assert result["master_eoa_native_balance"] == 3.0
        assert result["master_safe_native_balance"] == 4.0
        assert result["service_safe_olas_balance"] == 5.0  # 5 OLAS
        assert mock_get_native_balance.call_count == 4
        assert mock_get_wrapped_native_balance.call_count == 1
    
    def test_check_balance_no_instances(self):
        """Test check_balance method when no instances exist"""
        self.mock_service.chain_configs["gnosis"].chain_data.instances = []
        
        service = TritonService(self.mock_operate, "test_config_id")
        
        with pytest.raises(ValueError, match="No agent instances found"):
            service.check_balance()
    
    def test_claim_rewards_success(self):
        """Test claim_rewards method success"""
        self.mock_service_manager.claim_on_chain_from_safe.return_value = 1234
        
        service = TritonService(self.mock_operate, "test_config_id")
        result = service.claim_rewards()
        
        assert result == 1234
        self.mock_service_manager.claim_on_chain_from_safe.assert_called_once_with(
            service_config_id="test_config_id",
            chain="gnosis"
        )
    
    @patch('triton.service.traceback')
    def test_claim_rewards_exception(self, mock_traceback):
        """Test claim_rewards method with exception"""
        self.mock_service_manager.claim_on_chain_from_safe.side_effect = Exception("Test error")
        mock_traceback.format_exc.return_value = "Traceback info"
        
        service = TritonService(self.mock_operate, "test_config_id")
        service.logger.error = MagicMock()
        result = service.claim_rewards()
        
        assert result == 0
        service.logger.error.assert_called_once()
    
    @patch.dict(os.environ, {}, clear=True)
    def test_withdraw_rewards_no_withdrawal_address(self):
        """Test withdraw_rewards method without withdrawal address"""
        service = TritonService(self.mock_operate, "test_config_id")
        
        result = service.withdraw_rewards()
        
        assert result == []
    
    @patch.dict(os.environ, {"WITHDRAWAL_ADDRESS": "0x1111111111111111111111111111111111111111"})
    @patch('triton.service.get_olas_balance')
    def test_withdraw_rewards_no_balance(self, mock_get_olas_balance):
        """Test withdraw_rewards method with no OLAS balance"""
        mock_get_olas_balance.return_value = 0
        
        service = TritonService(self.mock_operate, "test_config_id")
        result = service.withdraw_rewards()
        
        assert result == []
    
    @patch.dict(os.environ, {"WITHDRAWAL_ADDRESS": "0x1111111111111111111111111111111111111111"})
    @patch('triton.service.get_olas_balance')
    @patch('triton.service.traceback')
    def test_withdraw_rewards_get_balance_exception(self, mock_traceback, mock_get_olas_balance):
        """Test withdraw_rewards method with exception getting balance"""
        mock_get_olas_balance.side_effect = Exception("Test error")
        mock_traceback.format_exc.return_value = "Traceback info"
        
        service = TritonService(self.mock_operate, "test_config_id")
        service.logger.error = MagicMock()
        result = service.withdraw_rewards()
        
        assert result == []
        service.logger.error.assert_called()
    
    @patch.dict(os.environ, {"WITHDRAWAL_ADDRESS": "0x1111111111111111111111111111111111111111"})
    @patch('triton.service.get_olas_balance')
    @patch('triton.service.OLAS', {Chain.GNOSIS: "0x5555555555555555555555555555555555555555"})
    def test_withdraw_rewards_success(self, mock_get_olas_balance):
        """Test withdraw_rewards method success"""
        mock_get_olas_balance.return_value = 1000000000000000000  # 1 OLAS in wei
        self.mock_master_wallet.transfer.return_value = "0xabcdef1234567890"
        
        service = TritonService(self.mock_operate, "test_config_id")
        result = service.withdraw_rewards()
        
        assert result == [("0xabcdef1234567890", 1.0, "Master Safe")]
        self.mock_master_wallet.transfer.assert_called_once()
    
    @patch.dict(os.environ, {"WITHDRAWAL_ADDRESS": "0x1111111111111111111111111111111111111111"})
    @patch('triton.service.get_olas_balance')
    @patch('triton.service.OLAS', {Chain.GNOSIS: "0x5555555555555555555555555555555555555555"})
    @patch('triton.service.traceback')
    def test_withdraw_rewards_transfer_exception(self, mock_traceback, mock_get_olas_balance):
        """Test withdraw_rewards method with transfer exception"""
        mock_get_olas_balance.return_value = 1000000000000000000  # 1 OLAS in wei
        self.mock_master_wallet.transfer.side_effect = Exception("Transfer failed")
        mock_traceback.format_exc.return_value = "Traceback info"
        
        service = TritonService(self.mock_operate, "test_config_id")
        service.logger.error = MagicMock()
        result = service.withdraw_rewards()
        
        assert result == []
        service.logger.error.assert_called()


class TestTritonServiceIntegration:
    """Integration tests for TritonService"""
    
    def test_service_workflow(self):
        """Test typical service workflow"""
        # This would be an integration test that tests the full workflow
        # For now, we'll just verify the class can be instantiated
        mock_operate = MagicMock()
        mock_service_manager = MagicMock()
        mock_wallet_manager = MagicMock()
        mock_master_wallet = MagicMock()
        mock_service = MagicMock()
        
        # Setup mock chains
        mock_operate.service_manager.return_value = mock_service_manager
        mock_operate.wallet_manager = mock_wallet_manager
        mock_wallet_manager.load.return_value = mock_master_wallet
        mock_service_manager.load.return_value = mock_service
        
        # Setup mock service properties
        mock_service.name = "test_service"
        mock_service.service_config_id = "test_config_id"
        mock_service.home_chain = "gnosis"
        mock_service.keys = [MagicMock()]
        mock_service.keys[0].private_key = "test_private_key"
        
        # Setup mock chain configs
        mock_chain_config = MagicMock()
        mock_chain_data = MagicMock()
        mock_chain_data.multisig = "0x1234567890abcdef1234567890abcdef12345678"
        mock_chain_data.token = 123
        mock_chain_data.instances = ["0xabcdef1234567890abcdef1234567890abcdef12"]
        mock_chain_config.chain_data = mock_chain_data
        
        mock_service.chain_configs = {"gnosis": mock_chain_config}
        
        service = TritonService(mock_operate, "test_config_id")
        
        assert service is not None
        assert service.service_id == 123
        assert service.agent_address == "0xabcdef1234567890abcdef1234567890abcdef12"
        assert service.service_safe == "0x1234567890abcdef1234567890abcdef12345678"