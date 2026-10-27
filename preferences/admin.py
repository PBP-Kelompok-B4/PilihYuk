from django.contrib import admin

from .models import Decision, Preference

admin.site.register(Preference)
admin.site.register(Decision)
