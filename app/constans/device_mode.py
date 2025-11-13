from enum import Enum


class DeviceMode(str, Enum):
    MANUAL = "MANUAL"  # ręczne włączanie/wyłączanie
    AUTO_POWER = "AUTO_POWER"  # automatyczne w oparciu o moc PV
    SCHEDULE = "SCHEDULE"  # tryb zaplanowany wg harmonogramu
