from functools import wraps

from django.http import Http404, JsonResponse
from django.core.cache import cache
from django.shortcuts import render

from .constants import WRITE_LIMIT, WRITE_WINDOW_SECONDS


def wants_json(request):
    return (request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or "application/json" in request.headers.get("Accept", ""))


def module_methods(*allowed):
    def decorate(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.method not in allowed:
                response = JsonResponse({"ok": False, "message": "Metode tidak diizinkan."}, status=405)
                response["Allow"] = ", ".join(allowed)
                return response
            return view(request, *args, **kwargs)
        return wrapped
    return decorate


def rate_limit(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        key = f"preferences:writes:{request.user.pk}"
        if cache.add(key, 1, timeout=WRITE_WINDOW_SECONDS):
            count = 1
        else:
            try:
                count = cache.incr(key)
            except ValueError:
                # Jendela bisa berakhir di antara add dan incr.
                cache.set(key, 1, timeout=WRITE_WINDOW_SECONDS)
                count = 1
        if count > WRITE_LIMIT:
            message = "Perubahan terlalu sering. Coba lagi dalam satu menit."
            if wants_json(request):
                response = JsonResponse({"ok": False, "message": message}, status=429)
            else:
                response = render(request, "preferences/_error.html", {"title": "Terlalu banyak perubahan", "message": message}, status=429)
            response["Retry-After"] = str(WRITE_WINDOW_SECONDS)
            return response
        return view(request, *args, **kwargs)
    return wrapped


def owner_required(model):
    def decorate(view):
        @wraps(view)
        def wrapped(request, pk, *args, **kwargs):
            item = model.objects.filter(pk=pk).first()
            if item is None:
                if wants_json(request):
                    return JsonResponse({"ok": False, "message": "Data tidak ditemukan."}, status=404)
                raise Http404("Data tidak ditemukan.")
            if item.user_id != request.user.pk:
                message = "Kamu tidak punya akses ke data ini."
                if wants_json(request):
                    return JsonResponse({"ok": False, "message": message}, status=403)
                return render(request, "preferences/_forbidden.html", {"message": message}, status=403)
            return view(request, item, *args, **kwargs)
        return wrapped
    return decorate
