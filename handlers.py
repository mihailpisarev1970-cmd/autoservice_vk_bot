import io
import json
import base64
import asyncio
import urllib.request
import aiohttp
from datetime import datetime, date
from PIL import Image

from vkbottle.bot import BotLabeler, Message
from vkbottle import GroupEventType
from vkbottle.modules import logger

from config import settings
import baserow_client
from states import BookingStates, AIDiagnosticStates
from keyboards import (
    get_main_keyboard, get_maps_keyboard, build_calendar_keyboard, 
    build_time_slots_keyboard, MENU_BUTTONS
)

labeler = BotLabeler()
AVAILABLE_TIME_SLOTS = ["09:00", "11:00", "13:00", "15:00", "17:00", "19:00"]

def get_dispenser():
    return labeler.custom_rules["state_dispenser"]

async def reset_state(peer_id: int):
    """Безопасный сброс состояния без KeyError."""
    try:
        current_state = await get_dispenser().get(peer_id)
        if current_state:
            await get_dispenser().delete(peer_id)
    except Exception:
        pass

# --- НАДЕЖНАЯ ЗАГРУЗКА МЕДИАФАЙЛОВ ИЗ ВК ---
def download_bytes_sync(url: str) -> bytes:
    """Синхронная загрузка байтов через urllib в обход сетевых сбоев aiohttp."""
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()

async def download_file_bytes(url: str) -> bytes:
    """Асинхронная неблокирующая обертка."""
    return await asyncio.to_thread(download_bytes_sync, url)

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ИИ ---
async def transcribe_voice_bytes(audio_bytes: bytes) -> str:
    url = f"{settings.POLZA_BASE_URL.rstrip('/')}/audio/transcriptions"
    headers = {"Authorization": f"Bearer {settings.POLZA_API_KEY}"}
    
    data = aiohttp.FormData()
    data.add_field(
        name='file',
        value=audio_bytes,
        filename='voice.ogg',
        content_type='audio/ogg'
    )
    data.add_field(name='model', value='openai/whisper-1')

    try:
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, data=data) as response:
                if response.status == 200:
                    res_json = await response.json()
                    return res_json.get("text", "")
                err = await response.text()
                logger.error(f"❌ [DEBUG AI Voice Error]: {response.status} - {err}")
    except Exception as e:
        logger.error(f"❌ [DEBUG AI Voice Exception]: {e}")
    return ""

async def ask_polza_ai_multimodal(content_input) -> str:
    url = f"{settings.POLZA_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.POLZA_API_KEY}",
        "Content-Type": "application/json"
    }

    if isinstance(content_input, str):
        content_payload = [{"type": "text", "text": content_input}]
    else:
        content_payload = content_input

    payload = {
        "model": settings.AI_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Ты старший мастер-приёмщик автосервиса 'Восток'. "
                    "ПРАВИЛА ОТВЕТА:\n"
                    "1. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО здороваться (не пиши 'Здравствуйте', 'Приветствую' и т.д.). Начинай ответ СРАЗУ с сути проблемы.\n"
                    "2. Ответ структурируй по блокам:\n"
                    "• Вероятные причины: 2-3 наиболее частые поломки при таких симптомах.\n"
                    "• Опасность для авто: можно ли аккуратно доехать своим ходом или лучше не рисковать / нужен эвакуатор.\n"
                    "• Что проверим в сервисе: конкретные узлы (ходовая на люфты, компьютерный сканер, замер давления и т.д.).\n"
                    "3. В самом конце напиши: 'Для точной локализации проблемы и оценки стоимости ремонта нажмите «📅 Записаться на ТО» в меню ниже.'\n"
                    "4. Тон профессиональный, чёткий, автомобильный, без лишней воды. Не используй HTML-теги, используй обычные переносы строк и знаки списка."
                )
            },
            {"role": "user", "content": content_payload}
        ],
        "temperature": 0.3
    }

    try:
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
                err_text = await response.text()
                logger.error(f"❌ [DEBUG AI Chat Error]: Статус {response.status}, Ответ: {err_text}")
                return "⚠️ Сервер диагностики временно перегружен. Запишитесь на осмотр к мастеру через кнопку «📅 Записаться на ТО»."
    except Exception as e:
        logger.error(f"❌ [DEBUG AI Chat Exception]: {e}")
        return "⚠️ Не удалось подключиться к серверу диагностики. Рекомендуем записаться через главное меню."

# --- ОСНОВНЫЕ КОМАНДЫ ---
@labeler.message(text=["/start", "Начать", "начать", "Start", "start"])
async def cmd_start(message: Message):
    user = await message.ctx_api.users.get(user_ids=[message.from_id])
    user_name = user[0].first_name if user else "клиент"
    await reset_state(message.peer_id)
    await message.answer(
        f"Здравствуйте, {user_name}!\n"
        "Вас приветствует автосервис «Восток».\n"
        "Выберите интересующий раздел меню ниже:",
        keyboard=get_main_keyboard()
    )

