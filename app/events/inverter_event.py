from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class InverterEvent(BaseModel):

    inverter_id: int = Field(..., description="ID inwertera z bazy")
    serial_number: str = Field(..., description="Numer seryjny inwertera z bazy SQLA")

    active_power: Optional[float] = Field(
        None, description="Bieżąca moc czynna (W) pobrana z API Huawei"
    )

    status: str = Field(..., description="updated | failed")

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Czas wygenerowania eventu (UTC)",
    )

    error_message: Optional[str] = Field(
        None, description="Treść błędu w przypadku status='failed'"
    )

    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
        }
    }
