"""Constants"""

import os

import dotenv

from triton.tools import str_to_bool

dotenv.load_dotenv(override=True)

# Constants
GNOSISSCAN_URL = "https://gnosisscan.io"
GNOSISSCAN_ADDRESS_URL = GNOSISSCAN_URL + "/address/{address}"
GNOSISSCAN_TX_URL = GNOSISSCAN_URL + "/tx/{tx_hash}"
AGENT_BALANCE_THRESHOLD = float(os.getenv("AGENT_BALANCE_THRESHOLD", "0.1"))
SAFE_BALANCE_THRESHOLD = float(os.getenv("SAFE_BALANCE_THRESHOLD", "1"))
MASTER_SAFE_BALANCE_THRESHOLD = float(os.getenv("MASTER_SAFE_BALANCE_THRESHOLD", "5"))
AUTOCLAIM = str_to_bool(os.getenv("AUTOCLAIM", "false"))
MANUAL_CLAIM = str_to_bool(os.getenv("MANUAL_CLAIM", "true"))
OLAS_TOKEN_ADDRESS_GNOSIS = "0xcE11e14225575945b8E6Dc0D4F2dD4C570f79d9f"
AUTOCLAIM_DAY = int(os.getenv("AUTOCLAIM_DAY", "1"))
AUTOCLAIM_HOUR_UTC = int(os.getenv("AUTOCLAIM_HOUR_UTC", "9"))
LOCAL_TIMEZONE = os.getenv("LOCAL_TIMEZONE", "UTC")
OPERATE_USER_PASSWORD = os.getenv("OPERATE_USER_PASSWORD")
STAKING_CONTRACTS = {
    "Hobbyist (100 OLAS)": {
        "address": "0x389b46c259631acd6a69bde8b6cee218230bae8c",
        "slots": 100,
    },
    "Hobbyist 2 (500 OLAS)": {
        "address": "0x238eb6993b90a978ec6aad7530d6429c949c08da",
        "slots": 50,
    },
    "Expert (1k OLAS)": {
        "address": "0x5344b7dd311e5d3dddd46a4f71481bd7b05aaa3e",
        "slots": 20,
    },
    "Expert 2 (1k OLAS)": {
        "address": "0xb964e44c126410df341ae04b13ab10a985fe3513",
        "slots": 40,
    },
    "Expert 3 (2k OLAS)": {
        "address": "0x80fad33cadb5f53f9d29f02db97d682e8b101618",
        "slots": 20,
    },
    "Expert 4 (10k OLAS)": {
        "address": "0xad9d891134443b443d7f30013c7e14fe27f2e029",
        "slots": 26,
    },
    "Expert 5 (10k OLAS)": {
        "address": "0xe56df1e563de1b10715cb313d514af350d207212",
        "slots": 26,
    },
    "Expert 6 (1k OLAS)": {
        "address": "0x2546214aee7eea4bee7689c81231017ca231dc93",
        "slots": 40,
    },
    "Expert 7 (10k OLAS)": {
        "address": "0xd7a3c8b975f71030135f1a66e9e23164d54ff455",
        "slots": 26,
    },
}
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")
