from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from product_catalog.models import Product

from .forms import RecommendationForm
from .models import Recommendation, RecommendationVote


def recommendations_with_vote_counts():
    return Recommendation.objects.select_related("source_product", "replacement_product").annotate(
        agree_count=Count("votes", filter=Q(votes__value=RecommendationVote.AGREE)),
        disagree_count=Count("votes", filter=Q(votes__value=RecommendationVote.DISAGREE)),
        score=Count("votes", filter=Q(votes__value=RecommendationVote.AGREE))
        - Count("votes", filter=Q(votes__value=RecommendationVote.DISAGREE)),
    )


def recommendation_list(request):
    recommendations = recommendations_with_vote_counts().order_by("-created_at")
    return render(request, "recommendations/list.html", {"recommendations": recommendations})


def recommendation_detail(request, pk):
    recommendation = get_object_or_404(recommendations_with_vote_counts(), pk=pk)
    return render(request, "recommendations/detail.html", {"recommendation": recommendation})


@login_required
@require_http_methods(["GET", "POST"])
def recommendation_create(request, source_pk):
    source_product = get_object_or_404(Product, pk=source_pk, is_active=True)
    form = RecommendationForm(
        request.POST or None,
        source_product=source_product,
    )
    if request.method == "POST" and form.is_valid():
        recommendation = form.save(author=request.user)
        return redirect("recommendations:detail", pk=recommendation.pk)
    return render(request, "recommendations/form.html", {"form": form, "source_product": source_product})
