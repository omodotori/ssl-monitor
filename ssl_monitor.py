import ssl
import socket
import os
import requests
import json
import logging
from dotenv import load_dotenv
from datetime import datetime, timezone
import time

STATE_FILE = "ssl_state.json"
LOG_FILE = "ssl_monitor.log"
EXPIRY_THRESHOLD_DAYS = 5


load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
DOMAINS = [d.strip() for d in os.getenv("DOMAINS", "").split(",") if d.strip()]


logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Утилиты для состояния уведомлений
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Не удалось загрузить state: {e}")
    return {}

def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Не удалось сохранить state: {e}")

# Проверка валидности токена
def validate_bot():
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN не задан в .env")
        return False
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe", timeout=10)
        if not r.ok:
            logging.error(f"Telegram getMe вернул ошибку: {r.status_code} {r.text}")
            return False
        data = r.json()
        if not data.get("ok"):
            logging.error(f"Telegram getMe ok=false: {data}")
            return False
        logging.info("Telegram token успешно проверен.")
        return True
    except Exception as e:
        logging.error(f"Ошибка при проверке токена Telegram: {e}")
        return False

# Получаем дату истечения сертификата
def get_certificate_expiry(domain, retries=3, delay=2):
    for attempt in range(1, retries + 1):
        try:
            context = ssl.create_default_context()
            with socket.create_connection((domain, 443), timeout=15) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
                    expiry = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
                    return expiry.replace(tzinfo=timezone.utc)
        except Exception as e:
            logging.error(f"Попытка {attempt} для {domain} не удалась: {e}")
            if attempt < retries:
                time.sleep(delay)
            else:
                logging.error(f"Не удалось получить сертификат для {domain} после {retries} попыток")
                return None

# отправка Telegram-сообщения (с проверкой)
def send_telegram_message(text, retries=3, delay=2):
    if not BOT_TOKEN or not CHAT_ID:
        logging.error("BOT_TOKEN или CHAT_ID не заданы. Пропускаем отправку.")
        return False
    for attempt in range(1, retries + 1):
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {"chat_id": CHAT_ID, "text": text}
            r = requests.post(url, data=payload, timeout=10)
            if r.ok and r.json().get("ok"):
                return True
            else:
                logging.error(f"Попытка {attempt}: Telegram вернул ошибку: {r.status_code} {r.text}")
        except Exception as e:
            logging.error(f"Попытка {attempt}: исключение при отправке в Telegram: {e}")
        if attempt < retries:
            time.sleep(delay)
    logging.error("Не удалось отправить сообщение в Telegram после нескольких попыток")
    return False


# проверка доменов
def check_domains(test_mode=False):
    # если токен невалиден то не отправляем, но логируем
    bot_ok = validate_bot()
    state = load_state()

    for domain in DOMAINS:
        expiry = get_certificate_expiry(domain)
        if not expiry:
            print(f"{domain}: не удалось получить сертификат (подробности в логе)")
            continue

        days_left = (expiry - datetime.now(timezone.utc)).days
        expiry_str = expiry.strftime("%d.%m.%Y %H:%M:%S")
        log_msg = f"{domain}: истекает {expiry_str} (UTC), осталось {days_left} дней"
        print(log_msg)
        logging.info(log_msg)

        already_notified = state.get(domain, False)


        should_send = test_mode or (days_left <= EXPIRY_THRESHOLD_DAYS and not already_notified)

        if should_send:

            mode_text = "Тестовое уведомление: " if test_mode else ""
            text = f"⚠️ {mode_text}Сертификат для {domain} истекает через {days_left} дней (до {expiry_str} UTC)."
            if bot_ok:
                ok = send_telegram_message(text)
                if ok:
                    logging.info(f"Уведомление отправлено для {domain}")
                    # Если это не тест , то помечаем как отправленное
                    if not test_mode and days_left <= EXPIRY_THRESHOLD_DAYS:
                        state[domain] = True
                else:
                    logging.error(f"Не удалось отправить уведомление для {domain}")
            else:
                logging.error("Телеграм токен невалиден — сообщение не отправлено.")
        else:
            # Если срок > threshold, сбрасываем флаг чтобы уведомление могло придти позже
            if days_left > EXPIRY_THRESHOLD_DAYS and state.get(domain, False):
                state[domain] = False
                logging.info(f"Сброшен флаг уведомления для {domain} (days_left={days_left})")

    save_state(state)

if __name__ == "__main__":
    # False для реальной работы.
    check_domains(test_mode=True)