@labeler.message(text="📍 Адрес и контакты")
async def show_contacts(message: Message):
    await reset_state(message.peer_id)
    text = (
        "📍 Автосервис «Восток»\n"
        "г. Санкт-Петербург, Невский пр., д. 1\n"
        "📞 Тел: +7 (812) 000-00-00\n"
        "⏰ 09:00 - 21:00 (без вых.)\n\n"
        "Маршрут на картах:"
    )
    await message.answer(text, keyboard=get_maps_keyboard())

@labeler.message(text="👨‍🔧 Связаться с деж. мастером")
async def call_duty_master(message: Message):
    await reset_state(message.peer_id)
    text = (
        "👨‍🔧 Дежурный мастер на связи:\n"
        "VK: vk.com/id_мастера\n"
        "Прямой телефон: +7 (812) 111-22-33"
    )
    await message.answer(text, keyboard=get_main_keyboard())

@labeler.message(text="💰 Прайс-лист")
async def show_price_list(message: Message):
    await reset_state(message.peer_id)
    text = (
        "💰 Ориентировочный прайс-лист:\n\n"
        "• Компьютерная диагностика — от 1 500 ₽\n"
        "• Замена масла и фильтра — от 1 200 ₽\n"
        "• Замена передних колодок — от 1 800 ₽\n"
        "• Регламентное ТО — от 4 500 ₽\n\n"
        "Точная стоимость зависит от марки и модели автомобиля."
    )
    await message.answer(text, keyboard=get_main_keyboard())

# --- ИИ-ДИАГНОСТИКА ---
@labeler.message(text="🤖 ИИ-диагностика")
async def ai_diagnostic(message: Message):
    await get_dispenser().set(message.peer_id, AIDiagnosticStates.WAITING_FOR_SYMPTOMS)
    text = (
        "🛠 Режим умной автодиагностики\n\n"
        "Опишите симптомы любым удобным способом:\n"
        "• Напишите текст с описанием проблемы (марка, модель, симптомы)\n"
        "• Отправьте фото (приборной панели с ошибкой или узла)\n"
        "• Отправьте голосовое сообщение с рассказом о поломке\n\n"
        "Вы можете в любой момент нажать любую кнопку меню ниже для выхода."
    )
    await message.answer(text, keyboard=get_main_keyboard())

@labeler.message(state=AIDiagnosticStates.WAITING_FOR_SYMPTOMS)
async def process_symptoms(message: Message):
    if message.text in MENU_BUTTONS:
        await reset_state(message.peer_id)
        return

    # 1. Проверка на голосовое сообщение
    audio_msg = next((att.audio_message for att in message.attachments if att.audio_message), None)
    if audio_msg:
        await message.answer("🎧 Распознаю голосовое сообщение и анализирую...")
        voice_url = audio_msg.link_mp3 or audio_msg.link_ogg
        try:
            voice_data = await download_file_bytes(voice_url)
            recognized_text = await transcribe_voice_bytes(voice_data)
            if not recognized_text:
                await message.answer("⚠️ Не удалось разобрать голосовое сообщение. Напишите, пожалуйста, текстом.", keyboard=get_main_keyboard())
                return

            ai_reply = await ask_polza_ai_multimodal(f"Пользователь надиктовал голосом симптомы: {recognized_text}")
            await reset_state(message.peer_id)
            await message.answer(f"🗣 Распознано: «{recognized_text}»\n\n{ai_reply}", keyboard=get_main_keyboard())
            return
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки голосового: {e}")
            await message.answer("⚠️ Не удалось загрузить голосовое сообщение. Попробуйте еще раз или напишите текстом.", keyboard=get_main_keyboard())
            return

    # 2. Проверка на фото
    photo = next((att.photo for att in message.attachments if att.photo), None)
    if photo:
        await message.answer("📷 Анализирую изображение...")
        largest_size = sorted(photo.sizes, key=lambda s: getattr(s, "width", 0) * getattr(s, "height", 0))[-1]
        photo_url = largest_size.url

        try:
            photo_bytes = await download_file_bytes(photo_url)

            try:
                image = Image.open(io.BytesIO(photo_bytes))
                if image.mode in ("RGBA", "P"):
                    image = image.convert("RGB")
                image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
                buffer = io.BytesIO()
                image.save(buffer, format="JPEG", quality=75, optimize=True)
                compressed_bytes = buffer.getvalue()
            except Exception:
                compressed_bytes = photo_bytes

            base64_image = base64.b64encode(compressed_bytes).decode('utf-8')
            caption = message.text or "Оцени состояние по фотографии, укажи возможные ошибки или причины."

            content_blocks = [
                {"type": "text", "text": caption},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]

            ai_reply = await ask_polza_ai_multimodal(content_blocks)
            await reset_state(message.peer_id)
            await message.answer(ai_reply, keyboard=get_main_keyboard())
            return
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки фото: {e}")
            await message.answer("⚠️ Не удалось загрузить фотографию. Попробуйте отправить повторно.", keyboard=get_main_keyboard())
            return

    # 3. Текстовое описание
    if message.text:
        await message.answer("🔧 Анализирую симптомы, пожалуйста, подождите...")
        ai_reply = await ask_polza_ai_multimodal(message.text.strip())
        await reset_state(message.peer_id)
        await message.answer(ai_reply, keyboard=get_main_keyboard())

