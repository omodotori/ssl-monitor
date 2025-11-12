# SSL Certificate Monitor

Скрипт для мониторинга срока действия SSL сертификатов доменов с уведомлениями в Telegram.

## Возможности

-  Проверка срока действия SSL сертификатов для списка доменов
-  Отправка уведомлений в Telegram при приближении срока истечения
-  Система состояний для предотвращения дублирования уведомлений
-  Тестовый режим для проверки работоспособности
-  Детальное логирование всех операций
-  Гибкая настройка через YAML конфигурацию

## Установка

### 1. Клонируйте репозиторий

```bash
git clone https://github.com/omodotori/ssl-monitor
cd ssl-monitor
```

### 2. Установите зависимости

```bash
pip install -r requirements.txt
```

### 3. Настройте конфигурацию

Создайте файл `config.yaml` на основе примера:

```bash
cp config.example.yaml config.yaml
```

Отредактируйте `config.yaml` и укажите:
- Токен Telegram бота
- Chat ID для получения уведомлений
- Список доменов для мониторинга
- Порог предупреждения (по умолчанию 5 дней)

## Как получить Telegram токен и chat_id

### Получение токена бота:

1. Найдите [@BotFather](https://t.me/botfather) в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям и получите токен вида `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

### Получение chat_id:

1. Напишите вашему боту любое сообщение (например, `/start`)
2. Откройте в браузере: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Найдите в ответе `"chat":{"id":123456789}` - это ваш chat_id

## Конфигурация

`config.yaml`:

```yaml
telegram:
  token: "YOUR_BOT_TOKEN"
  chat_id: YOUR_CHAT_ID

settings:
  expiry_threshold_days: 5  # Порог предупреждения в днях
  test_mode: false           # true для тестирования

domains:
  - one.com
  - two.com
  - three.com
```


### Разовая проверка

```bash
python ssl_monitor.py
```

```bash
## Тестовый режим

Для тестирования установите в `config.yaml`:

```yaml
settings:
  test_mode: true
```

В тестовом режиме уведомления отправляются для всех доменов независимо от срока действия сертификата.

После проверки нужно изменить на `false`:

```yaml
settings:
  test_mode: false
```

## Файлы

- `ssl_monitor.py` - основной скрипт
- `config.yaml` - конфигурация (не включается в git)
- `config.example.yaml` - пример конфигурации
- `ssl_state.json` - состояние уведомлений (создается автоматически)
- `ssl_monitor.log` - лог файл (создается автоматически)
- `requirements.txt` - зависимости Python

## Логи

Все операции логируются в файл `ssl_monitor.log`:

```bash
tail -f ssl_monitor.log
```

## Структура проекта

```
ssl-monitor/
├── ssl_monitor.py          # Основной скрипт
├── config.yaml             # Конфигурация (не в git)
├── config.example.yaml     # Пример конфигурации
├── requirements.txt        # Зависимости
├── README.md              # Документация
├── .gitignore             # Игнорируемые файлы
├── ssl_state.json         # Состояние (создается автоматически)
└── ssl_monitor.log        # Логи (создается автоматически)
```