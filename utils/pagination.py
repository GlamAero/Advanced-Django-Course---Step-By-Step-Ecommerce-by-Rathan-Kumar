from django.core.paginator import Paginator, Page, EmptyPage, PageNotAnInteger
from django.http import HttpRequest
from typing import Any, Tuple


def paginate_queryset(
    request: HttpRequest,
    queryset: Any,
    per_page: int = 10
) -> Tuple[Page, int]:
    """
    Paginate a given queryset based on the current request's page parameter.

    Args:
        request (HttpRequest): The incoming HTTP request object containing query params.
        queryset (QuerySet): The dataset to paginate (usually a list of model instances).
        per_page (int): Number of items to show per page (default is 10).

    Returns:
        Tuple[Page, int]: 
            - page_obj: A Django Page object containing paginated results.
            - page_number: The current active page number as an integer.
    """

    # Get the page number from query parameters (default to page 1 if not provided)
    page_number = request.GET.get("page", 1)

    # Instantiate Django's built-in paginator with the given queryset
    paginator = Paginator(queryset, per_page)

    try:
        # Try to get the page object for the current page number
        page_obj = paginator.page(page_number)

    except PageNotAnInteger:
        # If page is not an integer (e.g., ?page=abc), show the first page
        page_obj = paginator.page(1)
        page_number = 1

    except EmptyPage:
        # If page number is out of range (e.g., too high), show the last page
        page_obj = paginator.page(paginator.num_pages)
        page_number = paginator.num_pages

    # Return the paginated page and the current page number (as int)
    return page_obj, int(page_number)
