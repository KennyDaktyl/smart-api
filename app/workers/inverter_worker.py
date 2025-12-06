# app/workers/inverter_worker.py
import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.adapters.adapter_cache import get_adapter_for_user
from app.core.config import settings
from app.core.db import SessionLocal
from app.core.exceptions import HuaweiRateLimitException
from app.events.inverter_event import InverterEvent, InverterEventPayload
from app.nats.module import nats_module
from app.repositories.inverter_power_record_repository import InverterPowerRepository
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


async def publish_inverter_event(payload: InverterEventPayload):
    subject = f"device_communication.inverter.{payload.serial_number}.production.update"
    event = InverterEvent(payload=payload)

    try:
        logger.info(
            f"[NATS] Publishing inverter event subject={subject} status={payload.status} "
            f"active_power={payload.active_power} timestamp={payload.timestamp.isoformat()}"
        )
        await nats_module.events.publish_event(subject, event=event)
        logger.info(f"NATS publish → {subject}: {event.model_dump(mode='json')}")

    except Exception as e:
        logger.error(f"Failed to publish inverter event ({event.payload.serial_number}): {e}")


async def fetch_inverter_production_async():
    logger.info("=" * 80)
    logger.info("[Worker] Starting inverter production update cycle...")

    logger.info("[Worker] Ensuring NATS connection + stream...")
    if not nats_module.client.connected or nats_module.client.js is None:
        await nats_module.client.connect()
    await nats_module.ensure_stream()
    logger.info(
        "[Worker] NATS connection ready "
        f"(connected={nats_module.client.connected}, js_ready={nats_module.client.js is not None})"
    )

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
                    repo = InverterPowerRepository(db)

                    logger.info(
                        f"[Worker] Processing inverter {serial} (ID={inverter_id}) "
                        f"for user {user.email}..."
                    )

                    try:
                        production_data = adapter.get_production(serial)
                        logger.debug(f"[Worker] Production data for {serial}: {production_data}")

                    except HuaweiRateLimitException as e:
                        logger.warning(f"[Worker] Huawei rate limit for inverter {serial}: {e}")
                        change_time = datetime.now(timezone.utc)
                        latest = repo.get_latest_for_inverter(inverter_id)
                        latest_is_none = latest and latest.active_power is None

                        if latest_is_none:
                            logger.info(
                                f"[Worker] Skipping duplicate None power for inverter {serial}"
                            )
                        else:
                            if latest and latest.active_power is not None:
                                repo.create_record(
                                    inverter_id, float(latest.active_power), timestamp=change_time
                                )
                            repo.create_record(inverter_id, None, timestamp=change_time)

                        payload = InverterEventPayload(
                            inverter_id=inverter_id,
                            serial_number=serial,
                            active_power=None,
                            status="failed",
                            error_message="Huawei API rate limit exceeded",
                            timestamp=change_time,
                        )
                        await publish_inverter_event(payload)
                        logger.error(
                            f"[Worker] Persisted None active_power for inverter {serial} at {change_time.isoformat()} "
                            f"reason=Huawei API rate limit exceeded; latest_is_none={latest_is_none}"
                        )
                        await asyncio.sleep(1.2)
                        continue

                    except Exception as e:
                        logger.exception(
                            f"[Worker] Failed to fetch production data for inverter {serial}: {e}"
                        )
                        change_time = datetime.now(timezone.utc)
                        latest = repo.get_latest_for_inverter(inverter_id)
                        latest_is_none = latest and latest.active_power is None

                        if latest_is_none:
                            logger.info(
                                f"[Worker] Skipping duplicate None power for inverter {serial}"
                            )
                        else:
                            if latest and latest.active_power is not None:
                                repo.create_record(
                                    inverter_id, float(latest.active_power), timestamp=change_time
                                )
                            repo.create_record(inverter_id, None, timestamp=change_time)
                            logger.error(
                                f"[Worker] Persisted None active_power for inverter {serial} at {change_time.isoformat()} "
                                f"reason={e}"
                            )

                        payload = InverterEventPayload(
                            inverter_id=inverter_id,
                            serial_number=serial,
                            active_power=None,
                            status="failed",
                            error_message=str(e),
                            timestamp=change_time,
                        )
                        await publish_inverter_event(payload)
                        logger.error(
                            f"[Worker] Reported failed reading for inverter {serial} at {change_time.isoformat()} "
                            f"reason={e}; latest_is_none={latest_is_none}"
                        )
                        continue

                    active_power = production_data[0].get("dataItemMap", {}).get("active_power")
                    if active_power is None:
                        msg = f"Inverter {serial} returned no 'active_power'"
                        logger.warning(f"[Worker] {msg}")
                        change_time = datetime.now(timezone.utc)
                        latest = repo.get_latest_for_inverter(inverter_id)
                        latest_is_none = latest and latest.active_power is None

                        if latest_is_none:
                            logger.info(
                                f"[Worker] Skipping duplicate None power for inverter {serial}"
                            )
                        else:
                            if latest and latest.active_power is not None:
                                repo.create_record(
                                    inverter_id, float(latest.active_power), timestamp=change_time
                                )
                            repo.create_record(inverter_id, None, timestamp=change_time)

                        payload = InverterEventPayload(
                            inverter_id=inverter_id,
                            serial_number=serial,
                            active_power=None,
                            status="failed",
                            error_message=msg,
                            timestamp=change_time,
                        )
                        await publish_inverter_event(payload)
                        logger.error(
                            f"[Worker] Persisted None active_power for inverter {serial} at {change_time.isoformat()} "
                            f"reason={msg}; latest_is_none={latest_is_none}"
                        )
                        continue

                    latest = repo.get_latest_for_inverter(inverter_id)

                    latest_value = (
                        round(float(latest.active_power), 2)
                        if latest and latest.active_power is not None
                        else None
                    )

                    current_value = round(float(active_power), 2)

                    change_time = datetime.now(timezone.utc)

                    if latest_value is not None and latest_value != current_value:
                        repo.create_record(inverter_id, latest_value, timestamp=change_time)

                    should_persist = latest_value is None or latest_value != current_value

                    if should_persist:
                        repo.create_record(inverter_id, current_value, timestamp=change_time)
                        logger.info(
                            f"[Worker] Saved new power record for inverter {serial}: {current_value}"
                        )

                        payload = InverterEventPayload(
                            inverter_id=inverter_id,
                            serial_number=serial,
                            active_power=current_value,
                            status="updated",
                            timestamp=change_time,
                        )
                        await publish_inverter_event(payload)
                        logger.info(
                            f"[Worker] Published production update event for inverter {serial}: {current_value}"
                        )
                    else:
                        logger.info(
                            f"[Worker] Power unchanged for inverter {serial}: {current_value}; plateau extended"
                        )
                        payload = InverterEventPayload(
                            inverter_id=inverter_id,
                            serial_number=serial,
                            active_power=current_value,
                            status="updated",
                            timestamp=change_time,
                        )
                        await publish_inverter_event(payload)
                        logger.info(
                            f"[Worker] Published plateau update for inverter {serial}: {current_value}"
                        )

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
