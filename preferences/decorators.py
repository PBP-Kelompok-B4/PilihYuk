from functools import wraps

from django.http import Http404, JsonResponse
from django.shortcuts import render


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
