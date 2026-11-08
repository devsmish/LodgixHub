from __future__ import annotations

from tests_e2e.actions.api.base_api_action import BaseAPIAction
from tests_e2e.actions.base import ActionResult, NotificationActions


class APINotificationActions(BaseAPIAction, NotificationActions):
    def list_logs(self) -> ActionResult:
        return self._get("/notifications/logs/")
