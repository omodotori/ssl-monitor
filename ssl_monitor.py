
import ssl
import socket
import requests
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from time import sleep
from typing import Optional, Dict, Any
import yaml


class Config:

    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = Path(config_file)
        self._config = self._load()

    def _load(self) -> Dict[str, Any]:
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Файл конфигурации {self.config_file} не найден")
        except yaml.YAMLError as e:
            raise ValueError(f"Ошибка парсинга YAML: {e}")

    @property
    def bot_token(self) -> str:
        return self._config["telegram"]["token"]

    @property
    def chat_id(self) -> int:
        return self._config["telegram"]["chat_id"]

    @property
    def domains(self) -> list:
        return self._config["domains"]

    @property
    def threshold_days(self) -> int:
        return self._config["settings"].get("expiry_threshold_days", 5)

    @property
    def test_mode(self) -> bool:
        return self._config["settings"].get("test_mode", False)


class StateManager:

    def __init__(self, state_file: str = "ssl_state.json"):
        self.state_file = Path(state_file)
        self._state = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                logging.error(f"Ошибка загрузки состояния: {e}")
        return {}

    def save(self) -> None:
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self._state, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logging.error(f"Ошибка сохранения состояния: {e}")

    def get_last_notified(self, domain: str) -> Optional[int]:
        return self._state.get(domain, {}).get("last_notified_days")

    def update(self, domain: str, days_left: int) -> None:
        if domain not in self._state:
            self._state[domain] = {}
        self._state[domain]["last_notified_days"] = days_left
        self._state[domain]["last_check"] = datetime.now(timezone.utc).isoformat()


class TelegramNotifier:
    API_URL = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self, token: str, chat_id: int):
        self.token = token
        self.chat_id = chat_id

    def _request(self, method: str, params: Dict = None, retries: int = 3) -> Optional[Dict]:
        url = self.API_URL.format(token=self.token, method=method)

        for attempt in range(1, retries + 1):
            try:
                response = requests.post(url, json=params, timeout=10)
                if response.ok:
                    return response.json()
                logging.error(f"Попытка {attempt}: Telegram API ошибка: {response.status_code} {response.text}")
            except requests.RequestException as e:
                logging.error(f"Попытка {attempt}: Ошибка запроса: {e}")

            if attempt < retries:
                sleep(2)

        return None

    def validate(self) -> bool:
        if not self.token:
            logging.error("BOT_TOKEN не задан")
            return False

        result = self._request("getMe")
        if result and result.get("ok"):
            username = result.get("result", {}).get("username", "unknown")
            logging.info(f"Telegram токен валиден. Бот: @{username}")
            return True

        logging.error("Ошибка проверки Telegram токена")
        return False

    def send_message(self, text: str) -> bool:
        params = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML"
        }

        result = self._request("sendMessage", params)
        if result and result.get("ok"):
            logging.info("Сообщение успешно отправлено в Telegram")
            return True

        logging.error("Не удалось отправить сообщение в Telegram")
        return False


class SSLChecker:
    @staticmethod
    def get_expiry_date(domain: str, port: int = 443, retries: int = 3) -> Optional[datetime]:
        for attempt in range(1, retries + 1):
            try:
                context = ssl.create_default_context()
                with socket.create_connection((domain, port), timeout=15) as sock:
                    with context.wrap_socket(sock, server_hostname=domain) as secure_sock:
                        cert = secure_sock.getpeercert()
                        expiry = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
                        return expiry.replace(tzinfo=timezone.utc)
            except Exception as e:
                logging.error(f"Попытка {attempt} для {domain}: {e}")
                if attempt < retries:
                    sleep(2)

        logging.error(f"Не удалось получить сертификат для {domain} после {retries} попыток")
        return None

    @staticmethod
    def calculate_days_left(expiry: datetime) -> int:
        return (expiry - datetime.now(timezone.utc)).days


class SSLMonitor:

    def __init__(self, config_file: str = "config.yaml", log_file: str = "ssl_monitor.log"):
        # Настройка логирования
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )

        self.config = Config(config_file)
        self.state = StateManager()
        self.notifier = TelegramNotifier(self.config.bot_token, self.config.chat_id)
        self.checker = SSLChecker()

    def _print_header(self) -> None:
        print("=" * 60)
        print(f"Запуск проверки SSL сертификатов: {datetime.now()}")
        print(f"Режим: {'ТЕСТ' if self.config.test_mode else 'ПРОДАКШН'}")
        print(f"Порог предупреждения: {self.config.threshold_days} дней")
        print("=" * 60)

    def _should_notify(self, domain: str, days_left: int) -> bool:
        if self.config.test_mode:
            print(f"  🧪 Тестовый режим - отправляю уведомление")
            return True

        if days_left > self.config.threshold_days:
            print(f"  ✓ Сертификат в норме ({days_left} > {self.config.threshold_days} дней)")
            return False

        last_notified = self.state.get_last_notified(domain)

        if last_notified is None or days_left < last_notified:
            print(f"  ⚠️  Сертификат истекает через {days_left} дней - отправляю уведомление")
            return True

        print(f"  ℹ️  Уведомление уже отправлялось для {last_notified} дней")
        return False

    def _format_message(self, domain: str, days_left: int, expiry_str: str) -> str:
        if self.config.test_mode:
            return (
                f"🧪 <b>ТЕСТ</b>\n\n"
                f"⚠️ Сертификат для <b>{domain}</b> истекает через <b>{days_left} дней</b>\n"
                f"📅 До: {expiry_str} UTC"
            )
        return (
            f"⚠️ <b>ВНИМАНИЕ!</b>\n\n"
            f"Сертификат для <b>{domain}</b> истекает через <b>{days_left} дней</b>\n"
            f"📅 До: {expiry_str} UTC"
        )

    def _check_domain(self, domain: str) -> None:
        print(f"\n🔍 Проверяю домен: {domain}")

        expiry = self.checker.get_expiry_date(domain)
        if not expiry:
            print(f"  ❌ Не удалось получить сертификат (подробности в логе)")
            return

        days_left = self.checker.calculate_days_left(expiry)
        expiry_str = expiry.strftime("%d.%m.%Y %H:%M:%S")

        print(f"  ✅ Сертификат действителен до: {expiry_str} UTC")
        print(f"  📅 Осталось дней: {days_left}")
        logging.info(f"{domain}: истекает {expiry_str} (UTC), осталось {days_left} дней")

        if self._should_notify(domain, days_left):
            message = self._format_message(domain, days_left, expiry_str)

            if self.notifier.send_message(message):
                print(f"  ✉️  Уведомление отправлено в Telegram")
                self.state.update(domain, days_left)
            else:
                print(f"  ❌ Не удалось отправить уведомление в Telegram")

    def run(self) -> None:
        """Запустить мониторинг всех доменов"""
        self._print_header()

        if not self.notifier.validate():
            print("❌ Не удалось проверить Telegram бота. Проверьте токен.")
            return

        for domain in self.config.domains:
            self._check_domain(domain)

        self.state.save()

        print("\n" + "=" * 60)
        print("Проверка завершена")
        print("=" * 60)


def main():
    try:
        monitor = SSLMonitor()
        monitor.run()
    except Exception as e:
        logging.error(f"Критическая ошибка: {e}")
        print(f"❌ Ошибка: {e}")
        raise


if __name__ == "__main__":
    main()