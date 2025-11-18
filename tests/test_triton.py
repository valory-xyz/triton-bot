"""Tests for triton.py"""

import asyncio
import os
import re
from unittest.mock import AsyncMock, Mock, patch, mock_open

import pytest
import yaml
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from operate.operate_types import Chain


class TestTritonBot:
    """Test cases for Triton Telegram bot"""

    @pytest.fixture
    def mock_triton_app(self, mock_config, mock_service):
        """
        Mock the Triton application and capture handlers for direct execution.

        Args:
            handler_name: Name of the handler to execute (e.g., 'staking_status', 'balance', 'claim')

        Returns:
            A callable that executes the specified handler
        """
        def _create_mock_app(handler_name=None):
            captured_handlers = {}
            captured_jobs = {}

            # Mock the Application and its components
            mock_app = Mock()
            mock_builder = Mock()
            mock_job_queue = Mock()

            # Configure the builder chain
            mock_builder.token.return_value = mock_builder
            mock_builder.post_init.return_value = mock_builder
            mock_builder.build.return_value = mock_app

            # Configure the app
            mock_app.job_queue = mock_job_queue
            mock_app.run_polling = Mock()

            # Capture handlers when they're added
            def capture_handler(handler):
                if hasattr(handler, 'callback'):
                    captured_handlers[handler.callback.__name__] = handler.callback

            mock_app.add_handler.side_effect = capture_handler

            # Capture job functions when they're scheduled
            def capture_job_once(func, when):
                captured_jobs[func.__name__] = func

            def capture_job_repeating(func, interval, first):
                captured_jobs[func.__name__] = func

            def capture_job_monthly(func, day, when):
                captured_jobs[func.__name__] = func

            mock_job_queue.run_once.side_effect = capture_job_once
            mock_job_queue.run_repeating.side_effect = capture_job_repeating
            mock_job_queue.run_monthly.side_effect = capture_job_monthly

            # Mock other dependencies
            with patch('triton.triton.Application.builder', return_value=mock_builder), \
                 patch('triton.triton.yaml.safe_load', return_value=mock_config), \
                 patch('triton.triton.OperateApp') as mock_operate_app, \
                 patch('triton.triton.TritonService', return_value=mock_service), \
                 patch('builtins.open', mock_open(read_data=yaml.dump(mock_config))):

                # Mock the operate app
                mock_operate = Mock()
                mock_operate_service = Mock()
                mock_operate_service.name = "service"
                mock_operate_service.service_config_id = "service1"
                mock_operate.service_manager.return_value.get_all_services.return_value = [[
                    mock_operate_service,
                ]]
                mock_operate_app.return_value = mock_operate

                # Import and call run_triton to capture all handlers
                from triton.triton import run_triton
                run_triton()

            # Return the requested handler or job function
            if handler_name:
                if handler_name in captured_handlers:
                    return captured_handlers[handler_name]
                elif handler_name in captured_jobs:
                    return captured_jobs[handler_name]
                else:
                    available = list(captured_handlers.keys()) + list(captured_jobs.keys())
                    raise ValueError(f"Handler '{handler_name}' not found. Available: {available}")

            # Return all captured functions for inspection
            return {**captured_handlers, **captured_jobs}

        return _create_mock_app

    @pytest.fixture
    def mock_config(self):
        """Mock configuration"""
        return {
            "operators": {
                "operator1": "/path/to/operator1",
                "operator2": "/path/to/operator2",
            }
        }

    @pytest.fixture
    def mock_service(self):
        """Mock TritonService"""
        service = Mock()
        service.get_staking_status.return_value = {
            "accrued_rewards": "10.5 OLAS",
            "mech_requests_this_epoch": "5",
            "required_mech_requests": "10",
            "epoch_end": "2025-07-21 12:00:00",
            "metadata": {
                "name": "Staking Program 1",
            }
        }
        service.check_balance.return_value = {
            "agent_eoa_native_balance": 0.5,
            "service_safe_native_balance": 2.0,
            "service_safe_olas_balance": 100.0,
            "master_eoa_native_balance": 1.5,
            "master_safe_native_balance": 3.0,
        }
        service.claim_rewards.return_value = 12445
        service.withdraw_rewards.return_value = ("0x789ghi012jkl", 50.0)
        service.agent_address = "0xagent123"
        service.service_safe = "0xsafe456"
        service.master_wallet.crypto.address = "0xmaster789"
        service.master_wallet.safes = {Chain.GNOSIS: "0xmastersafe012"}
        service.withdrawal_address = "0xwithdraw345"
        service.service.home_chain = "gnosis"
        return service

    @pytest.fixture
    def mock_update(self):
        """Mock Telegram Update"""
        update = Mock(spec=Update)
        update.message = Mock()
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        """Mock Telegram Context"""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.bot = Mock()
        context.bot.send_message = AsyncMock()
        context.job_queue = Mock()
        context.job_queue.jobs.return_value = []
        return context

    def test_mock_triton_app_list_all_handlers(self, mock_triton_app):
        """Test that mock_triton_app can list all available handlers"""
        with patch.dict(os.environ, {
            'TELEGRAM_TOKEN': 'test_token',
            'CHAT_ID': '123456789',
            'OPERATE_USER_PASSWORD': 'test_password',
        }), patch('triton.triton.dotenv.load_dotenv'):
            
            # Get all handlers and jobs
            all_functions = mock_triton_app()
            
            # Verify that we have the expected handlers
            expected_handlers = ['staking_status', 'balance', 'claim', 'withdraw', 'slots', 'scheduled_jobs']
            expected_jobs = ['start', 'balance_check', 'autoclaim']
            
            for handler in expected_handlers:
                assert handler in all_functions, f"Handler '{handler}' not found"
            
            for job in expected_jobs:
                assert job in all_functions, f"Job '{job}' not found"

    def test_start_job(self, mock_triton_app, mock_context):
        """Test start job using the mock_triton_app fixture"""
        # Get the start job function
        start_job = mock_triton_app('start')
        
        with patch('triton.triton.CHAT_ID', '123456789'):
            # Execute the job
            asyncio.run(start_job(mock_context))
        
        # Verify the call
        mock_context.bot.send_message.assert_called_once_with(
            chat_id="123456789",
            text="Triton has started",
        )

    def test_staking_status_handler(self, mock_triton_app, mock_update):
        """Test staking_status handler using the mock_triton_app fixture"""
        # Get the staking_status handler
        staking_status_handler = mock_triton_app('staking_status')

        with (
            patch('triton.triton.get_olas_price', return_value=2.5),
            patch('triton.chain.requests.get', side_effect=Mock(
                status_code=200,
                json=lambda: {"name": "Staking Program 1"}
            )),
        ):
            # Execute the handler
            asyncio.run(staking_status_handler(mock_update, None))
        
        # Verify the call
        mock_update.message.reply_text.assert_called_once()
        mock_update.message.called_once_with(
            disable_web_page_preview=True,
            parse_mode=ParseMode.MARKDOWN,
            text="""[operator1-service] 10.5 OLAS [5/10]
Staking program: Staking Program 1
Next epoch: 2025-07-21 12:00:00

[operator2-service] 10.5 OLAS [5/10]
Staking program: Staking Program 1
Next epoch: 2025-07-21 12:00:00

Total rewards = 21 OLAS [$52.5]""",
        )

    def test_balance_handler(self, mock_triton_app, mock_update):
        """Test balance handler using the mock_triton_app fixture"""
        # Get the balance handler
        balance_handler = mock_triton_app('balance')
        
        # Execute the handler
        asyncio.run(balance_handler(mock_update, None))
        
        # Verify the call
        mock_update.message.reply_text.assert_called_once_with(
            disable_web_page_preview=True,
            parse_mode=ParseMode.MARKDOWN,
            text="""\\[operator1-service]
[Agent EOA](https://gnosisscan.io/address/0xagent123) = 0.5 xDAI
[Service Safe](https://gnosisscan.io/address/0xsafe456) = 2 xDAI  100 OLAS
[Master EOA](https://gnosisscan.io/address/0xmaster789) = 1.5 xDAI
[Master Safe](https://gnosisscan.io/address/0xmastersafe012) = 3 xDAI

\\[operator2-service]
[Agent EOA](https://gnosisscan.io/address/0xagent123) = 0.5 xDAI
[Service Safe](https://gnosisscan.io/address/0xsafe456) = 2 xDAI  100 OLAS
[Master EOA](https://gnosisscan.io/address/0xmaster789) = 1.5 xDAI
[Master Safe](https://gnosisscan.io/address/0xmastersafe012) = 3 xDAI"""
        )

    def test_claim_handler(self, mock_triton_app, mock_update):
        """Test claim handler using the mock_triton_app fixture"""
        # Get the claim handler
        claim_handler = mock_triton_app('claim')
        
        # Execute the handler
        asyncio.run(claim_handler(mock_update, None))
        
        # Verify the call
        mock_update.message.reply_text.assert_called_once_with(
            text="""[operator1-service] Claimed 12445 OLAS rewards into the Master safe.\n[operator2-service] Claimed 12445 OLAS rewards into the Master safe."""
        )

    def test_withdraw_handler(self, mock_triton_app, mock_update):
        """Test withdraw handler using the mock_triton_app fixture"""
        # Get the withdraw handler
        withdraw_handler = mock_triton_app('withdraw')
        
        # Execute the handler
        asyncio.run(withdraw_handler(mock_update, None))
        
        # Verify the call
        mock_update.message.reply_text.assert_called_once_with(
            disable_web_page_preview=True,
            parse_mode=ParseMode.MARKDOWN,
            text="""\\[operator1-service] Sent the [withdrawal transaction](https://gnosisscan.io/tx/0x789ghi012jkl). 50 OLAS sent from the Master Safe to [0xwithdraw345](https://gnosisscan.io/address/0xwithdraw345) #withdraw

\\[operator2-service] Sent the [withdrawal transaction](https://gnosisscan.io/tx/0x789ghi012jkl). 50 OLAS sent from the Master Safe to [0xwithdraw345](https://gnosisscan.io/address/0xwithdraw345) #withdraw""",
        )

    def test_slots_handler(self, mock_triton_app, mock_update):
        """Test slots handler using the mock_triton_app fixture"""
        # Get the slots handler
        slots_handler = mock_triton_app('slots')

        with (
            patch('triton.chain.load_contract', return_value=Mock()),
            patch('triton.chain.len', return_value=0),
        ):
            # Execute the handler
            asyncio.run(slots_handler(mock_update, None))
        
        # Verify the call
        mock_update.message.reply_text.assert_called_once_with(
            text="""[Hobbyist (100 OLAS)] 100 available slots
[Hobbyist 2 (500 OLAS)] 50 available slots
[Expert (1k OLAS)] 20 available slots
[Expert 2 (1k OLAS)] 40 available slots
[Expert 3 (2k OLAS)] 20 available slots
[Expert 4 (10k OLAS)] 26 available slots
[Expert 5 (10k OLAS)] 26 available slots
[Expert 6 (1k OLAS)] 40 available slots
[Expert 7 (10k OLAS)] 26 available slots"""
        )

    def test_ip_handler(self, mock_triton_app, mock_update):
        """Test ip handler using the mock_triton_app fixture"""
        ip_handler = mock_triton_app('ip_address')

        class MockResponse:
            """Mock aiohttp response"""

            async def text(self):
                return "1.2.3.4"

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

        class MockSession:
            """Mock aiohttp ClientSession"""

            def get(self, url):
                assert url == "https://api.ipify.org"
                return MockResponse()

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

        with patch('triton.triton.aiohttp.ClientSession', return_value=MockSession()):
            asyncio.run(ip_handler(mock_update, None))

        mock_update.message.reply_text.assert_called_once_with(
            text="Public IP address: 1.2.3.4"
        )

    def test_scheduled_jobs_handler_empty(self, mock_triton_app, mock_update, mock_context):
        """Test scheduled_jobs handler with no jobs using the mock_triton_app fixture"""
        mock_context.job_queue.jobs.return_value = []
        
        # Get the scheduled_jobs handler
        scheduled_jobs_handler = mock_triton_app('scheduled_jobs')
        
        # Execute the handler
        asyncio.run(scheduled_jobs_handler(mock_update, mock_context))
        
        # Verify the call
        mock_update.message.reply_text.assert_called_once_with("No scheduled jobs")

    @pytest.mark.parametrize(
        "agent_balance,safe_balance,master_balance,agent_threshold,safe_threshold,master_threshold,expected_messages",
        [
            # All monitored balances below their thresholds
            (0.05, 0.5, 4.0, 0.1, 1.0, 5.0, 6),
            # Only agent balance below threshold
            (0.05, 2.0, 6.0, 0.1, 1.0, 5.0, 2),
            # Only service safe balance below threshold
            (0.5, 0.5, 6.0, 0.1, 1.0, 5.0, 2),
            # Only master safe balance below threshold
            (0.5, 2.0, 4.0, 0.1, 1.0, 5.0, 2),
            # All balances above thresholds
            (0.5, 2.0, 6.0, 0.1, 1.0, 5.0, 0),
            # Edge case: exactly at thresholds
            (0.1, 1.0, 5.0, 0.1, 1.0, 5.0, 0),
            # Edge case: just below thresholds
            (0.099, 0.999, 4.999, 0.1, 1.0, 5.0, 6),
        ],
    )
    def test_balance_check_job_low_balance(
        self,
        mock_triton_app,
        mock_context,
        mock_service,
        agent_balance,
        safe_balance,
        master_balance,
        agent_threshold,
        safe_threshold,
        master_threshold,
        expected_messages,
        mock_config,
    ):
        """Test balance_check job with different balance scenarios using the mock_triton_app fixture"""
        # Configure the mock service with the test balances
        mock_service.check_balance.return_value = {
            "agent_eoa_native_balance": agent_balance,
            "service_safe_native_balance": safe_balance,
            "service_safe_olas_balance": 100.0,
            "master_eoa_native_balance": 1.5,
            "master_safe_native_balance": master_balance,
        }

        # Mock the thresholds in the environment
        with patch.dict(os.environ, {
            'AGENT_BALANCE_THRESHOLD': str(agent_threshold),
            'SAFE_BALANCE_THRESHOLD': str(safe_threshold),
            'MASTER_SAFE_BALANCE_THRESHOLD': str(master_threshold),
        }):
            # Reload constants to pick up new thresholds
            import importlib
            import triton.constants
            importlib.reload(triton.constants)
            
            # Get the balance_check job function
            balance_check_job = mock_triton_app('balance_check')
            
            # Execute the job
            asyncio.run(balance_check_job(mock_context))
        
        # Verify the correct number of messages were sent
        assert mock_context.bot.send_message.call_count == expected_messages
        
        if expected_messages > 0:
            # Verify the content of the messages
            call_args_list = mock_context.bot.send_message.call_args_list
            sent_messages = [call[1]["text"] for call in call_args_list]
            
            # Check if agent balance message was sent (when agent_balance < agent_threshold)
            if agent_balance < agent_threshold:
                for operator in mock_config['operators']:
                    assert (
                        f"[{operator}-service] [Agent EOA](https://gnosisscan.io/address/{mock_service.agent_address}) balance is {agent_balance:g} xDAI"
                        in sent_messages
                    ), f"Expected agent balance message for balance {agent_balance}"

            # Check if safe balance message was sent (when safe_balance < safe_threshold)
            if safe_balance < safe_threshold:
                for operator in mock_config['operators']:
                    assert (
                        f"[{operator}-service] [Service Safe](https://gnosisscan.io/address/{mock_service.service_safe}) balance is {safe_balance:g} xDAI"
                        in sent_messages
                    ), f"Expected safe balance message for balance {safe_balance}"

            # Check if master safe message was sent (when master_balance < master_threshold)
            if master_balance < master_threshold:
                master_safe_address = mock_service.master_wallet.safes[Chain.GNOSIS]
                for operator in mock_config['operators']:
                    assert (
                        f"[{operator}-service] [Master Safe](https://gnosisscan.io/address/{master_safe_address}) balance is {master_balance:g} xDAI"
                        in sent_messages
                    ), f"Expected master safe message for balance {master_balance}"

            # Verify message formatting
            for call in call_args_list:
                assert call[1]['parse_mode'] == "Markdown"
                assert call[1]['disable_web_page_preview'] is True

    def test_autoclaim_job(self, mock_triton_app, mock_context):
        """Test autoclaim job when enabled/disabled using the mock_triton_app fixture"""
        with patch('triton.triton.AUTOCLAIM', False):
            # Get the autoclaim job function
            autoclaim_job = mock_triton_app('autoclaim')
            
            # Execute the job
            asyncio.run(autoclaim_job(mock_context))
            
            # Verify the correct number of calls
            assert mock_context.bot.send_message.call_count == 0
            
        with patch('triton.triton.AUTOCLAIM', True):
            # Get the autoclaim job function
            autoclaim_job = mock_triton_app('autoclaim')
            
            # Execute the job
            asyncio.run(autoclaim_job(mock_context))
            
            # Verify the correct number of calls
            assert mock_context.bot.send_message.call_count == 1
            
            # Verify the content of the messages when autoclaim is enabled
            call_args_list = mock_context.bot.send_message.call_args_list
            assert len(call_args_list) == 1
            call_kwargs = call_args_list[0].kwargs
            assert call_kwargs == {
                "chat_id": call_kwargs['chat_id'],
                "text": f"""\\[operator1-service] (Autoclaim) Sent the [withdrawal transaction](https://gnosisscan.io/tx/0x789ghi012jkl). 50 OLAS sent from the Safe to [0xwithdraw345](https://gnosisscan.io/address/0xwithdraw345) #withdraw

\\[operator2-service] (Autoclaim) Sent the [withdrawal transaction](https://gnosisscan.io/tx/0x789ghi012jkl). 50 OLAS sent from the Safe to [0xwithdraw345](https://gnosisscan.io/address/0xwithdraw345) #withdraw""",
                "parse_mode": ParseMode.MARKDOWN,
                "disable_web_page_preview": True,
            }
