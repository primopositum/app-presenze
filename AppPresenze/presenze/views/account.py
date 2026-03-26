from django.contrib.auth import update_session_auth_hash
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ..models import Utente, Saldo
from ..serializer import UtenteSerializer, SaldoMiniSerializer, ContrattoMiniSerializer


def _is_staff_or_super(user):
    return user.is_staff or user.is_superuser


def _resolve_target_user(request):
    query_user_id = request.query_params.get("user_id")
    query_id = request.query_params.get("id")
    body_user_id = request.data.get("user_id") if hasattr(request, "data") else None
    body_id = request.data.get("id") if hasattr(request, "data") else None

    provided_ids = [
        value
        for value in (query_user_id, query_id, body_user_id, body_id)
        if value not in (None, "")
    ]

    if len(set(str(v) for v in provided_ids)) > 1:
        return None, Response(
            {"errors": "Parametri target in conflitto: usa un solo valore per id/user_id."},
            status=status.HTTP_400_BAD_REQUEST
        )

    raw_user_id = provided_ids[0] if provided_ids else None

    if raw_user_id in (None, ""):
        return request.user, None

    try:
        target_user_id = int(raw_user_id)
    except (TypeError, ValueError):
        return None, Response(
            {"errors": "id/user_id non valido."},
            status=status.HTTP_400_BAD_REQUEST
        )

    is_admin = _is_staff_or_super(request.user)
    is_owner = request.user.id == target_user_id
    if not (is_admin or is_owner):
        return None, Response(
            {"errors": "Non hai i permessi per aggiornare questo utente."},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        return Utente.objects.get(pk=target_user_id), None
    except Utente.DoesNotExist:
        return None, Response(
            {"errors": "Utente non trovato."},
            status=status.HTTP_404_NOT_FOUND
        )


def _resolve_target_user_id_for_delete(request):
    query_user_id = request.query_params.get("user_id")
    query_id = request.query_params.get("id")
    body_user_id = request.data.get("user_id") if hasattr(request, "data") else None
    body_id = request.data.get("id") if hasattr(request, "data") else None

    provided_ids = [
        value
        for value in (query_user_id, query_id, body_user_id, body_id)
        if value not in (None, "")
    ]

    if not provided_ids:
        return None, Response(
            {"errors": "Parametro id/user_id obbligatorio."},
            status=status.HTTP_400_BAD_REQUEST
        )

    if len(set(str(v) for v in provided_ids)) > 1:
        return None, Response(
            {"errors": "Parametri target in conflitto: usa un solo valore per id/user_id."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        return int(provided_ids[0]), None
    except (TypeError, ValueError):
        return None, Response(
            {"errors": "id/user_id non valido."},
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    old_password = request.data.get("old_password")
    new_password = request.data.get("new_password")

    if not request.user.check_password(old_password):
        return Response({"error": "Vecchia password errata"}, status=status.HTTP_400_BAD_REQUEST)

    request.user.set_password(new_password)
    request.user.save()
    update_session_auth_hash(request, request.user)

    return Response({"message": "Password modificata con successo!"})

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    target_user, error_response = _resolve_target_user(request)
    if error_response is not None:
        return error_response

    if request.method == 'GET':
        return Response(UtenteSerializer(target_user).data)

    is_admin = _is_staff_or_super(request.user)
    is_owner = request.user.id == target_user.id
    if not (is_admin or is_owner):
        return Response(
            {"errors": "Non hai i permessi per aggiornare questo utente."},
            status=status.HTTP_403_FORBIDDEN
        )

    payload = request.data
    user_payload = {}
    for key in ("email", "nome", "cognome", "dati_anagrafici"):
        if key in payload:
            user_payload[key] = payload.get(key)

    # Evita errori "email already exists" quando l'email è di fatto invariata
    if "email" in user_payload:
        incoming_email = (user_payload.get("email") or "").strip()
        current_email = (target_user.email or "").strip()
        if incoming_email.lower() == current_email.lower():
            user_payload.pop("email", None)
        else:
            user_payload["email"] = incoming_email

    if "is_active" in payload:
        if not is_admin:
            return Response(
                {"errors": "Solo admin e superuser possono modificare is_active."},
                status=status.HTTP_403_FORBIDDEN
            )
        user_payload["is_active"] = payload.get("is_active")

    saldo_payload = payload.get("saldo", None)
    contratti_payload = payload.get("contratti", None)

    if saldo_payload is not None and not is_admin:
        return Response(
            {"errors": "Solo admin e superuser possono modificare il saldo."},
            status=status.HTTP_403_FORBIDDEN
        )

    if contratti_payload is not None and not is_admin:
        return Response(
            {"errors": "Solo admin e superuser possono modificare i contratti."},
            status=status.HTTP_403_FORBIDDEN
        )

    with transaction.atomic():
        if user_payload:
            serializer = UtenteSerializer(target_user, data=user_payload, partial=True)
            if not serializer.is_valid():
                return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            serializer.save()

        if saldo_payload is not None:
            if not isinstance(saldo_payload, dict):
                return Response(
                    {"saldo": "Formato non valido: atteso oggetto JSON."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            saldo_obj, _ = Saldo.objects.get_or_create(utente=target_user)
            saldo_serializer = SaldoMiniSerializer(saldo_obj, data=saldo_payload, partial=True)
            if not saldo_serializer.is_valid():
                return Response({"saldo": saldo_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            saldo_serializer.save()

        if contratti_payload is not None:
            # Supporta sia un oggetto singolo che una lista (usa il primo elemento valido).
            if isinstance(contratti_payload, list):
                if not contratti_payload:
                    return Response(
                        {"contratti": "Lista contratti vuota."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                contract_data = contratti_payload[0]
            elif isinstance(contratti_payload, dict):
                contract_data = contratti_payload
            else:
                return Response(
                    {"contratti": "Formato non valido: atteso oggetto o lista."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not isinstance(contract_data, dict):
                return Response(
                    {"contratti": "Formato contratto non valido."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            contract_instance = target_user.contratti.filter(is_active=True).order_by("-data_ass", "-id").first()
            if contract_instance is None:
                contract_instance = target_user.contratti.order_by("-data_ass", "-id").first()

            if contract_instance is None:
                contract_serializer = ContrattoMiniSerializer(data=contract_data)
                if not contract_serializer.is_valid():
                    return Response({"contratti": contract_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
                contract_serializer.save(utente=target_user)
            else:
                contract_serializer = ContrattoMiniSerializer(contract_instance, data=contract_data, partial=True)
                if not contract_serializer.is_valid():
                    return Response({"contratti": contract_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
                contract_serializer.save()

    return Response(UtenteSerializer(target_user).data)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_account(request):
    if not request.user.is_superuser:
        return Response(
            {"errors": "Solo i superuser possono eliminare un account."},
            status=status.HTTP_403_FORBIDDEN
        )

    target_user_id, error_response = _resolve_target_user_id_for_delete(request)
    if error_response is not None:
        return error_response

    try:
        target_user = Utente.objects.get(pk=target_user_id)
    except Utente.DoesNotExist:
        return Response(
            {"errors": "Utente non trovato."},
            status=status.HTTP_404_NOT_FOUND
        )

    if target_user.is_superuser:
        return Response(
            {"errors": "I superuser non possono eliminare altri superuser."},
            status=status.HTTP_403_FORBIDDEN
        )

    deleted_id = target_user.id
    target_user.delete()
    return Response(
        {"message": "Account eliminato con successo.", "deleted_user_id": deleted_id},
        status=status.HTTP_200_OK
    )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def users_list(request):
    # if not _is_staff_or_super(request.user):
    #     return Response(
    #         {"errors": "Non hai i permessi per vedere questi utenti."},
    #         status=status.HTTP_403_FORBIDDEN,
    #     )

    qs = Utente.objects.all().order_by("email")
    serializer = UtenteSerializer(qs, many=True)
    return Response({
        "count": qs.count(),
        "results": serializer.data,
    })
