# 🤖 VK Bot — Автосервис: запись на ТО, ИИ-диагностика авто, статус ремонта

> **Кратко:** VK-бот для автосервиса на Python — онлайн-запись на ТО через календарь, ИИ-диагностика неисправностей по тексту, фото и голосовому сообщению (LLM + Whisper), статус ремонта и синхронизация заявок с CRM Baserow.

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg?style=for-the-badge&logo=python)](https://www.python.org/)
[![vkbottle 3.0](https://img.shields.io/badge/vkbottle-3.0-green.svg?style=for-the-badge)](https://github.com/vkbottle/vkbottle)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?style=for-the-badge&logo=docker)](https://www.docker.com/)
[![MIT License](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
[![VK Bot](https://img.shields.io/badge/VK-ВКонтакте-blue.svg?style=for-the-badge&logo=vk)](https://vk.com/)
[![Baserow](https://img.shields.io/badge/CRM-Baserow-5193E9.svg?style=for-the-badge)](https://baserow.io/)

**VK-бот автосервиса с ИИ-диагностикой** (текст, фото, голос), **записью на ТО** через интерактивный календарь и **статусом ремонта** из CRM Baserow. Решение для автосервисов, которые хотят автоматизировать приём клиентов через сообщество ВКонтакте.

## ✨ Возможности

- **📅 Запись на ТО** — пошаговый сценарий: выбор даты на ближайшие 8 дней → выбор свободного времени (занятые слоты подтягиваются из CRM) → имя → автомобиль → причина обращения. Заявка автоматически создаётся в Baserow.
- **🤖 ИИ-диагностика** — консультация «старшего мастера-приёмщика» на основе LLM (шлюз Polza.ai):
  - текстом (марка, модель, симптомы),
  - **фото** (приборная панель, узел — изображение сжимается и отправляется в модель),
  - **голосовым сообщением** (транскрибация через Whisper-совместимый endpoint).
- **🔍 Статус ремонта** — клиент видит свою последнюю запись и текущий статус из Baserow.
- **📍 Адрес и контакты** — кнопки перехода в Яндекс Карты и 2ГИС.
- **💰 Прайс-лист** и **👨‍🔧 связь с дежурным мастером**.

## 🏗 Структура проекта

```
autoservice_vk_bot/
├── main.py             # Точка входа: создаёт бота и запускает polling
├── config.py           # Загрузка настроек из .env
├── handlers.py         # Обработчики сообщений, callback-кнопок, ИИ-логика
├── keyboards.py        # Клавиатуры: главное меню, календарь, слоты времени, карты
├── states.py           # Состояния диалога (запись на ТО, ИИ-диагностика)
├── baserow_client.py   # HTTP-клиент Baserow (создание/чтение записей)
├── requirements.txt    # Python-зависимости
├── Dockerfile          # Образ для запуска в контейнере
├── docker-compose.yml  # Оркестрация запуска
├── .env.example        # Шаблон переменных окружения
├── .gitignore          # Файлы, исключённые из git
└── .dockerignore       # Файлы, исключённые из Docker-образа
```

## 📋 Требования

- **Python 3.11+** (в Docker используется 3.11, локально проверено на 3.13)
- или **Docker + Docker Compose** для запуска в контейнере
- Токен сообщества ВКонтакте — [инструкция VK API](https://dev.vk.com/ru/api/access-token/getting-started)
- API-ключ шлюза Polza.ai (для ИИ-диагностики)
- Доступ к Baserow (URL + токен + ID таблицы)

## ⚙️ Настройка

### 1. Токен сообщества ВКонтакте

1. Откройте управление сообществом → **Работа с API** → вкладка **Ключи доступа**.
2. Создайте ключ доступа с правами: `messages`, `photos` (права на сообщения достаточны для работы бота).
3. В настройках сообщества подключите **Работа с API** и разрешите **Получать сообщения** (Long Poll API) — [документация VK: Long Poll для ботов](https://dev.vk.com/ru/api/bots/long-poll).

### 2. API-ключ Polza.ai

Зарегистрируйтесь в шлюзе [Polza.ai](https://polza.ai), создайте API-ключ (`pza_...`). Ключ используется для чат-модели и транскрибации голоса.

### 3. Таблица Baserow

Создайте базу с таблицей (по умолчанию ожидается ID `278`) со следующими колонками:

| Колонка      | Тип                       | Назначение                                   |
|--------------|---------------------------|----------------------------------------------|
| `Name`       | Текст                     | Имя и фамилия клиента                        |
| `Data_Time`  | Дата и время              | Дата и время визита                          |
| `Avto`       | Текст                     | Марка и модель автомобиля                    |
| `Notes`      | Текст                     | Причина обращения (с меткой `[VK:id]`)       |
| `Status`     | Выбор (single/multi select) | Статус ремонта, начальное значение «Запланирован визит» |

Получите **токен Baserow**: Настройки профиля → **Токены** → Создать токен.

### 4. Переменные окружения

Скопируйте шаблон и заполните своими значениями:

```bash
cp .env.example .env        # Windows: copy .env.example .env
```

| Переменная          | Описание                                      | Пример                                  |
|---------------------|-----------------------------------------------|-----------------------------------------|
| `VK_TOKEN`          | Ключ доступа сообщества ВК                    | `vk1.a.xxxx`                            |
| `POLZA_API_KEY`     | API-ключ шлюза Polza.ai                       | `pza_xxxx`                              |
| `POLZA_BASE_URL`    | Базовый URL API                               | `https://api.polza.ai/v1`               |
| `AI_MODEL`          | Модель для чата                               | `openai/gpt-4o-mini`                    |
| `BASEROW_URL`       | URL вашего инстанса Baserow                   | `https://crm.example.com`               |
| `BASEROW_TOKEN`     | Токен доступа к Baserow                       | `your_baserow_database_token`           |
| `BASEROW_TABLE_ID`  | ID таблицы записей                            | `278`                                   |

> ⚠️ **Безопасность:** файл `.env` содержит секреты и **никогда не попадает в git** (исключён в `.gitignore` и `.dockerignore`). Не публикуйте его содержимое и при утечке сразу пересоздавайте ключи.

## 🚀 Запуск

### Вариант A. Локально (Windows / Linux / macOS)

```bash
# 1. Клонируйте репозиторий
git clone https://github.com/<ваш_логин>/autoservice_vk_bot.git
cd autoservice_vk_bot

# 2. Создайте виртуальное окружение
python -m venv venv

# 3. Активируйте его
# Windows (PowerShell):
venv\Scripts\Activate.ps1
# Windows (CMD):
venv\Scripts\activate.bat
# Linux / macOS:
source venv/bin/activate

# 4. Установите зависимости
pip install -r requirements.txt

# 5. Создайте файл .env (см. раздел «Настройка»)
cp .env.example .env
# ... и заполните значения

# 6. Запустите бота
python main.py
```

При успешном запуске в консоли появится: `🚀 Бот автосервиса для ВКонтакте запущен!`

> **Примечание для Windows:** в `main.py` уже установлен `WindowsSelectorEventLoopPolicy`, исправляющий типовые проблемы с SSL и таймаутом семафора на Windows.

### Вариант B. Docker

```bash
# 1. Убедитесь, что файл .env создан и заполнен (см. выше)

# 2. Соберите и запустите контейнер
docker compose up --build -d

# 3. Проверьте логи
docker compose logs -f

# 4. Остановка
docker compose down
```

Бот перезапускается автоматически (`restart: always`).

## 🧪 Проверка работы

1. Откройте сообщество ВК напрямую и нажмите **«Начать»** или отправьте `/start`.
2. Появится главное меню — проверьте каждый пункт.
3. **Запись на ТО:** выберите дату → время → заполните данные → найдите созданную строку в Baserow.
4. **ИИ-диагностика:** отправьте текст, фото или голосовое сообщение с описанием проблемы.
5. **Статус ремонта:** измените `Status` в Baserow и проверьте ответ бота.

## 📦 Стек

| Компонент        | Технология                          |
|------------------|-------------------------------------|
| Язык             | Python 3.11+                        |
| VK API           | [vkbottle](https://github.com/vkbottle/vkbottle) 3.0 (pinned) |
| Асинхронность    | asyncio, aiohttp                    |
| ИИ               | Шлюз Polza.ai (OpenAI-совместимый), Whisper для голоса |
| CRM              | Baserow (REST API)                  |
| Изображения      | Pillow (сжатие фото перед отправкой в ИИ) |
| Контейнеризация  | Docker, Docker Compose              |

## 📚 Документация и полезные ссылки

| Что | Ссылка |
|-----|--------|
| vkbottle — репозиторий (исходники, примеры) | https://github.com/vkbottle/vkbottle |
| vkbottle — документация (хаб) | https://vkbottle.readthedocs.io/ru/latest/ |
| vkbottle — первый бот (туториал) | https://vkbottle.readthedocs.io/ru/latest/tutorial/first-bot/ |
| vkbottle — клавиатуры | https://vkbottle.readthedocs.io/ru/latest/tools/keyboard/ |
| vkbottle — FAQ | https://vkbottle.readthedocs.io/ru/latest/tutorial/faq/ |
| VK API — работа с ботами сообществ | https://dev.vk.com/ru/api/bots/getting-started |
| VK API — получение ключа доступа | https://dev.vk.com/ru/api/access-token/getting-started |
| VK API — Long Poll для ботов | https://dev.vk.com/ru/api/bots/long-poll |
| vkbottle на PyPI | https://pypi.org/project/vkbottle/ |

> ℹ️ Обратите внимание: проект использует **зафиксированную версию `vkbottle==3.0.0`** (см. `requirements.txt`), а публичная документация на Read the Docs описывает актуальную **4.x**. Ссылки ведут только на существующие разделы; часть разделов документации 4.x по API отличается от 3.0 — сверяйтесь с исходниками тега 3.x в репозитории vkbottle.

## 🔧 Возможные проблемы

| Проблема | Решение |
|----------|---------|
| `SSL: CERTIFICATE_VERIFY_FAILED` на Windows | Убедитесь, что используется Python 3.11+ и активирован `WindowsSelectorEventLoopPolicy` (уже есть в `main.py`) |
| Бот не отвечает | Проверьте токен `VK_TOKEN`, права ключа и включённый Long Poll API в сообществе |
| `401 Unauthorized` от Baserow | Проверьте `BASEROW_TOKEN` и `BASEROW_URL` |
| Пустой ответ ИИ | Проверьте `POLZA_API_KEY` и доступность `POLZA_BASE_URL` |
| Занятое время всё равно предлагается | Проверьте формат колонки `Data_Time` в Baserow (ожидается дата/время) |
| Ошибка в Docker: нет `.env` | Создайте `.env` рядом с `docker-compose.yml` перед `docker compose up` |

## 📄 Лицензия

MIT — подробности в файле [LICENSE](LICENSE).

## ⭐ Поддержите проект

Если проект полезен — поставьте звезду, создайте issue с идеей или пришлите pull request.

---

## 🔎 Ключевые слова / Keywords (SEO)

`VK бот автосервис`, `бот ВКонтакте запись на ТО`, `запись на техобслуживание бот`,
`ИИ диагностика автомобиля`, `нейросеть диагностика авто по фото`, `распознавание голоса Whisper`,
`чат-бот для автосервиса Python`, `vkbottle 3.0 бот`, `VK API Long Poll бот`,
`Baserow CRM интеграция`, `онлайн-запись клиентов`, `автоматизация автосервиса`,
`OpenAI-совместимый шлюз LLM`, `asyncio aiohttp бот`, `VK Long Poll бот без токена вебхука`,
`car service booking bot`, `VK community chatbot`, `AI car diagnostics`,
`automotive service chatbot`, `appointment scheduling bot`, `python chatbot crm integration`.

