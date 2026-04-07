from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Automobile
from ..serializer import AutomobileSerializer, AutomobilePatchSerializer


class AutomobileListCreateView(ListCreateAPIView):
    """
    GET  /automobili/   -> lista (query param ?is_active=true/false)
    POST /automobili/   -> crea
    """

    serializer_class = AutomobileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Automobile.objects.all().order_by("-data_creaz")

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        return qs

    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


class AutomobileDetailView(RetrieveUpdateAPIView):
    """
    GET   /automobili/<a_id>/   -> dettaglio
    PUT   /automobili/<a_id>/   -> aggiornamento completo
    PATCH /automobili/<a_id>/   -> aggiornamento parziale (qualsiasi campo)
    """

    queryset = Automobile.objects.all()
    serializer_class = AutomobileSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)


class AutomobileDeleteView(APIView):
    """
    DELETE /automobili/<a_id>/delete/

    - Se l'auto e collegata ad altre entita -> soft delete (is_active=False)
      HTTP 200  { "detail": "Automobile archiviata.", "action": "archived", "data": {...} }

    - Se l'auto non ha relazioni             -> hard delete
      HTTP 200  { "detail": "Automobile eliminata.", "action": "deleted" }
    """

    permission_classes = [IsAuthenticated]

    def _has_related_objects(self, automobile):
        """
        Controlla tutti i related managers generati da FK/M2M verso Automobile.
        Restituisce True se almeno un record collegato esiste.
        """
        for rel in automobile._meta.related_objects:
            accessor = rel.get_accessor_name()
            manager = getattr(automobile, accessor, None)
            if manager is not None and manager.exists():
                return True
        return False

    def delete(self, request, pk):
        try:
            automobile = Automobile.objects.get(pk=pk)
        except Automobile.DoesNotExist:
            return Response(
                {"detail": "Automobile non trovata."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if self._has_related_objects(automobile):
            automobile.is_active = False
            automobile.save(update_fields=["is_active", "data_upd"])
            return Response(
                {
                    "detail": "Automobile archiviata.",
                    "action": "archived",
                    "data": AutomobileSerializer(automobile).data,
                },
                status=status.HTTP_200_OK,
            )

        automobile.delete()
        return Response(
            {
                "detail": "Automobile eliminata.",
                "action": "deleted",
            },
            status=status.HTTP_200_OK,
        )


class AutomobilePatchView(APIView):
    """
    PATCH /automobili/<a_id>/patch/

    Aggiorna coefficiente e/o is_active in un'unica rotta dedicata.
    """

    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            automobile = Automobile.objects.get(pk=pk)
        except Automobile.DoesNotExist:
            return Response(
                {"detail": "Automobile non trovata."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AutomobilePatchSerializer(
            automobile,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            AutomobileSerializer(automobile).data,
            status=status.HTTP_200_OK,
        )
