from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from product_catalog.models import Product

from .models import Substitution, SubstitutionVote


class SubstitutionModelTests(TestCase):
    def setUp(self):
        self.author = get_user_model().objects.create_user(username="author")
        self.voter = get_user_model().objects.create_user(username="voter")
        self.source = Product.objects.create(source="manual", product_name="Produk Asal")
        self.replacement = Product.objects.create(source="manual", product_name="Produk Pengganti")

    def create_substitution(self):
        return Substitution.objects.create(
            source_product=self.source,
            replacement_product=self.replacement,
            author=self.author,
            reason="Kandungan gulanya lebih rendah.",
        )

    def test_substitution_stores_a_directed_product_pair(self):
        forward = self.create_substitution()
        reverse = Substitution.objects.create(
            source_product=self.replacement,
            replacement_product=self.source,
            author=self.author,
            reason="Pilihan untuk arah sebaliknya.",
        )

        self.assertEqual(str(forward), "Produk Asal → Produk Pengganti")
        self.assertNotEqual(forward.pk, reverse.pk)

    def test_substitution_cannot_replace_a_product_with_itself(self):
        substitution = Substitution(
            source_product=self.source,
            replacement_product=self.source,
            author=self.author,
            reason="Tidak valid.",
        )

        with self.assertRaises(ValidationError):
            substitution.full_clean()

    def test_duplicate_directed_pair_is_rejected(self):
        self.create_substitution()

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.create_substitution()

    def test_product_used_by_substitution_is_protected_from_deletion(self):
        self.create_substitution()

        with self.assertRaises(IntegrityError):
            self.source.delete()

    def test_one_user_can_only_have_one_vote_per_substitution(self):
        substitution = self.create_substitution()
        SubstitutionVote.objects.create(
            substitution=substitution,
            user=self.voter,
            value=SubstitutionVote.AGREE,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            SubstitutionVote.objects.create(
                substitution=substitution,
                user=self.voter,
                value=SubstitutionVote.DISAGREE,
            )

    def test_vote_only_accepts_agree_or_disagree(self):
        vote = SubstitutionVote(
            substitution=self.create_substitution(),
            user=self.voter,
            value=0,
        )

        with self.assertRaises(ValidationError):
            vote.full_clean()

        with self.assertRaises(IntegrityError), transaction.atomic():
            SubstitutionVote.objects.create(
                substitution=vote.substitution,
                user=self.voter,
                value=0,
            )


class SubstitutionPageTests(TestCase):
    def setUp(self):
        self.author = get_user_model().objects.create_user(username="author", password="Rahasia-12345")
        self.source = Product.objects.create(source="manual", product_name="Produk Asal", category="Minuman")
        self.replacement = Product.objects.create(source="manual", product_name="Produk Pengganti", category="Minuman")
        self.other_category = Product.objects.create(source="manual", product_name="Produk Lain", category="Makanan")

    def create_substitution(self):
        return Substitution.objects.create(
            source_product=self.source,
            replacement_product=self.replacement,
            author=self.author,
            reason="Kandungan gulanya lebih rendah.",
        )

    def test_public_list_and_detail_render_a_substitution(self):
        substitution = self.create_substitution()

        response = self.client.get(reverse("substitutions:list"))
        self.assertContains(response, "Produk Asal")
        self.assertContains(response, "Produk Pengganti")
        self.assertContains(response, substitution.reason)

        response = self.client.get(reverse("substitutions:detail", args=[substitution.pk]))
        self.assertContains(response, "Produk Asal")
        self.assertContains(response, "Produk Pengganti")

    def test_anonymous_user_is_redirected_when_proposing(self):
        url = reverse("substitutions:create", args=[self.source.pk])

        self.assertRedirects(self.client.get(url), f"{reverse('accounts:login')}?next={url}")

    def test_authenticated_user_can_propose_an_eligible_replacement(self):
        self.client.force_login(self.author)
        response = self.client.post(
            reverse("substitutions:create", args=[self.source.pk]),
            {"replacement_product": self.replacement.pk, "reason": "Gula lebih rendah."},
        )

        substitution = Substitution.objects.get()
        self.assertRedirects(response, reverse("substitutions:detail", args=[substitution.pk]))
        self.assertEqual((substitution.source_product, substitution.replacement_product), (self.source, self.replacement))
        self.assertEqual(substitution.author, self.author)

    def test_user_cannot_propose_a_product_outside_the_source_category(self):
        self.client.force_login(self.author)
        response = self.client.post(
            reverse("substitutions:create", args=[self.source.pk]),
            {"replacement_product": self.other_category.pk, "reason": "Kategori berbeda."},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Substitution.objects.exists())
