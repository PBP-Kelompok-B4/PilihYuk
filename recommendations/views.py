from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from product_catalog.models import Product

from .forms import RecommendationForm, RecommendationReasonForm
from .models import Recommendation, RecommendationVote


PAGE_SIZE = 10


def recommendations_with_vote_counts():
    return Recommendation.objects.filter(
        source_product__is_active=True, replacement_product__is_active=True,
    ).select_related("source_product", "replacement_product", "author").annotate(
        agree_count=Count("votes", filter=Q(votes__value=RecommendationVote.AGREE)),
        disagree_count=Count("votes", filter=Q(votes__value=RecommendationVote.DISAGREE)),
        score=Count("votes", filter=Q(votes__value=RecommendationVote.AGREE))
        - Count("votes", filter=Q(votes__value=RecommendationVote.DISAGREE)),
    )


def wants_json(request):
    return "application/json" in request.headers.get("Accept", "")


def serialize_recommendation(recommendation):
    return {
        "id": recommendation.pk,
        "source_product_id": recommendation.source_product_id,
        "replacement_product_id": recommendation.replacement_product_id,
        "reason": recommendation.reason,
        "agree_count": getattr(recommendation, "agree_count", 0),
        "disagree_count": getattr(recommendation, "disagree_count", 0),
        "score": getattr(recommendation, "score", 0),
        "created_at": recommendation.created_at.isoformat(),
        "updated_at": recommendation.updated_at.isoformat(),
    }


def recommendation_list(request):
    recommendations = recommendations_with_vote_counts()
    query = request.GET.get("q", "").strip()
    if query:
        recommendations = recommendations.filter(
            Q(source_product__product_name__icontains=query) | Q(replacement_product__product_name__icontains=query)
        )
    sort = request.GET.get("urutan", "")
    recommendations = recommendations.order_by("-score", "-created_at") if sort == "skor" else recommendations.order_by("-created_at")
    page = Paginator(recommendations, PAGE_SIZE).get_page(request.GET.get("page"))
    if wants_json(request):
        return JsonResponse({
            "recommendations": [serialize_recommendation(item) for item in page],
            "page": page.number,
            "num_pages": page.paginator.num_pages,
        })
    return render(request, "recommendations/list.html", {"page": page, "query": query, "sort": sort})


def recommendation_detail(request, pk):
    recommendation = get_object_or_404(recommendations_with_vote_counts(), pk=pk)
    if wants_json(request):
        return JsonResponse({"recommendation": serialize_recommendation(recommendation)})
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
        if wants_json(request):
            recommendation = get_object_or_404(recommendations_with_vote_counts(), pk=recommendation.pk)
            return JsonResponse({"recommendation": serialize_recommendation(recommendation)}, status=201)
        return redirect("recommendations:detail", pk=recommendation.pk)
    if wants_json(request):
        return JsonResponse({"errors": form.errors.get_json_data()}, status=400 if request.method == "POST" else 200)
    return render(request, "recommendations/form.html", {"form": form, "source_product": source_product})


@login_required
@require_http_methods(["GET", "POST"])
def recommendation_edit(request, pk):
    recommendation = get_object_or_404(Recommendation, pk=pk)
    if recommendation.author_id != request.user.pk:
        return HttpResponseForbidden("Hanya pembuat rekomendasi yang dapat menyuntingnya.")
    form = RecommendationReasonForm(request.POST or None, instance=recommendation)
    if request.method == "POST" and form.is_valid():
        form.save()
        if wants_json(request):
            recommendation = get_object_or_404(recommendations_with_vote_counts(), pk=recommendation.pk)
            return JsonResponse({"recommendation": serialize_recommendation(recommendation)})
        return redirect("recommendations:detail", pk=recommendation.pk)
    if wants_json(request):
        return JsonResponse({"errors": form.errors.get_json_data()}, status=400 if request.method == "POST" else 200)
    return render(request, "recommendations/form.html", {
        "form": form,
        "source_product": recommendation.source_product,
        "recommendation": recommendation,
        "editing": True,
    })


@login_required
@require_POST
def recommendation_delete(request, pk):
    recommendation = get_object_or_404(Recommendation, pk=pk)
    if recommendation.author_id != request.user.pk:
        return HttpResponseForbidden("Hanya pembuat rekomendasi yang dapat menariknya.")
    recommendation.delete()
    if wants_json(request):
        return JsonResponse({"deleted": True, "id": pk})
    return redirect("recommendations:list")


@login_required
@require_POST
def recommendation_vote(request, pk):
    recommendation = get_object_or_404(Recommendation, pk=pk)
    if recommendation.author_id == request.user.pk:
        message = "Kamu tidak dapat memberi suara pada rekomendasimu sendiri."
        if wants_json(request):
            return JsonResponse({"error": message}, status=403)
        return HttpResponseForbidden(message)
    try:
        value = int(request.POST.get("value", ""))
    except ValueError:
        value = None
    if value not in {RecommendationVote.AGREE, RecommendationVote.DISAGREE}:
        return JsonResponse({"error": "Pilihan suara tidak valid."}, status=400)
    with transaction.atomic():
        vote = RecommendationVote.objects.select_for_update().filter(
            recommendation=recommendation, user=request.user,
        ).first()
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
