from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from product_catalog.models import Product

from .forms import SubstitutionForm
from .models import Substitution, SubstitutionVote


def substitutions_with_vote_counts():
    return Substitution.objects.select_related("source_product", "replacement_product").annotate(
        agree_count=Count("votes", filter=Q(votes__value=SubstitutionVote.AGREE)),
        disagree_count=Count("votes", filter=Q(votes__value=SubstitutionVote.DISAGREE)),
        score=Count("votes", filter=Q(votes__value=SubstitutionVote.AGREE))
        - Count("votes", filter=Q(votes__value=SubstitutionVote.DISAGREE)),
    )


def substitution_list(request):
    substitutions = substitutions_with_vote_counts().order_by("-created_at")
    return render(request, "substitutions/list.html", {"substitutions": substitutions})


def substitution_detail(request, pk):
    substitution = get_object_or_404(substitutions_with_vote_counts(), pk=pk)
    return render(request, "substitutions/detail.html", {"substitution": substitution})


@login_required
@require_http_methods(["GET", "POST"])
def substitution_create(request, source_pk):
    source_product = get_object_or_404(Product, pk=source_pk, is_active=True)
    form = SubstitutionForm(
        request.POST or None,
        source_product=source_product,
    )
    if request.method == "POST" and form.is_valid():
        substitution = form.save(author=request.user)
        return redirect("substitutions:detail", pk=substitution.pk)
    return render(request, "substitutions/form.html", {"form": form, "source_product": source_product})
