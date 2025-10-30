import math
from typing import Type, TypeVar

from django.contrib.auth import get_user_model as get_untyped_user_model
from django.db.models import Model, QuerySet

from whimo.common.schemas.base import Pagination, PaginationRequest
from whimo.db.models import User

T = TypeVar("T", bound=Model)


def get_user_model() -> Type[User]:
    return get_untyped_user_model()


def paginate_queryset(
    queryset: QuerySet[T],
    request: PaginationRequest,
    default_page_size: int = 20,
) -> tuple[list[T], Pagination]:
    # Parse pagination parameters
    page = request.page
    page_size = request.page_size or default_page_size

    # Ensure reasonable values
    page = max(1, page)
    page_size = min(max(1, page_size), 100)  # Limit maximum page size to 100

    # Calculate pagination values
    total_items = queryset.count()
    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 1

    # Adjust page if it exceeds total pages
    page = min(page, total_pages)

    # Calculate offset and limit
    offset = (page - 1) * page_size

    # Get paginated items
    paginated_items = list(queryset[offset : offset + page_size])

    # Create pagination metadata
    pagination = Pagination(
        count=total_items,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        next_page=page + 1 if page < total_pages else None,
        previous_page=page - 1 if page > 1 else None,
    )

    return paginated_items, pagination
