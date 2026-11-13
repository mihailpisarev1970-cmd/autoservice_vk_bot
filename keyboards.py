from datetime import date, timedelta
from typing import List
from vkbottle import Keyboard, KeyboardButtonColor, Text, Callback, OpenLink

MONTH_NAMES = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря"
]

WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

MENU_BUTTONS = [
    "📅 Записаться на ТО", "🔍 Статус ремонта",
    "📍 Адрес и контакты", "🤖 ИИ-диагностика",
    "👨‍🔧 Связаться с деж. мастером", "💰 Прайс-лист"
]

LATITUDE = 59.9372
LONGITUDE = 30.3130

def get_main_keyboard() -> str:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("📅 Записаться на ТО"), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("🔍 Статус ремонта"), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    kb.add(Text("📍 Адрес и контакты"), color=KeyboardButtonColor.SECONDARY)
    kb.add(Text("🤖 ИИ-диагностика"), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text("👨‍🔧 Связаться с деж. мастером"), color=KeyboardButtonColor.SECONDARY)
    kb.add(Text("💰 Прайс-лист"), color=KeyboardButtonColor.SECONDARY)
    return kb.get_json()

def get_maps_keyboard() -> str:
    kb = Keyboard(inline=True)
    kb.add(OpenLink(f"https://yandex.ru/maps/?pt={LONGITUDE},{LATITUDE},pm2rdm&z=18&l=map", "📍 Яндекс Карты"))
    kb.add(OpenLink(f"https://2gis.ru/spb/geo/5348651268307283?m={LONGITUDE}%2C{LATITUDE}%2F18", "🧭 2ГИС"))
    return kb.get_json()

def build_calendar_keyboard(offset_days: int = 0) -> str:
    """
    Генерирует аккуратную клавиатуру на ближайшие дни.
    Укладывается ровно в 4-5 рядов (лимит ВК - до 6 рядов).
    """
    kb = Keyboard(inline=True)
    today = date.today() + timedelta(days=offset_days)
    
    # Предлагаем запись на ближайшие 8 дней (по 2 кнопки в ряд = 4 ряда)
    for i in range(8):
        current_day = today + timedelta(days=i)
        weekday_name = WEEKDAYS_RU[current_day.weekday()]
        label = f"{weekday_name}, {current_day.day} {MONTH_NAMES[current_day.month]}"
        
        kb.add(
            Callback(label, {"cmd": "date", "val": current_day.isoformat()}),
            color=KeyboardButtonColor.PRIMARY
        )
        if i % 2 == 1 and i < 7:
            kb.row()
            
    return kb.get_json()

def build_time_slots_keyboard(free_slots: List[str]) -> str:
    kb = Keyboard(inline=True)
    count = 0
    for slot in free_slots:
        kb.add(Callback(f"🕒 {slot}", {"cmd": "time", "val": slot}), color=KeyboardButtonColor.POSITIVE)
        count += 1
        if count % 2 == 0 and count < len(free_slots):
            kb.row()

    kb.row()
    kb.add(Callback("⬅️ Выбрать другую дату", {"cmd": "change_date"}), color=KeyboardButtonColor.NEGATIVE)
    return kb.get_json()