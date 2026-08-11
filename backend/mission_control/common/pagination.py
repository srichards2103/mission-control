from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response


class ApiPagination(LimitOffsetPagination):
    default_limit = 25
    max_limit = 100


def get_paginated_response(*, serializer_class, queryset, request):
    paginator = ApiPagination()
    page = paginator.paginate_queryset(queryset, request)

    return Response(
        {
            "results": serializer_class(page, many=True).data,
            "count": paginator.count,
            "limit": paginator.limit,
            "offset": paginator.offset,
        }
    )
