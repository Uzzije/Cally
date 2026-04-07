import inngest.django
from django.conf import settings

from apps.calendars.inngest.client import inngest_client
from apps.calendars.inngest.functions import sync_primary_calendar_function

inngest_endpoint = inngest.django.serve(
    inngest_client,
    [sync_primary_calendar_function],
    serve_origin=settings.INNGEST_SERVE_ORIGIN,
    serve_path=settings.INNGEST_SERVE_PATH,
)
