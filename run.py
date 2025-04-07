import requests
import secrets
import sys
import time
from datetime import datetime
from fake_useragent import UserAgent
from colorama import init
from src.utils import pth, htm, countdown_timer
from src.logger import info, success, warning, error, step, line, _log_to_file
from src.config import read_config

init(autoreset=True)
ua = UserAgent()

class SolpotAutomation:
    BASE_URL = "https://solpot.com"
    FILES = {"ACCOUNTS": "cookies.txt"}
    ENDPOINTS = {
        "profile": "/api/profile/info",
        "client_seed": "/api/profile/updateClientSeed",
        "daily_case": "/api/daily-case/open",
        "transactions": "/api/profile/transactions"
    }

    def __init__(self):
        self.cfg = read_config()
        self.accounts = self._load_accounts()

    def _load_accounts(self):
        try:
            with open(self.FILES["ACCOUNTS"], "r", encoding="utf-8") as file:
                accounts = [line.strip() for line in file if line.strip()]
            if not accounts:
                warning("no accounts found in cookies.txt file")
                sys.exit(1)
            return accounts
        except Exception as e:
            warning(f"error reading accounts file: {str(e)}")
            _log_to_file(f"{str(e)}")
            sys.exit(1)

    def _create_session(self, cookie):
        session = requests.Session()
        session.headers.update({
            "authority": "solpot.com",
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/json",
            "origin": self.BASE_URL,
            "user-agent": ua.random,
            "cookie": cookie,
        })
        return session

    def _get_user_profile(self, session, index):
        try:
            response = session.post(self.BASE_URL + self.ENDPOINTS["profile"])
            data = response.json()

            if data.get("success"):
                user = data["data"]["telegram"]["username"]
                referred = data["data"].get("referredBy", {})
                ref_code = referred.get("code", "N/A")
                ref_owner = referred.get("owner", "N/A")

                info(f"telegram     : {pth}@{user}")
                info(f"referred by  : {pth}{ref_code} {htm}(owner: {ref_owner})")
                return True
            else:
                error(f"account {pth}{index + 1} - failed to fetch profile: {data.get('error', 'Unknown error')}")
                _log_to_file(f"{data.get('error', 'Unknown error')}")
                return False

        except Exception as e:
            error(f"account {pth}{index + 1} - error fetching profile: {str(e)}")
            _log_to_file(f"{str(e)}")
            return False

    def _update_client_seed(self, session, index):
        try:
            if not self.cfg.get("UPDATE_CLIENT_SEED", True):
                profile_resp = session.post(self.BASE_URL + self.ENDPOINTS["profile"])
                profile_data = profile_resp.json()
                current_seed = profile_data['data'].get("clientSeed", "unknown")
                success(f"client seed change is disabled. Current seed: {pth}{current_seed}")
                return True

            new_seed = secrets.token_hex(32)
            response = session.post(self.BASE_URL + self.ENDPOINTS["client_seed"], json={"clientSeed": new_seed})
            data = response.json()

            if data.get("success"):
                success("client seed updated successfully")
                info(new_seed)
                return True
            else:
                warning(f"failed to update client seed - {data.get('error', 'Unknown error')}")
                _log_to_file(f"{data.get('error', 'Unknown error')}")
                return False

        except Exception as e:
            error(f"account {pth}{index + 1} - Error updating client seed: {str(e)}")
            return False

    def _open_daily_case(self, session, index):
        try:
            response = session.post(self.BASE_URL + self.ENDPOINTS["daily_case"], json={"demo": False})
            data = response.json()

            if data.get("success"):
                block = data["data"]["targetBlock"]
                success("daily case opened successfully!")
                info(f"target Block: {pth}{block}")
                return True
            elif "once per day" in data.get("error", ""):
                warning("daily case already claimed today")
                return True
            else:
                error(f"failed to open daily case - {data.get('error', 'Unknown error')}")
                _log_to_file(f"{data.get('error', 'Unknown error')}")
                return False
        except Exception as e:
            error(f"account {pth}{index + 1} - error opening daily case: {str(e)}")
            return False

    def _get_last_daily_reward(self, session, index):
        try:
            response = session.post(self.BASE_URL + self.ENDPOINTS["transactions"], json={"page": 1, "limit": 10})
            data = response.json()

            if not data.get("success"):
                warning(f"failed to fetch transaction history - {data.get('error', 'Unknown error')}")
                _log_to_file(f"{data.get('error', 'Unknown error')}")
                return False

            for tx in data["data"]["transactions"]["data"]:
                if tx.get("type") == "WITHDRAWAL" and \
                   tx.get("status") == "SUCCESS" and \
                   tx.get("action", {}).get("name") == "daily-reward":

                    date_utc = datetime.fromisoformat(tx["date"].replace("Z", "+00:00"))
                    success(f"last reward received: {pth}{date_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                    return True

            warning("no previous reward received found.")
            return True

        except Exception as e:
            error(f"account {pth}{index + 1} - error fetching transactions: {str(e)}")
            _log_to_file(f"{str(e)}")
            return False

    def _process_account(self, cookie, index):
        info(f"account      : {pth}{index + 1}/{len(self.accounts)}")
        session = self._create_session(cookie)

        steps = [
            self._get_user_profile,
            self._update_client_seed,
            self._open_daily_case,
            self._get_last_daily_reward
        ]

        for step in steps:
            if not step(session, index):
                return False

        return True

    def start(self):
        try:
            while True:
                try:
                    print(f"\naccounts loaded: {len(self.accounts)}\n")
                    time.sleep(3)
                    step("~" * 38)

                    for i, account in enumerate(self.accounts):
                        self._process_account(account, i)
                        if i < len(self.accounts) - 1:
                            step("~" * 38)
                            countdown_timer(self.cfg.get("DELAY_BETWEEN_ACCOUNTS", 3))

                    line()
                    info("waiting for the next cycle...")
                    countdown_timer(self.cfg.get("SECONDS_PER_DAY", 86400))

                except Exception as e:
                    error(f"cycle error: {str(e)}")
                    warning("restarting cycle in 24 hours...")
                    countdown_timer(self.cfg.get("SECONDS_PER_DAY", 86400))

        except KeyboardInterrupt:
            warning("keyboard interrupted by user")
            sys.exit(0)
        except Exception as e:
            error(f"fatal error: {str(e)}")
            _log_to_file(f"{str(e)}")
            sys.exit(1)

if __name__ == "__main__":
    bot = SolpotAutomation()
    bot.start()
