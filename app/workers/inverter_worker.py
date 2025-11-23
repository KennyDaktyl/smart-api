import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.adapters.adapter_cache import get_adapter_for_user
from app.core.config import settings
from app.core.db import SessionLocal
from app.core.nats_client import NatsClient
from app.models.inverter import Inverter
from app.repositories.inverter_power_record_repository import InverterPowerRepository

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


async def publish_status(
    nc: NatsClient,
    inverter_id: int,
    serial: str,
    power: float | None,
    status: str,
    error_message: str | None = None,
):
    """Helper do wysyłania komunikatu do NATS z informacją o stanie inwertera."""
    message = {
        "inverter_id": inverter_id,
        "serial_number": serial,
        "active_power": power,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "error_message": error_message,
    }

    subject = f"inverter.{serial}.production"

    try:
        await nc.publish(subject=subject, message=message)
        logger.info(f"📡 Sent NATS message → {subject}: {message}")
    except Exception as e:
        logger.error(f"❌ Failed to publish NATS message for {serial}: {e}")


async def fetch_inverter_production_async():
    """Asynchroniczna wersja workera pobierającego dane z inwerterów."""
    logger.info("=" * 80)
    logger.info("[Worker] Starting inverter production update cycle...")
    db: Session = SessionLocal()
    nc = NatsClient()

    try:
        await nc.connect()

        inverters = db.query(Inverter).all()
        logger.info(f"Fetched {len(inverters)} inverters from database.")

        if not inverters:
            logger.warning("No inverters found in the database. Exiting cycle.")
            return

        repo = InverterPowerRepository(db)

        for inv in inverters:
            logger.info(f"Processing inverter {inv.serial_number} (ID: {inv.id})...")

            installation = inv.installation
            if not installation:
                message = f"Skipping inverter {inv.serial_number}: no assigned installation."
                logger.warning(message)
                await publish_status(
                    nc, inv.id, inv.serial_number, None, "failed", error_message=message
                )
                continue

            user = installation.user
            if not user or not user.huawei_username or not user.huawei_password_encrypted:
                message = f"Skipping inverter {inv.serial_number}: missing Huawei credentials."
                logger.warning(message)
                await publish_status(
                    nc, inv.id, inv.serial_number, None, "failed", error_message=message
                )
                continue

            try:
                adapter = get_adapter_for_user(db, user)
                production_data = adapter.get_production(inv.serial_number)
                logger.debug(f"Received production data: {production_data}")

                if not production_data:
                    message = f"Inverter {inv.serial_number}: no production data received."
                    logger.warning(message)
                    await publish_status(
                        nc, inv.id, inv.serial_number, None, "failed", error_message=message
                    )
                    continue

                active_power = production_data[0].get("dataItemMap", {}).get("active_power")

                if active_power is None:
                    message = f"Inverter {inv.serial_number}: missing 'active_power' in response."
                    logger.warning(message)
                    await publish_status(
                        nc, inv.id, inv.serial_number, None, "failed", error_message=message
                    )
                    continue

                # ✅ Zapis do bazy
                repo.create_record(inverter_id=inv.id, active_power=active_power)
                logger.info(
                    f"Successfully recorded production for inverter {inv.serial_number}: {active_power:.2f} W"
                )

                # ✅ Wysłanie statusu do NATS
                await publish_status(nc, inv.id, inv.serial_number, active_power, "updated")

            except Exception as e:
                message = f"Error fetching production for inverter {inv.serial_number}: {e}"
                logger.exception(message)
                await publish_status(
                    nc, inv.id, inv.serial_number, None, "failed", error_message=message
                )

    except Exception as e:
        logger.exception(f"Fatal error during inverter production update cycle: {e}")
    finally:
        db.close()
        await nc.close()
        logger.info("[Worker] Finished inverter production update cycle.")
        logger.info("=" * 80)


def fetch_inverter_production():
    """Wrapper do uruchamiania async funkcji w APSchedulerze."""
    asyncio.run(fetch_inverter_production_async())


def start_inverter_scheduler():
    """Uruchamia harmonogram dla odpytywania inwerterów co określony interwał."""
    logger.info(
        f"Initializing inverter production scheduler (interval = {settings.GET_PRODUCTION_INTERVAL_MINUTES} min)..."
    )

    try:
        scheduler.add_job(
            fetch_inverter_production,
            "interval",
            minutes=settings.GET_PRODUCTION_INTERVAL_MINUTES,
            id="fetch_inverter_production",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("✅ Inverter production scheduler started successfully.")
        logger.info(f"Registered scheduler jobs: {scheduler.get_jobs()}")
    except Exception as e:
        logger.exception(f"❌ Failed to start inverter scheduler: {e}")
