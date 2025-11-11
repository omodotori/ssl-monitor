import ssl
import socket
import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timezone
import logging

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
DOMAINS = [d.strip() for d in os.getenv('DOMAINS', '').split(',')]


logging.basicConfig(
    filename="ssl_monitor.log",
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)


# Получаем дату истечения SSL-сертификата для домена
def get_certificate_expiry(domain):
    try:
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                expiry_date = datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")
                return expiry_date.replace(tzinfo=timezone.utc)
    except Exception as e:
        logging.error(f"Ошибка при получении сертификата {domain}: {e}")
        return None


# Отправляем сообщение в Telegram
def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": message}
        requests.post(url, data=data, timeout=5)
    except Exception as e:
        logging.error(f"Ошибка при отправке Telegram-сообщения: {e}")


# Проверяем все домены и уведомляем, если сертификат истекает от 5 дней
def check_domains(test_mode=False):
    for domain in DOMAINS:
        expiry_date = get_certificate_expiry(domain)
        if not expiry_date:
            continue

        days_left = (expiry_date - datetime.now(timezone.utc)).days
        expiry_str = expiry_date.strftime('%d.%m.%Y %H:%M:%S')

        log_msg = f"{domain}: истекает {expiry_str}, осталось {days_left} дней"
        print(log_msg)
        logging.info(log_msg)

        # Отправка уведомления
        if test_mode or days_left <= 5:
            send_telegram_message(
                f"⚠️ {'Тестовое уведомление: ' if test_mode else ''}"
                f"Сертификат для {domain} истекает через {days_left} дней (до {expiry_str})."
            )

if __name__ == "__main__":
    # test_mode=True для проверки уведомлений, False для реальной работы
    check_domains()