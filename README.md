
> [!CAUTION]
> ## Disclaimer
>
> This project is provided "as is" without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement.
>
> The authors or contributors shall not be held liable for any claim, damages, or other liabilities arising from the use of this software, whether in an action of contract, tort, or otherwise.
>
> Use this software at your own risk. Always verify its applicability and security for your specific use case before deployment.
>

# Triton

> [!NOTE]
> *Triton, a figure from Greek mythology and son of Poseidon, had the ability to calm and stirr the waves by blowing his conch shell.*

Triton is a Telegram bot to handle staked Olas services. Triton can help you to:
- Monitor your wallet balances (agent, safe and operator wallets) and receive an alert when they are too low.
- Check your staking status (mech requests and rewards)
- Check empty slots on staking contracts
- Claim your rewards (manual and automatic mode)
- Withdraw your OLAS

Point triton to all your trader_quickstart folder locations (they have to contain the `.operate` folder) and it will handle them.

</br>
<p align="center">
  <img width="50%" src="images/triton.jpg">
</p>

## Prepare the repo

1. Clone the repo:

    ```bash
    git clone https://github.com/valory-xyz/triton-bot.git
    cd triton
    ```

2. Prepare the virtual environment:

    ```bash
    poetry shell
    poetry install
    ```

3. Copy the env file:

    ```bash
    cp sample.env .env
    ```

    And fill in the required environment variables.

    - `GNOSIS_RPC`: a Gnosis RPC.
    - `TELEGRAM_TOKEN`: your Telegram bot API token (get one from @BotFather on Telegram).
    - `CHAT_ID`: your Telegram chat id. Easiest way to get it is to open your session on Telegram web and checking the url while having "Saved messages" chat open.
    - `OPERATE_USER_PASSWORD`: Password of the operator user account.
    - `COINGECKO_API_KEY`: optional, only needed to check your rewards' value.
    - `WITHDRAWAL_ADDRESS`: optional. An address to send your rewards to.
    - `AGENT_BALANCE_THRESHOLD`: if the agent balance goes lower than this, you will receive an alert.
    - `SAFE_BALANCE_THRESHOLD`: if the safe balance goes lower than this, you will receive an alert.
    - `MANUAL_CLAIM`: enable manual claiming command. Defaults to true.
    - `AUTOCLAIM`: enable automatic claiming command (claims once per month). Defaults to false.
    - `AUTOCLAIM_DAY`: day of the month for the autoclaim task to run.
    - `AUTOCLAIM_HOUR_UTC`: UTC hour for the autoclaim task to run.
    - `LOCAL_TIMEZONE`: Local timezone for the time shown in the alerts.

    Make sure you start your bot by sending `/start` command to it on Telegram.

4. Edit `config.yaml` and add the path to your trader_quickstart folders. Multiple instances can be added.


## Run Triton as a python script

1. Copy the env file:

    ```bash
    poetry run python run.py
    ```

## Run Triton as a systemd service

1. Install:

    ```bash
    make install
    ```

2. Verify it is working:
    ```bash
    systemctl status triton.service
    ```

## Useful commands

```bash
make install  # install the service (systemd)
make start    # start the service (systemd)
make stop     # stop the service (systemd)
make logs     # see the service logs (systemd)
make update   # pull the latest version, reinstall and restart the service if needed (systemd)
```

## What it looks like



<p align="center">
  <img src="images/screencap.jpg" alt="Imagen 1" width="40%"/>
  <img src="images/screencap2.jpg" alt="Imagen 2" width="40%"/>
</p>
