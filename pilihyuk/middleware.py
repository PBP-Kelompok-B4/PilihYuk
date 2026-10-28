import zoneinfo

from django.utils import timezone


def user_timezone(get_response):
    """Tampilkan waktu dalam zona waktu browser (cookie "tz" diisi base.html). Database tetap UTC."""

    def middleware(request):
        try:
            timezone.activate(zoneinfo.ZoneInfo(request.COOKIES.get("tz", "")))
        except (ValueError, zoneinfo.ZoneInfoNotFoundError):
            timezone.deactivate()
        return get_response(request)

    return middleware
