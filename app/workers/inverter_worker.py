# app/workers/inverter_worker.py
import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.adapters.adapter_cache import get_adapter_for_user
from app.core.config import settings
from app.core.db import SessionLocal
from app.core.exceptions import HuaweiRateLimitException
from app.events.inverter_event import InverterEvent
from app.nats.module import nats_module
from app.repositories.inverter_power_record_repository import InverterPowerRepository
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


async def publish_inverter_event(event: InverterEvent):
    subject = f"device_communication.inverter.{event.serial_number}.production.update"

    try:
        await nats_module.publisher.publish(subject, event.model_dump(mode="json"))
        logger.info(f"NATS publish → {subject}: {event.model_dump(mode='json')}")

    except Exception as e:
        logger.error(f"Failed to publish inverter event ({event.serial_number}): {e}")


async def fetch_inverter_production_async():
    logger.info("=" * 80)
    logger.info("[Worker] Starting inverter production update cycle...")

    if not nats_module.client.connected or nats_module.client.js is None:
        await nats_module.client.connect()
        await nats_module.ensure_stream()

    db: Session = SessionLocal()

    try:
        user_repo = UserRepository()
        users = user_repo.get_all_with_installations_and_inverters(db)
        logger.info(f"[Worker] Retrieved {len(users)} users with installations & inverters.")

        if not users:
            logger.warning("[Worker] No users with installations found.")
            return

        for user in users:

            if not user.huawei_username or not user.huawei_password_encrypted:
                logger.warning(f"[Worker] Skipping user {user.email}: missing Huawei credentials.")
                continue

            try:
                adapter = get_adapter_for_user(db, user)
            except Exception as e:
                logger.error(f"[Worker] Could not initialize HuaweiAdapter for {user.email}: {e}")
                continue

            for installation in user.installations:
                for inverter in installation.inverters:

                    serial = inverter.serial_number
                    inverter_id = inverter.id

                    logger.info(
                        f"[Worker] Processing inverter {serial} (ID={inverter_id}) "
                        f"for user {user.email}..."
                    )

                    try:
                        production_data = adapter.get_production(serial)
                        logger.debug(f"[Worker] Production data for {serial}: {production_data}")

                    except HuaweiRateLimitException as e:
                        logger.warning(f"[Worker] Huawei rate limit for inverter {serial}: {e}")

                        event = InverterEvent(
                            inverter_id=inverter_id,
                            serial_number=serial,
                            active_power=None,
                            status="failed",
                            error_message="Huawei API rate limit exceeded",
                        )
                        await publish_inverter_event(event)

                        await asyncio.sleep(1.2)
                        continue

                    except Exception as e:
                        logger.exception(
                            f"[Worker] Failed to fetch production data for inverter {serial}: {e}"
                        )

                        event = InverterEvent(
                            inverter_id=inverter_id,
                            serial_number=serial,
                            active_power=None,
                            status="failed",
                            error_message=str(e),
                        )
                        await publish_inverter_event(event)
                        continue

                    active_power = production_data[0].get("dataItemMap", {}).get("active_power")
                    if active_power is None:
                        msg = f"Inverter {serial} returned no 'active_power'"
                        logger.warning(f"[Worker] {msg}")

                        event = InverterEvent(
                            inverter_id=inverter_id,
                            serial_number=serial,
                            active_power=None,
                            status="failed",
                            error_message=msg,
                        )
                        await publish_inverter_event(event)
                        continue

                    repo = InverterPowerRepository(db)
                    latest = repo.get_latest_for_inverter(inverter_id)

                    if latest:
                        latest_value = round(float(latest.active_power), 2)
                    else:
                        latest_value = None

                    current_value = round(float(active_power), 2)

                    if latest_value is not None and latest_value == current_value:
                        logger.info(
                            f"[Worker] Skipping DB save for inverter {serial}: power unchanged ({current_value})"
                        )
                    else:
                        repo.create_record(inverter_id, current_value)
                        logger.info(
                            f"[Worker] Saved new power record for inverter {serial}: {current_value}"
                        )

                    event = InverterEvent(
                        inverter_id=inverter_id,
                        serial_number=serial,
                        active_power=current_value,
                        status="updated",
                    )
                    await publish_inverter_event(event)

    except Exception as e:
        logger.exception(f"[Worker] Fatal worker error: {e}")

    finally:
        db.close()
        logger.info("[Worker] Finished inverter production update cycle.")
        logger.info("=" * 80)


def fetch_inverter_production():
    asyncio.run(fetch_inverter_production_async())


def start_inverter_scheduler():
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

        logger.info("Inverter production scheduler started successfully.")
        logger.info(f"Registered scheduler jobs: {scheduler.get_jobs()}")

    except Exception as e:
        logger.exception(f"Failed to start inverter scheduler: {e}")
