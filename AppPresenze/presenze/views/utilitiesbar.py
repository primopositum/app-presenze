from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from ..models import UtilitiesBar
from ..serializer import UtilitiesBarSerializer


class UtilitiesBarListView(ListAPIView):
    """
    GET /utilitiesbar/ -> lista ordinata per posizione.
    Endpoint in sola lettura: non espone POST/PUT/PATCH/DELETE.
    """

    serializer_class = UtilitiesBarSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UtilitiesBar.objects.all().order_by("posizione", "id")
