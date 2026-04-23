from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class ProfilePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "limit"
    max_page_size = 50
    page_query_param = "page"

    def get_paginated_response(self, data):
        total = self.page.paginator.count
        limit = self.get_page_size(self.request)
        import math
        total_pages = math.ceil(total / limit) if limit else 1
        return Response(
            {
                "status": "success",
                "page": self.page.number,
                "limit": limit,
                "total": total,
                "total_pages": total_pages,
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
