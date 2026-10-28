"""Admin Modul 4, hanya untuk debug.

Notes:
- Halaman bawaan Django di /admin/ untuk melihat dan mengelola
  isi database. Hanya bisa dibuka oleh akun staf.
- File ini mendaftarkan dua model Modul 4 (DataCorrection dan DataCorrectionItem)
  supaya isinya bisa dilihat di /admin/, misalnya untuk mengecek data saat debugging.
- Kenapa hanya-baca? Tinjauan sesungguhnya wajib lewat /moderasi/, karena persetujuan
  harus menulis nilai ke Product dalam satu transaksi. Kalau status diubah lewat admin
  menjadi "approved", Product TIDAK ikut berubah, jadi datanya tidak sinkron.
  Karena itu admin ini hanya bisa melihat, menyaring, mencari, dan menghapus pengajuan,
  tetapi tidak bisa menambah atau mengubahnya.
- Identitas pengguna ditampilkan sebagai first_name, bukan username/email
"""
from django.contrib import admin

from .models import DataCorrection, DataCorrectionItem


def display_name(user):
    # Hanya nama tampilan. username berisi email (keputusan 38), jadi tidak ditampilkan.
    if user is None:
        return "-"
    return user.first_name or "Pengguna"


class ReadOnlyAdminMixin:
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class DataCorrectionItemInline(ReadOnlyAdminMixin, admin.TabularInline):
    model = DataCorrectionItem
    extra = 0
    can_delete = False
    fields = ("field_name", "old_value", "proposed_value", "status", "review_note")
    readonly_fields = fields


@admin.register(DataCorrection)
class DataCorrectionAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = (
        "id", "product_label", "submitter", "status_label", "created_at", "reviewer", "reviewed_at",
    )
    list_filter = ("items__status", "created_at")
    list_select_related = ("product", "submitted_by", "reviewed_by")
    search_fields = ("product__product_name", "product__code")
    fields = ("product_label", "submitter", "status_label", "created_at", "reviewer", "reviewed_at")
    readonly_fields = fields
    inlines = [DataCorrectionItemInline]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("items")

    @admin.display(description="produk", ordering="product__product_name")
    def product_label(self, obj):
        return f"{obj.product.product_name or 'Tanpa nama'} (#{obj.product_id})"

    @admin.display(description="pengaju")
    def submitter(self, obj):
        return display_name(obj.submitted_by)

    @admin.display(description="peninjau terakhir")
    def reviewer(self, obj):
        return display_name(obj.reviewed_by)

    @admin.display(description="status")
    def status_label(self, obj):
        return obj.get_status_display()


@admin.register(DataCorrectionItem)
class DataCorrectionItemAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("id", "correction", "field_name", "old_value", "proposed_value", "status")
    list_filter = ("status", "field_name")
    list_select_related = ("correction__product",)
    search_fields = ("correction__product__product_name", "correction__product__code")
    fields = ("correction", "field_name", "old_value", "proposed_value", "status", "review_note")
    readonly_fields = fields