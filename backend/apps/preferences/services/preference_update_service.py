from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.contrib.auth import get_user_model

from apps.preferences.models.user_preferences import ExecutionMode, UserPreferences
from apps.preferences.services.preferences_validation_error import PreferencesValidationError

logger = logging.getLogger(__name__)
User = get_user_model()

WEEKDAY_ORDER = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
WEEKDAY_SET = set(WEEKDAY_ORDER)


class PreferenceUpdateService:
    def update_for_user(
        self,
        user: Any,
        *,
        execution_mode: str,
        display_timezone: str | None,
        blocked_times: list[dict],
    ) -> UserPreferences:
        normalized_execution_mode = self._normalize_execution_mode(execution_mode)
        normalized_display_timezone = self._normalize_display_timezone(display_timezone)
        normalized_blocked_times = self._normalize_blocked_times(blocked_times)
        preferences, _ = UserPreferences.objects.get_or_create(user=user)
        preferences.execution_mode = normalized_execution_mode
        preferences.display_timezone = normalized_display_timezone
        preferences.blocked_times = normalized_blocked_times
        preferences.save(
            update_fields=["execution_mode", "display_timezone", "blocked_times", "updated_at"]
        )

        logger.info(
            "preferences.updated user_id=%s execution_mode=%s display_timezone=%s blocked_time_count=%s",
            user.id,
            normalized_execution_mode,
            normalized_display_timezone or "none",
            len(normalized_blocked_times),
        )
        return preferences

    def _normalize_execution_mode(self, execution_mode: str) -> str:
        if execution_mode not in ExecutionMode.values:
            raise PreferencesValidationError(
                "Preferences payload is invalid.",
                errors={"execution_mode": ["Select a valid execution mode."]},
            )
        return execution_mode

    def _normalize_blocked_times(self, blocked_times: list[dict]) -> list[dict]:
        if not isinstance(blocked_times, list):
            raise PreferencesValidationError(
                "Preferences payload is invalid.",
                errors={"blocked_times": ["Blocked times must be a list."]},
            )

        normalized_entries: list[dict] = []
        for index, entry in enumerate(blocked_times):
            if not isinstance(entry, dict):
                raise PreferencesValidationError(
                    "Preferences payload is invalid.",
                    errors={"blocked_times": [f"Entry {index + 1} must be an object."]},
                )

            label = str(entry.get("label", "")).strip()
            if not label:
                raise PreferencesValidationError(
                    "Preferences payload is invalid.",
                    errors={"blocked_times": [f"Entry {index + 1} requires a label."]},
                )

            raw_days = entry.get("days")
            if not isinstance(raw_days, list) or not raw_days:
                raise PreferencesValidationError(
                    "Preferences payload is invalid.",
                    errors={"blocked_times": [f"Entry {index + 1} requires at least one day."]},
                )

            normalized_days = self._normalize_days(raw_days, index=index)
            start = self._normalize_time_value(entry.get("start"), field_name="start", index=index)
            end = self._normalize_time_value(entry.get("end"), field_name="end", index=index)

            if start >= end:
                raise PreferencesValidationError(
                    "Preferences payload is invalid.",
                    errors={
                        "blocked_times": [
                            f"Entry {index + 1} start time must be earlier than end time."
                        ]
                    },
                )

            normalized_entries.append(
                {
                    "id": self._normalize_entry_id(entry.get("id")),
                    "label": label,
                    "days": normalized_days,
                    "start": start,
                    "end": end,
                }
            )

        self._validate_overlaps(normalized_entries)

        return sorted(
            normalized_entries,
            key=lambda entry: (
                WEEKDAY_ORDER.index(entry["days"][0]),
                entry["start"],
                entry["end"],
                entry["label"].lower(),
            ),
        )

    def _normalize_display_timezone(self, display_timezone: str | None) -> str:
        normalized_timezone = str(display_timezone or "").strip()
        if not normalized_timezone:
            return ""

        try:
            ZoneInfo(normalized_timezone)
        except ZoneInfoNotFoundError as exc:
            raise PreferencesValidationError(
                "Preferences payload is invalid.",
                errors={"display_timezone": ["Select a valid IANA timezone."]},
            ) from exc

        return normalized_timezone

    def _normalize_days(self, raw_days: list, *, index: int) -> list[str]:
        normalized_days: list[str] = []
        for day in raw_days:
            normalized_day = str(day).strip().lower()
            if normalized_day not in WEEKDAY_SET:
                raise PreferencesValidationError(
                    "Preferences payload is invalid.",
                    errors={"blocked_times": [f"Entry {index + 1} contains an unsupported day."]},
                )
            if normalized_day not in normalized_days:
                normalized_days.append(normalized_day)

        if not normalized_days:
            raise PreferencesValidationError(
                "Preferences payload is invalid.",
                errors={"blocked_times": [f"Entry {index + 1} requires at least one valid day."]},
            )

        return sorted(normalized_days, key=WEEKDAY_ORDER.index)

    def _normalize_time_value(self, raw_value, *, field_name: str, index: int) -> str:
        value = str(raw_value or "").strip()
        try:
            parsed_value = datetime.strptime(value, "%H:%M")
        except ValueError as exc:
            raise PreferencesValidationError(
                "Preferences payload is invalid.",
                errors={"blocked_times": [f"Entry {index + 1} has an invalid {field_name} time."]},
            ) from exc
        return parsed_value.strftime("%H:%M")

    def _normalize_entry_id(self, raw_entry_id) -> str:
        entry_id = str(raw_entry_id or "").strip()
        return entry_id or str(uuid4())

    def _validate_overlaps(self, entries: list[dict]) -> None:
        entries_by_day: dict[str, list[dict]] = {day: [] for day in WEEKDAY_ORDER}
        for entry in entries:
            for day in entry["days"]:
                entries_by_day[day].append(entry)

        for day, day_entries in entries_by_day.items():
            ordered_entries = sorted(day_entries, key=lambda entry: (entry["start"], entry["end"]))
            for previous, current in zip(ordered_entries, ordered_entries[1:], strict=False):
                if current["start"] < previous["end"]:
                    raise PreferencesValidationError(
                        "Preferences payload is invalid.",
                        errors={
                            "blocked_times": [
                                f"Blocked times cannot overlap on {day.title()}.",
                            ]
                        },
                    )
