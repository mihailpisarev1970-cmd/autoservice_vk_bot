from vkbottle import BaseStateGroup

class BookingStates(BaseStateGroup):
    WAITING_FOR_DATE = 1
    WAITING_FOR_TIME = 2
    WAITING_FOR_NAME = 3
    WAITING_FOR_CAR = 4
    WAITING_FOR_TROUBLE = 5

class AIDiagnosticStates(BaseStateGroup):
    WAITING_FOR_SYMPTOMS = 1