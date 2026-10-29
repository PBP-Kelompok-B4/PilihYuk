from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

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


def wants_json(request):
    return "application/json" in request.headers.get("Accept", "")


def recommendation_list(request):
    recommendations = recommendations_with_vote_counts().order_by("-created_at")
    return render(request, "recommendations/list.html", {"recommendations": recommendations})


def recommendation_detail(request, pk):
    recommendation = get_object_or_404(recommendations_with_vote_counts(), pk=pk)
    user_vote = None
    if request.user.is_authenticated:
        user_vote = RecommendationVote.objects.filter(
            recommendation=recommendation,
            user=request.user,
        ).values_list("value", flat=True).first()
    return render(request, "recommendations/detail.html", {
        "recommendation": recommendation,
        "user_vote": user_vote,
    })


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


@login_required
@require_POST
def recommendation_vote(request, pk):
    recommendation = get_object_or_404(Recommendation, pk=pk)
    try:
        value = int(request.POST.get("value", ""))
    except ValueError:
        value = None
    if value not in {RecommendationVote.AGREE, RecommendationVote.DISAGREE}:
        return JsonResponse({"error": "Pilihan suara tidak valid."}, status=400)
    vote = RecommendationVote.objects.filter(recommendation=recommendation, user=request.user).first()
    if vote and vote.value == value:
        vote.delete()
        value = None
    else:
        RecommendationVote.objects.update_or_create(
            recommendation=recommendation,
            user=request.user,
            defaults={"value": value},
        )
    recommendation = get_object_or_404(recommendations_with_vote_counts(), pk=pk)
    data = {
        "value": value,
        "agree_count": recommendation.agree_count,
        "disagree_count": recommendation.disagree_count,
        "score": recommendation.score,
    }
    if wants_json(request):
        return JsonResponse(data)
    return redirect("recommendations:detail", pk=recommendation.pk)
