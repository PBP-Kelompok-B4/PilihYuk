"""Model Modul 4 (Antrean Data).

Notes:
- Ada dua model, sesuai PRD bagian 7 dan ERD:
  1. DataCorrection     : satu PENGAJUAN koreksi untuk satu produk.
  2. DataCorrectionItem : satu FIELD di dalam pengajuan itu.
  Contoh: pengguna mengajukan koreksi protein dan gula untuk "Indomie Goreng".
  Hasilnya 1 DataCorrection + 2 DataCorrectionItem (protein, gula).
- Kenapa dipisah per field? Karena kurator meninjau PER FIELD (PRD F-4.4): protein bisa
  disetujui sementara gula ditolak, dalam pengajuan yang sama.
- Setelah mengubah file ini, wajib membuat migration:
  `python manage.py makemigrations data_correction`, lalu `python manage.py migrate`.
"""
from django.conf import settings
from django.db import models
from django.db.models import Q

from .constants import (
    APPROVED,
    CORRECTABLE_FIELDS,
    CORRECTION_STATUS_LABELS,
    FIELD_CHOICES,
    PARTIAL,
    PENDING,
    REJECTED,
    STATUS_CHOICES,
)


class DataCorrection(models.Model):
    product = models.ForeignKey(
        "product_catalog.Product",  # string, bukan impor, agar tidak ada circular import
        on_delete=models.PROTECT,  # K-1: produk yang punya pengajuan tidak bisa dihapus
        related_name="data_corrections",
        verbose_name="produk",
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submitted_data_corrections",
        verbose_name="pengaju",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_data_corrections",
        verbose_name="peninjau terakhir",
    )
    created_at = models.DateTimeField("diajukan pada", auto_now_add=True)
    reviewed_at = models.DateTimeField("terakhir ditinjau pada", null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name = "pengajuan koreksi"
        verbose_name_plural = "pengajuan koreksi"

    def __str__(self):
        label = f"Koreksi #{self.pk}" if self.pk else "Koreksi baru"
        if not self.product_id:
            return label
        return f"{label} · {self.product.product_name or f'produk #{self.product_id}'}"

    def _item_statuses(self):
        # items.all() memakai cache prefetch_related("items") bila ada. Jangan prefetch
        # "items" dengan queryset yang disaring: status akan dihitung dari sebagian item.
        if self.pk is None:
            return set()
        return {item.status for item in self.items.all()}

    @property
    def status(self):
        statuses = self._item_statuses()
        if not statuses or PENDING in statuses:
            return PENDING
        if statuses == {APPROVED}:
            return APPROVED
        if statuses == {REJECTED}:
            return REJECTED
        return PARTIAL

    def get_status_display(self):
        return CORRECTION_STATUS_LABELS[self.status]

    @property
    def is_withdrawable(self):
        return self._item_statuses() <= {PENDING}


class DataCorrectionItem(models.Model):
    correction = models.ForeignKey(
        DataCorrection,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="pengajuan",
    )
    field_name = models.CharField("field", max_length=32, choices=FIELD_CHOICES)
    old_value = models.TextField(
        "nilai lama",
        null=True,
        blank=True,
        help_text="Dalam satuan kolom Product (natrium dalam gram). "
                  "Kosong berarti tidak diketahui saat diajukan.",
    )
    proposed_value = models.TextField(
        "nilai usulan",
        help_text="Dalam satuan kolom Product (natrium dalam gram).",
    )
    status = models.CharField(
        "status",
        max_length=10,
        choices=STATUS_CHOICES,
        default=PENDING,
        db_index=True,
    )
    review_note = models.TextField("catatan kurator", blank=True)

    class Meta:
        ordering = ["correction_id", "pk"]
        verbose_name = "item koreksi"
        verbose_name_plural = "item koreksi"
        constraints = [
            models.UniqueConstraint(fields=["correction", "field_name"], name="uniq_correction_field"),
            # Pertahanan di tingkat database untuk F-4.2: persetujuan menulis ke kolom
            # bernama field_name, jadi nama di luar daftar tetap tidak boleh tersimpan.
            models.CheckConstraint(
                condition=Q(field_name__in=CORRECTABLE_FIELDS),
                name="dc_item_field_correctable",
            ),
            models.CheckConstraint(
                condition=Q(status__in=[PENDING, APPROVED, REJECTED]),
                name="dc_item_status_valid",
            ),
        ]

    def __str__(self):
        field = self.get_field_name_display()
        return f"Koreksi #{self.correction_id} · {field} · {self.get_status_display()}"