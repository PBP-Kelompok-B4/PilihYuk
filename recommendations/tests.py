from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from product_catalog.models import Product

from .models import Recommendation, RecommendationVote


class RecommendationModelTests(TestCase):
    def setUp(self):
        self.author = get_user_model().objects.create_user(username="author")
        self.voter = get_user_model().objects.create_user(username="voter")
        self.source = Product.objects.create(source="manual", product_name="Produk Asal")
        self.replacement = Product.objects.create(source="manual", product_name="Produk Pengganti")

    def create_recommendation(self):
        return Recommendation.objects.create(
            source_product=self.source,
            replacement_product=self.replacement,
            author=self.author,
            reason="Kandungan gulanya lebih rendah.",
        )

    def test_recommendation_stores_a_directed_product_pair(self):
        forward = self.create_recommendation()
        reverse = Recommendation.objects.create(
            source_product=self.replacement,
            replacement_product=self.source,
            author=self.author,
            reason="Pilihan untuk arah sebaliknya.",
        )

        self.assertEqual(str(forward), "Produk Asal → Produk Pengganti")
        self.assertNotEqual(forward.pk, reverse.pk)

    def test_recommendation_cannot_replace_a_product_with_itself(self):
        recommendation = Recommendation(
            source_product=self.source,
            replacement_product=self.source,
            author=self.author,
            reason="Tidak valid.",
        )

        with self.assertRaises(ValidationError):
            recommendation.full_clean()

    def test_duplicate_directed_pair_is_rejected(self):
        self.create_recommendation()

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.create_recommendation()

    def test_product_used_by_recommendation_is_protected_from_deletion(self):
        self.create_recommendation()

        with self.assertRaises(IntegrityError):
            self.source.delete()

    def test_one_user_can_only_have_one_vote_per_recommendation(self):
        recommendation = self.create_recommendation()
        RecommendationVote.objects.create(
            recommendation=recommendation,
            user=self.voter,
            value=RecommendationVote.AGREE,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            RecommendationVote.objects.create(
                recommendation=recommendation,
                user=self.voter,
                value=RecommendationVote.DISAGREE,
            )

    def test_vote_only_accepts_agree_or_disagree(self):
        vote = RecommendationVote(
            recommendation=self.create_recommendation(),
            user=self.voter,
            value=0,
        )

        with self.assertRaises(ValidationError):
            vote.full_clean()

        with self.assertRaises(IntegrityError), transaction.atomic():
            RecommendationVote.objects.create(
                recommendation=vote.recommendation,
                user=self.voter,
                value=0,
            )


class RecommendationPageTests(TestCase):
    def setUp(self):
        self.author = get_user_model().objects.create_user(username="author", password="Rahasia-12345")
        self.source = Product.objects.create(source="manual", product_name="Produk Asal", category="Minuman")
        self.replacement = Product.objects.create(source="manual", product_name="Produk Pengganti", category="Minuman")
        self.other_category = Product.objects.create(source="manual", product_name="Produk Lain", category="Makanan")

    def create_recommendation(self):
        return Recommendation.objects.create(
            source_product=self.source,
            replacement_product=self.replacement,
            author=self.author,
            reason="Kandungan gulanya lebih rendah.",
        )

    def test_public_list_and_detail_render_a_recommendation(self):
        recommendation = self.create_recommendation()

        response = self.client.get(reverse("recommendations:list"))
        self.assertContains(response, "Produk Asal")
        self.assertContains(response, "Produk Pengganti")
        self.assertContains(response, recommendation.reason)

        response = self.client.get(reverse("recommendations:detail", args=[recommendation.pk]))
        self.assertContains(response, "Produk Asal")
        self.assertContains(response, "Produk Pengganti")

    def test_anonymous_user_is_redirected_when_proposing(self):
        url = reverse("recommendations:create", args=[self.source.pk])

        self.assertRedirects(self.client.get(url), f"{reverse('accounts:login')}?next={url}")

    def test_authenticated_user_can_propose_an_eligible_replacement(self):
        self.client.force_login(self.author)
        response = self.client.post(
            reverse("recommendations:create", args=[self.source.pk]),
            {"replacement_product": self.replacement.pk, "reason": "Gula lebih rendah."},
        )

        recommendation = Recommendation.objects.get()
        self.assertRedirects(response, reverse("recommendations:detail", args=[recommendation.pk]))
        self.assertEqual((recommendation.source_product, recommendation.replacement_product), (self.source, self.replacement))
        self.assertEqual(recommendation.author, self.author)

    def test_user_cannot_propose_a_product_outside_the_source_category(self):
        self.client.force_login(self.author)
        response = self.client.post(
            reverse("recommendations:create", args=[self.source.pk]),
            {"replacement_product": self.other_category.pk, "reason": "Kategori berbeda."},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Recommendation.objects.exists())
