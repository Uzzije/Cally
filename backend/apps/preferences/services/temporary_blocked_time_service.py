from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TypedDict
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db import transaction
from django.utils import timezone

from apps.preferences.models.temporary_blocked_time import (
    TemporaryBlockedTime,
    TemporaryBlockedTimeSource,
)

logger = logging.getLogger(__name__)


class TemporaryBlockedTimeValidationError(Exception):
    def __init__(self, message: str, *, errors: dict[str, list[str]] | None = None) -> None:
        super().__init__(message)
        self.detail = message
        self.errors = errors or {}


class TemporaryBlockedTimeNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class TemporaryBlockedTimeCreateRequest:
    label: str
    date: str
    start: str
    end: str
    timezone: str
    source: str = TemporaryBlockedTimeSource.EMAIL_DRAFT


class NormalizedTemporaryBlockedTimeRequest(TypedDict):
    label: str
    start_time: datetime
    end_time: datetime
    timezone: str
    source: str


class TemporaryBlockedTimeService:
    hold_duration = timedelta(hours=1)

    def list_active_for_user(self, user) -> list[TemporaryBlockedTime]:
        return list(
            TemporaryBlockedTime.objects.filter(user=user, expires_at__gt=timezone.now()).order_by(
                "start_time",
                "id",
            )
        )

    def create_many_for_user(
        self,
        user,
        *,
        requests: list[TemporaryBlockedTimeCreateRequest],
    ) -> list[TemporaryBlockedTime]:
        if not isinstance(requests, list) or len(requests) == 0:
            raise TemporaryBlockedTimeValidationError(
                "Temporary blocked times payload is invalid.",
                errors={"entries": ["At least one temporary blocked time is required."]},
            )

        created_at = timezone.now()
        created_entries: list[TemporaryBlockedTime] = []

        with transaction.atomic():
            for index, request in enumerate(requests):
                normalized = self._normalize_request(index=index, request=request)
                created_entries.append(
                    TemporaryBlockedTime.objects.create(
                        user=user,
                        label=normalized["label"],
                        start_time=normalized["start_time"],
                        end_time=normalized["end_time"],
                        timezone=normalized["timezone"],
                        source=normalized["source"],
                        expires_at=created_at + self.hold_duration,
                    )
                )

        logger.info(
            "preferences.temporary_blocked_times.created user_id=%s count=%s",
            user.id,
            len(created_entries),
        )
        return created_entries

    def delete_for_user(self, user, *, public_id: str) -> None:
        deleted_count, _ = TemporaryBlockedTime.objects.filter(
            user=user, public_id=public_id
        ).delete()
        if deleted_count == 0:
            raise TemporaryBlockedTimeNotFoundError("Temporary blocked time not found.")

        logger.info(
            "preferences.temporary_blocked_time.deleted user_id=%s temp_block_id=%s",
            user.id,
            public_id,
        )

    def clear_for_user(self, user) -> int:
        deleted_count, _ = TemporaryBlockedTime.objects.filter(user=user).delete()
        logger.info(
            "preferences.temporary_blocked_times.cleared user_id=%s count=%s",
            user.id,
            deleted_count,
        )
        return deleted_count

    def expire_by_public_ids(self, *, public_ids: list[str]) -> int:
        if not public_ids:
            return 0

        deleted_count, _ = TemporaryBlockedTime.objects.filter(
            public_id__in=public_ids,
            expires_at__lte=timezone.now(),
        ).delete()
        logger.info(
            "preferences.temporary_blocked_times.expired count=%s ids=%s",
            deleted_count,
            public_ids,
        )
        return deleted_count

    def serialize(self, blocked_time: TemporaryBlockedTime) -> dict[str, str]:
        local_start_time = timezone.localtime(
            blocked_time.start_time, ZoneInfo(blocked_time.timezone)
        )
        local_end_time = timezone.localtime(blocked_time.end_time, ZoneInfo(blocked_time.timezone))
        return {
            "id": blocked_time.public_id,
            "label": blocked_time.label,
            "date": local_start_time.date().isoformat(),
            "start": local_start_time.strftime("%H:%M"),
            "end": local_end_time.strftime("%H:%M"),
            "timezone": blocked_time.timezone,
            "source": blocked_time.source,
            "created_at": blocked_time.created_at.isoformat(),
            "expires_at": blocked_time.expires_at.isoformat(),
        }

    def _normalize_request(
        self,
        *,
        index: int,
        request: TemporaryBlockedTimeCreateRequest,
    ) -> NormalizedTemporaryBlockedTimeRequest:
        label = request.label.strip()
        if not label:
            raise TemporaryBlockedTimeValidationError(
                "Temporary blocked times payload is invalid.",
                errors={"entries": [f"Entry {index + 1} requires a label."]},
            )

        try:
            zone = ZoneInfo(request.timezone)
        except ZoneInfoNotFoundError as exc:
            raise TemporaryBlockedTimeValidationError(
                "Temporary blocked times payload is invalid.",
                errors={"timezone": ["Timezone is invalid."]},
            ) from exc

        start_time = self._parse_local_datetime(
            date_value=request.date,
            time_value=request.start,
            timezone_name=request.timezone,
        )
        end_time = self._parse_local_datetime(
            date_value=request.date,
            time_value=request.end,
            timezone_name=request.timezone,
        )
        if start_time is None or end_time is None:
            raise TemporaryBlockedTimeValidationError(
                "Temporary blocked times payload is invalid.",
                errors={"entries": [f"Entry {index + 1} contains an invalid date or time."]},
            )
        if start_time >= end_time:
            raise TemporaryBlockedTimeValidationError(
                "Temporary blocked times payload is invalid.",
                errors={
                    "entries": [f"Entry {index + 1} start time must be earlier than end time."]
                },
            )

        source = request.source
        if source not in TemporaryBlockedTimeSource.values:
            raise TemporaryBlockedTimeValidationError(
                "Temporary blocked times payload is invalid.",
                errors={"entries": [f"Entry {index + 1} contains an unsupported source."]},
            )

        return {
            "label": label,
            "start_time": start_time.astimezone(zone),
            "end_time": end_time.astimezone(zone),
            "timezone": request.timezone,
            "source": source,
        }

    def _parse_local_datetime(
        self,
        *,
        date_value: str,
        time_value: str,
        timezone_name: str,
    ) -> datetime | None:
        try:
            naive_datetime = datetime.fromisoformat(f"{date_value}T{time_value}:00")
            return timezone.make_aware(naive_datetime, ZoneInfo(timezone_name))
        except (ValueError, ZoneInfoNotFoundError):
            return None
