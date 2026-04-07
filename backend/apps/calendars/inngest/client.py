import logging

import inngest
from django.conf import settings

inngest_client = inngest.Inngest(
    app_id=settings.INNGEST_APP_ID,
    api_base_url=settings.INNGEST_BASE_URL,
    event_api_base_url=settings.INNGEST_BASE_URL,
    event_key=settings.INNGEST_EVENT_KEY,
    is_production=True,
    logger=logging.getLogger(__name__),
    signing_key=settings.INNGEST_SIGNING_KEY,
)
