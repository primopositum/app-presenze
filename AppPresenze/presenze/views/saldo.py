from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import Saldo, Utente
from ..saldo_utils import upsert_saldo_mensile
from ..serializer import SaldoMiniSerializer, SaldoPatchSerializer


def _is_staff_or_super(user):
    return user.is_staff or user.is_superuser


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def saldo_detail(request, u_id: int):
    is_owner = request.user.id == u_id
    is_admin = _is_staff_or_super(request.user)

    if request.method == "GET" and not (is_owner or is_admin):
        return Response(
            {"errors": "Non hai i permessi per vedere questo saldo."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.method == "PATCH" and not is_admin:
        return Response(
            {"errors": "Solo admin e superuser possono modificare il saldo."},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        target_user = Utente.objects.get(pk=u_id)
    except Utente.DoesNotExist:
        return Response(
            {"errors": f"Utente con id {u_id} non trovato."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        saldo_obj, _ = Saldo.objects.get_or_create(utente=target_user)
        return Response(SaldoMiniSerializer(saldo_obj).data, status=status.HTTP_200_OK)

    serializer = SaldoPatchSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    with transaction.atomic():
        saldo_obj, _ = Saldo.objects.select_for_update().get_or_create(utente=target_user)
        upsert_saldo_mensile(
            saldo_obj,
            serializer.validated_data["periodo"],
            serializer.validated_data["saldo"],
        )
        saldo_obj.save(update_fields=["saldo", "data_upd"])

    return Response(SaldoMiniSerializer(saldo_obj).data, status=status.HTTP_200_OK)