# --- ЗАПИСЬ НА ТО ---
@labeler.message(text="📅 Записаться на ТО")
async def start_booking(message: Message):
    kb = build_calendar_keyboard()
    await get_dispenser().set(message.peer_id, BookingStates.WAITING_FOR_DATE)
    await message.answer("Выберите удобную дату визита:", keyboard=kb)

# Обработка нажатий инлайн-кнопок
@labeler.raw_event(GroupEventType.MESSAGE_EVENT, dataclass=dict)
async def handle_callback(event: dict):
    payload = event.get("object", {}).get("payload", {})
    user_id = event.get("object", {}).get("user_id")
    peer_id = event.get("object", {}).get("peer_id")
    event_id = event.get("object", {}).get("event_id")
    conversation_message_id = event.get("object", {}).get("conversation_message_id")

    api = labeler.custom_rules.get("api")
    cmd = payload.get("cmd")

    if cmd == "ignore":
        await api.messages.send_message_event_answer(
            event_id=event_id, user_id=user_id, peer_id=peer_id
        )
        return

    if cmd == "change_date":
        kb = build_calendar_keyboard()
        await get_dispenser().set(peer_id, BookingStates.WAITING_FOR_DATE)
        await api.messages.edit(
            peer_id=peer_id,
            conversation_message_id=conversation_message_id,
            message="Выберите удобную дату визита:",
            keyboard=kb
        )
        await api.messages.send_message_event_answer(
            event_id=event_id, user_id=user_id, peer_id=peer_id
        )
        return

    if cmd == "date":
        chosen_date_str = payload.get("val")
        chosen_date = date.fromisoformat(chosen_date_str)

        await api.messages.send_message_event_answer(
            event_id=event_id, user_id=user_id, peer_id=peer_id
        )

        existing_rows = await baserow_client.get_appointments_by_date(chosen_date_str)
        booked_hours = []
        for r in existing_rows:
            dt_raw = r.get("Data_Time")
            if dt_raw:
                dt_clean = dt_raw.split("+")[0].replace("Z", "")
                for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M"):
                    try:
                        dt_obj = datetime.strptime(dt_clean, fmt)
                        booked_hours.append(dt_obj.strftime("%H:%M"))
                        break
                    except ValueError:
                        continue

        free_slots = [slot for slot in AVAILABLE_TIME_SLOTS if slot not in booked_hours]

        if not free_slots:
            kb = build_calendar_keyboard()
            await api.messages.edit(
                peer_id=peer_id,
                conversation_message_id=conversation_message_id,
                message=f"❌ На {chosen_date.strftime('%d.%m.%Y')} все места заняты.\nВыберите другую дату:",
                keyboard=kb
            )
            return

        await get_dispenser().set(
            peer_id, 
            BookingStates.WAITING_FOR_TIME, 
            chosen_date=chosen_date_str
        )

        time_kb = build_time_slots_keyboard(free_slots)
        await api.messages.edit(
            peer_id=peer_id,
            conversation_message_id=conversation_message_id,
            message=f"📅 Выбрана дата: {chosen_date.strftime('%d.%m.%Y')}\nТеперь выберите свободное время визита:",
            keyboard=time_kb
        )
        return

    if cmd == "time":
        chosen_time = payload.get("val")
        state_data = await get_dispenser().get(peer_id)
        chosen_date_str = state_data.payload.get("chosen_date")

        await get_dispenser().set(
            peer_id,
            BookingStates.WAITING_FOR_NAME,
            chosen_date=chosen_date_str,
            chosen_time=chosen_time
        )

        await api.messages.send_message_event_answer(
            event_id=event_id, user_id=user_id, peer_id=peer_id
        )

        chosen_date_formatted = datetime.strptime(chosen_date_str, "%Y-%m-%d").strftime("%d.%m.%Y")
        await api.messages.edit(
            peer_id=peer_id,
            conversation_message_id=conversation_message_id,
            message=f"⏱ Вы выбрали: {chosen_date_formatted} в {chosen_time}\n\nДля подтверждения записи введите ваше Имя и Фамилию:"
        )

