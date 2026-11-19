from django.db.models import Q
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .serializers import ShelfSerializer
from .views import paginate, shelves_with_counts


@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
def shelf_list(request):
    query = request.GET.get("q", "").strip()
    shelves = shelves_with_counts().filter(is_private=False)
    if query:
        shelves = shelves.filter(Q(name__icontains=query) | Q(store_context__icontains=query)
                                 | Q(description__icontains=query))
    page = paginate(request, shelves)
    return Response({"results": ShelfSerializer(page, many=True).data, "page": page.number,
                     "num_pages": page.paginator.num_pages, "count": page.paginator.count})
