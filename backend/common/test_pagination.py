import pytest
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from .pagination import StandardPagination

factory = APIRequestFactory()


def paginate(items, query=""):
    """แบ่งหน้ารายการ (list ธรรมดา) ตาม URL ที่ระบุ แล้วคืนตัวข้อมูลของคำตอบ"""
    paginator = StandardPagination()
    page = paginator.paginate_queryset(items, Request(factory.get(f"/items/{query}")))
    return paginator.get_paginated_response(page).data


class TestStandardPagination:
    def test_first_page_has_twenty_items_and_page_info(self):
        data = paginate(list(range(45)))

        assert data["results"] == list(range(20))
        assert data["count"] == 45
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert data["total_pages"] == 3
        assert data["previous"] is None
        assert data["next"].endswith("/items/?page=2")

    def test_last_page_holds_the_remainder(self):
        data = paginate(list(range(45)), "?page=3")

        assert data["results"] == list(range(40, 45))
        assert data["next"] is None
        assert data["previous"].endswith("/items/?page=2")

    def test_empty_list_is_one_empty_page(self):
        data = paginate([])

        assert data["results"] == []
        assert data["count"] == 0
        assert data["total_pages"] == 1

    def test_client_cannot_change_page_size(self):
        data = paginate(list(range(100)), "?page_size=1000")

        assert len(data["results"]) == 20
        assert data["page_size"] == 20

    @pytest.mark.parametrize(
        "query", ["?page=4", "?page=0", "?page=-1", "?page=abc", "?page=" + "9" * 30]
    )
    def test_invalid_or_out_of_range_page_is_not_found(self, query):
        with pytest.raises(NotFound):
            paginate(list(range(45)), query)
