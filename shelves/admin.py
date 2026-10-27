from django.contrib import admin

from .models import SavedShelf, Shelf, ShelfItem

admin.site.register(Shelf)
admin.site.register(ShelfItem)
admin.site.register(SavedShelf)
