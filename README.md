
### Структура проекта

```
ssl-monitor/
├─ ssl_monitor.py         # скрипт для мониторинга
├─ .gitignore
├─ README.md
├─ .env.example
```

---

### `.gitignore`

```gitignore
# Секретные данные
.env

# Файл состояния уведомлений
ssl_state.json

# Логи скрипта
ssl_monitor.log

# Кэш Python
__pycache__/
```

---

### `.env.example`

```env
# Telegram Bot Token
BOT_TOKEN=

# Telegram Chat ID
CHAT_ID=

# Домен(ы) для мониторинга через запятую
DOMAINS=example.com,example2.com
```

---

### `README.md`

````markdown
# SSL Monitor

Скрипт для мониторинга сроков действия SSL-сертификатов доменов и отправки уведомлений в Telegram.

## Установка

1. Клонируем репозиторий:

```bash
git clone https://github.com/username/ssl-monitor.git
cd ssl-monitor
````

2. Создаём файл `.env` на основе `.env.example` или просто меняем название `.env.example`:

```bash
cp .env.example .env
```

и заполняем его своими значениями:

```ini
BOT_TOKEN=ваш_telegram_bot_token
CHAT_ID=ваш_chat_id
DOMAINS=example.com,example2.com
```

3. Устанавливаем зависимости:

```bash
pip install requests python-dotenv
```

## Запуск

Для обычной работы:

```bash
python ssl_monitor.py
```

Для теста Telegram уведомлений (не меняя реальные статусы), откройте Python внутри проекта и вызовите:

```python
from ssl_monitor import check_domains

# тестовый запуск
check_domains(test_mode=True)

## Функционал

* Проверка SSL-сертификатов всех доменов из `.env`.
* Отправка уведомлений в Telegram, если осталось ≤ 5 дней.
* Логирование в `ssl_monitor.log`.
* Хранение состояния уведомлений в `ssl_state.json`, чтобы не спамить.
* Тестовый режим для проверки уведомлений.