# Пошаговый сбор данных
@labeler.message(state=BookingStates.WAITING_FOR_NAME)
async def process_name(message: Message):
    if message.text in MENU_BUTTONS:
        await reset_state(message.peer_id)
        return

    state = await get_dispenser().get(message.peer_id)
    await get_dispenser().set(
        message.peer_id,
        BookingStates.WAITING_FOR_CAR,
        chosen_date=state.payload["chosen_date"],
        chosen_time=state.payload["chosen_time"],
        client_name=message.text.strip()
    )
    await message.answer("Укажите марку и модель автомобиля:", keyboard=get_main_keyboard())

@labeler.message(state=BookingStates.WAITING_FOR_CAR)
async def process_car(message: Message):
    if message.text in MENU_BUTTONS:
        await reset_state(message.peer_id)
        return

    state = await get_dispenser().get(message.peer_id)
    await get_dispenser().set(
        message.peer_id,
        BookingStates.WAITING_FOR_TROUBLE,
        chosen_date=state.payload["chosen_date"],
        chosen_time=state.payload["chosen_time"],
        client_name=state.payload["client_name"],
        client_car=message.text.strip()
    )
    await message.answer("Опишите неисправность или причину обращения:", keyboard=get_main_keyboard())

@labeler.message(state=BookingStates.WAITING_FOR_TROUBLE)
async def process_trouble(message: Message):
    if message.text in MENU_BUTTONS:
        await reset_state(message.peer_id)
        return

    state = await get_dispenser().get(message.peer_id)
    trouble_desc = message.text.strip()
    data = state.payload

    time_part = data["chosen_time"] if ":" in data["chosen_time"] else f"{data['chosen_time']}:00"
    iso_datetime = f"{data['chosen_date']}T{time_part}:00+03:00"

    await baserow_client.create_appointment(
        client_name=data["client_name"],
        date_time_iso=iso_datetime,
        notes=trouble_desc,
        avto=data["client_car"],
        vk_user_id=message.from_id
    )

    await reset_state(message.peer_id)
    chosen_dt = datetime.strptime(f"{data['chosen_date']} {time_part}", "%Y-%m-%d %H:%M")

    await message.answer(
        f"✅ Вы успешно записаны!\n\n"
        f"📅 Дата: {chosen_dt.strftime('%d.%m.%Y')}\n"
        f"⏰ Время: {chosen_dt.strftime('%H:%M')}\n"
        f"👤 Клиент: {data['client_name']}\n"
        f"🚗 Автомобиль: {data['client_car']}\n"
        f"🛠 Причина обращения: {trouble_desc}\n\n"
        f"Ждём вас в назначенное время!",
        keyboard=get_main_keyboard()
    )

# --- ПРОВЕРКА СТАТУСА ---
@labeler.message(text="🔍 Статус ремонта")
async def check_status(message: Message):
    await reset_state(message.peer_id)
    appointment = await baserow_client.get_latest_client_appointment(message.from_id)

    if not appointment:
        await message.answer("У вас пока нет активных обращений.", keyboard=get_main_keyboard())
        return

    raw_dt = appointment.get("Data_Time", "") or ""
    date_part, time_part = "—", "—"
    if raw_dt:
        dt_clean = raw_dt.split("+")[0].replace("Z", "")
        for fmt in ("%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
            try:
                dt_obj = datetime.strptime(dt_clean, fmt)
                date_part = dt_obj.strftime("%d.%m.%Y")
                time_part = dt_obj.strftime("%H:%M")
                break
            except ValueError:
                continue

    client_name = appointment.get("Name") or "Не указан"
    avto_name = appointment.get("Avto") or "Не указан"

    status_raw = appointment.get("Status")
    if isinstance(status_raw, list) and status_raw:
        status_text = status_raw[0].get("value", "Запланирован визит")
    elif isinstance(status_raw, dict):
        status_text = status_raw.get("value", "Запланирован визит")
    elif status_raw:
        status_text = str(status_raw)
    else:
        status_text = "Запланирован визит"

    notes_raw = appointment.get("Notes", "") or ""
    if "[VK:" in notes_raw and "]" in notes_raw:
        trouble_text = notes_raw.split("]", 1)[-1].strip()
    else:
        trouble_text = notes_raw.strip()

    response_text = (
        f"📋 Данные вашей записи:\n\n"
        f"📅 Дата: {date_part}\n"
        f"⏰ Время: {time_part}\n"
        f"👤 Клиент: {client_name}\n"
        f"🚗 Автомобиль: {avto_name}\n"
        f"🛠 Причина обращения: {trouble_text or 'Не указана'}\n"
        f"📌 Статус ремонта: {status_text}"
    )

    await message.answer(response_text, keyboard=get_main_keyboard())