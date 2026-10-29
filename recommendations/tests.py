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


class RecommendationVotingTests(TestCase):
    def setUp(self):
        self.author = get_user_model().objects.create_user(username="author", password="Rahasia-12345")
        self.voter = get_user_model().objects.create_user(username="voter", password="Rahasia-12345")
        source = Product.objects.create(source="manual", product_name="Produk Asal")
        replacement = Product.objects.create(source="manual", product_name="Produk Pengganti")
        self.recommendation = Recommendation.objects.create(
            source_product=source,
            replacement_product=replacement,
            author=self.author,
            reason="Lebih sesuai untuk pilihan ini.",
        )
        self.url = reverse("recommendations:vote", args=[self.recommendation.pk])

    def test_authenticated_user_can_vote_and_receive_updated_json_counts(self):
        self.client.force_login(self.voter)

        response = self.client.post(
            self.url,
            {"value": RecommendationVote.AGREE},
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"value": 1, "agree_count": 1, "disagree_count": 0, "score": 1},
        )
        self.assertEqual(
            RecommendationVote.objects.get(recommendation=self.recommendation, user=self.voter).value,
            RecommendationVote.AGREE,
        )

    def test_user_can_change_and_withdraw_their_vote(self):
        self.client.force_login(self.voter)
        RecommendationVote.objects.create(
            recommendation=self.recommendation,
            user=self.voter,
            value=RecommendationVote.AGREE,
        )

        response = self.client.post(
            self.url,
            {"value": RecommendationVote.DISAGREE},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(
            response.json(),
            {"value": -1, "agree_count": 0, "disagree_count": 1, "score": -1},
        )

        response = self.client.post(
            self.url,
            {"value": RecommendationVote.DISAGREE},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(
            response.json(),
            {"value": None, "agree_count": 0, "disagree_count": 0, "score": 0},
        )
        self.assertFalse(
            RecommendationVote.objects.filter(recommendation=self.recommendation, user=self.voter).exists()
        )

    def test_vote_requires_login_and_rejects_invalid_values(self):
        response = self.client.post(self.url, {"value": RecommendationVote.AGREE})
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")

        self.client.force_login(self.voter)
        response = self.client.post(self.url, {"value": "0"}, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Pilihan suara tidak valid."})
        self.assertFalse(RecommendationVote.objects.exists())

    def test_detail_marks_the_current_users_vote(self):
        RecommendationVote.objects.create(
            recommendation=self.recommendation,
            user=self.voter,
            value=RecommendationVote.AGREE,
        )
        self.client.force_login(self.voter)

        response = self.client.get(reverse("recommendations:detail", args=[self.recommendation.pk]))

        self.assertEqual(response.context["user_vote"], RecommendationVote.AGREE)
        self.assertContains(response, 'data-current-vote="1"')

    def test_vote_form_has_a_redirect_fallback_without_javascript(self):
        self.client.force_login(self.voter)

        response = self.client.post(self.url, {"value": RecommendationVote.AGREE})

        self.assertRedirects(
            response,
            reverse("recommendations:detail", args=[self.recommendation.pk]),
        )
        self.assertTrue(
            RecommendationVote.objects.filter(
                recommendation=self.recommendation,
                user=self.voter,
                value=RecommendationVote.AGREE,
            ).exists()
        )


class RecommendationCrudTests(TestCase):
    def setUp(self):
        self.author = get_user_model().objects.create_user(username="author", password="Rahasia-12345")
        self.other_user = get_user_model().objects.create_user(username="other", password="Rahasia-12345")
        source = Product.objects.create(source="manual", product_name="Produk Asal")
        replacement = Product.objects.create(source="manual", product_name="Produk Pengganti")
        self.recommendation = Recommendation.objects.create(
            source_product=source,
            replacement_product=replacement,
            author=self.author,
            reason="Alasan awal.",
        )

    def test_author_can_edit_the_recommendation_reason(self):
        self.client.force_login(self.author)

        response = self.client.post(
            reverse("recommendations:edit", args=[self.recommendation.pk]),
            {"reason": "Alasan yang diperbarui."},
        )

        self.assertRedirects(response, reverse("recommendations:detail", args=[self.recommendation.pk]))
        self.recommendation.refresh_from_db()
        self.assertEqual(self.recommendation.reason, "Alasan yang diperbarui.")

    def test_non_author_cannot_edit_a_recommendation(self):
        self.client.force_login(self.other_user)

        response = self.client.post(
            reverse("recommendations:edit", args=[self.recommendation.pk]),
            {"reason": "Tidak boleh tersimpan."},
        )

        self.assertEqual(response.status_code, 403)
        self.recommendation.refresh_from_db()
        self.assertEqual(self.recommendation.reason, "Alasan awal.")

    def test_author_can_delete_their_recommendation_and_its_votes(self):
        RecommendationVote.objects.create(
            recommendation=self.recommendation,
            user=self.other_user,
            value=RecommendationVote.AGREE,
        )
        self.client.force_login(self.author)

        response = self.client.post(reverse("recommendations:delete", args=[self.recommendation.pk]))

        self.assertRedirects(response, reverse("recommendations:list"))
        self.assertFalse(Recommendation.objects.exists())
        self.assertFalse(RecommendationVote.objects.exists())

    def test_non_author_cannot_delete_a_recommendation(self):
        self.client.force_login(self.other_user)

        response = self.client.post(reverse("recommendations:delete", args=[self.recommendation.pk]))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Recommendation.objects.filter(pk=self.recommendation.pk).exists())


class ProductRecommendationIntegrationTests(TestCase):
    def setUp(self):
        self.author = get_user_model().objects.create_user(username="author")
        self.source = Product.objects.create(source="manual", product_name="Produk Asal")
        self.first_replacement = Product.objects.create(source="manual", product_name="Pengganti Pertama")
        self.second_replacement = Product.objects.create(source="manual", product_name="Pengganti Kedua")
        self.first = Recommendation.objects.create(
            source_product=self.source,
            replacement_product=self.first_replacement,
            author=self.author,
            reason="Pilihan pertama.",
        )
        self.second = Recommendation.objects.create(
            source_product=self.source,
            replacement_product=self.second_replacement,
            author=self.author,
            reason="Pilihan kedua.",
        )
        voters = [get_user_model().objects.create_user(username=f"voter-{index}") for index in range(3)]
        RecommendationVote.objects.create(recommendation=self.second, user=voters[0], value=1)
        RecommendationVote.objects.create(recommendation=self.second, user=voters[1], value=1)
        RecommendationVote.objects.create(recommendation=self.first, user=voters[2], value=-1)

    def test_product_detail_shows_recommendations_ordered_by_score(self):
        response = self.client.get(reverse("product_catalog:product_detail", args=[self.source.pk]))

        recommendations = list(response.context["recommendations"])
        self.assertEqual([item.pk for item in recommendations], [self.second.pk, self.first.pk])
        self.assertContains(response, "Pengganti Pertama")
        self.assertContains(response, "Pengganti Kedua")

    def test_product_detail_json_includes_public_recommendations_without_author_identity(self):
        response = self.client.get(
            reverse("product_catalog:product_detail", args=[self.source.pk]),
            HTTP_ACCEPT="application/json",
        )

        data = response.json()
        self.assertEqual([item["id"] for item in data["recommendations"]], [self.second.pk, self.first.pk])
        self.assertNotIn("author", data["recommendations"][0])
        self.assertEqual(data["recommendations"][0]["score"], 2)


class RecommendationJsonApiTests(TestCase):
    def setUp(self):
        self.author = get_user_model().objects.create_user(username="author")
        self.source = Product.objects.create(source="manual", product_name="Produk Asal", category="Minuman")
        self.replacement = Product.objects.create(source="manual", product_name="Produk Pengganti", category="Minuman")
        self.recommendation = Recommendation.objects.create(
            source_product=self.source,
            replacement_product=self.replacement,
            author=self.author,
            reason="Alasan awal.",
        )

    def test_list_and_detail_json_do_not_expose_author_identity(self):
        list_data = self.client.get(reverse("recommendations:list"), HTTP_ACCEPT="application/json").json()
        detail_data = self.client.get(
            reverse("recommendations:detail", args=[self.recommendation.pk]),
            HTTP_ACCEPT="application/json",
        ).json()

        self.assertEqual(list_data["recommendations"][0]["id"], self.recommendation.pk)
        self.assertNotIn("author", list_data["recommendations"][0])
        self.assertNotIn("author", detail_data["recommendation"])

    def test_authenticated_user_can_create_edit_and_delete_through_json(self):
        self.client.force_login(self.author)
        another_replacement = Product.objects.create(
            source="manual", product_name="Pengganti Lain", category="Minuman"
        )
        create_response = self.client.post(
            reverse("recommendations:create", args=[self.source.pk]),
            {"replacement_product": another_replacement.pk, "reason": "Alasan baru."},
            HTTP_ACCEPT="application/json",
        )
        created = Recommendation.objects.get(replacement_product=another_replacement)
        self.assertEqual(create_response.status_code, 201)
        self.assertNotIn("author", create_response.json()["recommendation"])

        edit_response = self.client.post(
            reverse("recommendations:edit", args=[created.pk]),
            {"reason": "Alasan diperbarui."},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(edit_response.json()["recommendation"]["reason"], "Alasan diperbarui.")

        delete_response = self.client.post(
            reverse("recommendations:delete", args=[created.pk]),
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(delete_response.json(), {"deleted": True, "id": created.pk})
