from django.core.paginator import InvalidPage
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class ProfilePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "limit"
    max_page_size = 50
    page_query_param = "page"

    def paginate_queryset(self, queryset, request, view=None):
        page_size = self.get_page_size(request)
        if not page_size:
            return None

        paginator = self.django_paginator_class(queryset, page_size)
        page_number = self._get_page_number(request, paginator)

        try:
            self.page = paginator.page(page_number)
        except InvalidPage:
            # Clamp to last valid page so envelope stays well-formed
            last = max(paginator.num_pages, 1)
            self.page = paginator.page(last)

        self.request = request
        return list(self.page)

    def get_paginated_response(self, data):
        return Response(
            {
                "status": "success",
                "page": self.page.number,
                "limit": self.get_page_size(self.request),
                "total": self.page.paginator.count,
                "data": data,
            }
        )

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "page": {"type": "integer"},
                "limit": {"type": "integer"},
                "total": {"type": "integer"},
                "data": schema,
            },
        }
