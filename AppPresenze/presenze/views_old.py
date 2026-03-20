from django.contrib.auth import update_session_auth_hash, authenticate, logout
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
import calendar
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from decimal import Decimal
# import per la vista che gestisce la logica dell'endpoint per la raccolta delle timeentries
from datetime import date
from django.db.models import Q
from .models import TimeEntry, Utente, Saldo, Trasferta, Spesa
from .pdfs import PresenzeMeseScorsoPDFView
from .serializer import TimeEntrySerializer, TimeEntryValidationSerializer, UtenteSerializer, TrasfertaSerializer, SpesaSerializer
from .utils import update_saldo_for_timeentry
# ---------------------------
# AUTH API (Login/Logout)
# ---------------------------

@api_view(['POST'])
@permission_classes([AllowAny])
def api_login(request):
    """Login Bearer-only: restituisce un token per Authorization: Bearer token.

    Body: { "email"|"username": "...", "password": "..." }
    Ritorna: { "token": "...", "token_type": "Bearer", "user": { ... } }
    """
    email = request.data.get('email') or request.data.get('username')
    password = request.data.get('password')
    if not email or not password:
        return Response({"error": "Email e password sono obbligatori"}, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(request, username=email, password=password)
    if user is None or not user.is_active:
        return Response({"error": "Credenziali non valide"}, status=status.HTTP_400_BAD_REQUEST)

    token, _ = Token.objects.get_or_create(user=user)
    return Response({
        "token": token.key,
        "token_type": "Bearer",
        "user": UtenteSerializer(user).data,
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def get_token(request):
    """Rilascia un Bearer token (DRF Token) a fronte di email/password.
    Body: { "email": "...", "password": "..." } o { "username": "...", "password": "..." }
    Ritorna: { "token": "...", "token_type": "Bearer", "user": { ... } }
    """
    email = request.data.get('email')
    username = request.data.get('username')
    password = request.data.get('password')

    login_username = email or username
    if not login_username or not password:
        return Response(
            {"error": "Email/username e password sono obbligatori"},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = authenticate(request, username=login_username, password=password)
    if user is None or not user.is_active:
        return Response(
            {"error": "Credenziali non valide"},
            status=status.HTTP_400_BAD_REQUEST
        )

    token, _ = Token.objects.get_or_create(user=user)
    return Response({
        "token": token.key,
        "token_type": "Bearer",
        "user": UtenteSerializer(user).data,
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_logout(request):
    """Logout della sessione corrente."""
    logout(request)
    request.user.auth_token.delete() # Con questa riga viene rimosso anche il token presente a DB e l'utente fa logout da qualsiasi client
    return Response({"message": "Logout effettuato"})

# ---------------------------
# ACCOUNT
# ---------------------------

def _is_staff_or_super(user):
    return user.is_staff or user.is_superuser

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
    if request.method == 'GET':
        return Response(UtenteSerializer(request.user).data)

    serializer = UtenteSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(UtenteSerializer(request.user).data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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

# ---------------------------
# TimeEntries
# ---------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def time_entries_from_month_to_previous(request):
    """
    GET /presenze/api/time-entries/from-month-to-previous?[u_id=...][&data=YYYY-MM-DD]

    Logica:
    - Se arriva solo utente_id:
        -> TimeEntry di quell'utente del mese corrente + mese precedente
        -> consentito se requester è lo stesso utente o superuser
    - Se non arriva nulla:
        -> 400 BAD REQUEST
    - Se arriva solo data:
        -> TimeEntry di tutti gli utenti del mese di data + mese precedente
        -> consentito solo superuser
    - Se arrivano utente_id e data:
        -> TimeEntry dell'utente del mese di data + mese precedente
        -> consentito se requester è lo stesso utente o superuser
    """

    utente_id_param = request.query_params.get("u_id")
    data_str = request.query_params.get("data")

    # almeno uno dei due parametri deve essere presente
    if not utente_id_param and not data_str:
        return Response(
            {"errors": "Devi passare almeno uno tra 'u_id' e 'data'."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # parsing utente_id (se presente)
    utente_id = None
    if utente_id_param:
        try:
            utente_id = int(utente_id_param)
        except (TypeError, ValueError):
            return Response(
                {"errors": "Parametro 'u_id' non valido."},
                status=status.HTTP_400_BAD_REQUEST
            )

    # parsing data (se presente)
    data_date = None
    if data_str:
        try:
            data_date = date.fromisoformat(data_str)
        except ValueError:
            return Response(
                {"errors": "Parametro 'data' non valido. Usa il formato YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST
            )

    is_super = request.user.is_superuser
    is_owner = (utente_id is not None and request.user.id == utente_id)

    # --- controlli permessi ---
    # solo utente_id
    if utente_id is not None and data_date is None:
        print(f"is_super: {is_super}")
        print(f"is_owner: {is_owner}")
        if not (is_super or is_owner):
            return Response(
                {"errors": "Non hai i permessi per vedere le TimeEntry di questo utente."},
                status=status.HTTP_403_FORBIDDEN
            )

    # solo data
    if utente_id is None and data_date is not None:
        if not is_super:
            return Response(
                {"errors": "Solo un superuser può richiedere le TimeEntry di tutti gli utenti per un mese specifico."},
                status=status.HTTP_403_FORBIDDEN
            )

    # utente_id + data
    if utente_id is not None and data_date is not None:
        if not (is_super or is_owner):
            return Response(
                {"errors": "Non hai i permessi per vedere le TimeEntry di questo utente."},
                status=status.HTTP_403_FORBIDDEN
            )

    # --- calcolo periodo: mese base + mese precedente ---

    today = date.today()
    base = data_date or today
    base_year, base_month = base.year, base.month

    # mese precedente
    if base_month == 1:
        prev_year, prev_month = base_year - 1, 12
    else:
        prev_year, prev_month = base_year, base_month - 1

    start_date = date(prev_year, prev_month, 1)
    last_day_base = calendar.monthrange(base_year, base_month)[1]
    end_date = date(base_year, base_month, last_day_base)

    # evita date future
    # if end_date > today:
    #     end_date = today

    qs = (
        TimeEntry.objects
        .filter(data__gte=start_date, data__lte=end_date)
        .select_related("utente")
        .order_by("-data", "utente__email")
    )

    if utente_id is not None:
        qs = qs.filter(utente_id=utente_id)

    serializer = TimeEntrySerializer(qs, many=True)
    return Response({
        "count": qs.count(),
        "period": {"from": start_date, "to": end_date},
        "results": serializer.data
    })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def timeentry_create(request):
    """
    POST /presenze/api/time-entries/
    Body:
    {
      "utente_id": 5,
      "data": "2026-01-08",
      "type": 1,
      "ore_tot": "8.00",
      "validation_level": 0   # opzionale
    }
    """
    serializer = TimeEntrySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    utente_id = serializer.validated_data["utente_id"]
    if not _is_staff_or_super(request.user) and utente_id != request.user.id:
        return Response(
            {"errors": "Non puoi creare TimeEntry per altri utenti."},
            status=status.HTTP_403_FORBIDDEN,
        )
    requested_level = serializer.validated_data.get("validation_level", TimeEntry.ValidationLevel.AUTO)
    if not _is_staff_or_super(request.user) and requested_level == TimeEntry.ValidationLevel.VALIDATO_ADMIN:
        return Response(
            {"errors": "Solo admin può impostare VALIDATO_ADMIN."},
            status=status.HTTP_403_FORBIDDEN,
        )

    te = serializer.save()
    return Response(TimeEntrySerializer(te).data, status=status.HTTP_201_CREATED)

@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def timeentry_detail(request, te_id: int):
    try:
        te = TimeEntry.objects.select_related("utente").get(pk=te_id)
    except TimeEntry.DoesNotExist:
        return Response(
            {"errors": "TimeEntry non trovato."}, 
            status=status.HTTP_404_NOT_FOUND
        )

    is_owner = (te.utente_id == request.user.id)
    is_super = request.user.is_superuser
    
    if not (is_owner or is_super):
        return Response(
            {"errors": "Non hai i permessi per questa operazione."},
            status=status.HTTP_403_FORBIDDEN
        )

    # GET - Dettaglio
    if request.method == "GET":
        return Response(TimeEntrySerializer(te).data, status=status.HTTP_200_OK)

    # DELETE
    elif request.method == "DELETE":
        if te.validation_level == TimeEntry.ValidationLevel.VALIDATO_ADMIN:
            return Response(
                {"errors": "TimeEntry validata dall'admin: non può essere cancellata."},
                status=status.HTTP_403_FORBIDDEN,
            )
        te.delete()
        return Response(
            {"message": "TimeEntry cancellata con successo."},
            status=status.HTTP_204_NO_CONTENT
        )

    # PUT
    elif request.method == "PUT":
        if te.validation_level == TimeEntry.ValidationLevel.VALIDATO_ADMIN:
            return Response(
                {"errors": "TimeEntry già validata dal superadmin: non modificabile."},
                status=status.HTTP_403_FORBIDDEN,
            )

        old_level = te.validation_level
        serializer = TimeEntrySerializer(te, data=request.data)  
        serializer.is_valid(raise_exception=True)

        requested_level = serializer.validated_data.get("validation_level", old_level)
        if requested_level == TimeEntry.ValidationLevel.VALIDATO_ADMIN:
            return Response(
                {"errors": "Non puoi validare a livello admin con PUT. Usa /validation/."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if requested_level < old_level:
            return Response(
                {"errors": f"Downgrade: {old_level} -> {requested_level} non consentito."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        te = serializer.save()
        if not is_super:
            if te.validation_level == TimeEntry.ValidationLevel.AUTO:
                te.validation_level = TimeEntry.ValidationLevel.VALIDATO_UTENTE
                te.save(update_fields=["validation_level"])

        return Response(TimeEntrySerializer(te).data, status=status.HTTP_200_OK)

@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def timeentry_update_validation_level(request, te_id: int):
    """
    PATCH /presenze/api/time-entries/<te_id>/validation/
    Body: { "validation_level": 1 } oppure { "validation_level": 2 }

    Policy:
    - Utente normale: SOLO 0 -> 1, SOLO sulle proprie TimeEntry
    - Superuser: SOLO 1 -> 2 (anche su TimeEntry di altri utenti)
    - Se già a 2: non modificabile
    - Aggiorna SOLO saldo validato e SOLO quando diventa VALIDATO_ADMIN (2) su type 3/4
    """
    try:
        te = TimeEntry.objects.select_related("utente").get(pk=te_id)
    except TimeEntry.DoesNotExist:
        return Response({"errors": "TimeEntry non trovato."}, status=status.HTTP_404_NOT_FOUND)

    serializer = TimeEntryValidationSerializer(te, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)

    new_level = serializer.validated_data.get("validation_level")
    if new_level is None:
        return Response({"errors": "validation_level è obbligatorio."}, status=status.HTTP_400_BAD_REQUEST)

    old_level = te.validation_level

    if old_level == TimeEntry.ValidationLevel.VALIDATO_ADMIN:
        return Response(
            {"errors": "TimeEntry già validata dal superadmin: non modificabile."},
            status=status.HTTP_403_FORBIDDEN,
        )

    is_super = request.user.is_superuser
    is_owner = (te.utente_id == request.user.id)

    if is_super:
        if not (old_level == TimeEntry.ValidationLevel.VALIDATO_UTENTE and
                new_level == TimeEntry.ValidationLevel.VALIDATO_ADMIN):
            return Response(
                {"errors": "Il superuser può solo validare da 1 a 2."},
                status=status.HTTP_403_FORBIDDEN,
            )
    elif is_owner:
        if not (old_level == TimeEntry.ValidationLevel.AUTO and
                new_level == TimeEntry.ValidationLevel.VALIDATO_UTENTE):
            return Response(
                {"errors": "Puoi solo validare da 0 a 1 sulle tue TimeEntry."},
                status=status.HTTP_403_FORBIDDEN,
            )
    else:
        return Response(
            {"errors": "Non puoi validare TimeEntry altrui"},
            status=status.HTTP_403_FORBIDDEN,
        )

    with transaction.atomic():
        te = TimeEntry.objects.select_for_update().select_related("utente").get(pk=te_id)
        if te.validation_level == TimeEntry.ValidationLevel.VALIDATO_ADMIN:
            return Response(
                {"errors": "TimeEntry già validata dal superadmin: non modificabile."},
                status=status.HTTP_403_FORBIDDEN,
            )

        prev_level = te.validation_level
        te.validation_level = new_level
        te.save(update_fields=["validation_level"])
        if (
            prev_level != TimeEntry.ValidationLevel.VALIDATO_ADMIN
            and new_level == TimeEntry.ValidationLevel.VALIDATO_ADMIN
            and te.type in (
                TimeEntry.EntryType.VERSAMENTO_BANCA_ORE,
                TimeEntry.EntryType.PRELIEVO_BANCA_ORE,
            )
        ):
            saldo = Saldo.objects.select_for_update().get(utente=te.utente)

            ore = Decimal(str(te.ore_tot))
            delta = ore if te.type == TimeEntry.EntryType.VERSAMENTO_BANCA_ORE else -ore

            saldo.valore_saldo_validato += delta
            saldo.save(update_fields=["valore_saldo_validato", "data_upd"])

    return Response(TimeEntrySerializer(te).data, status=status.HTTP_200_OK)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def timeentry_bulk_validate_month(request):
    """
    PATCH /presenze/api/time-entries/bulk-validate-month/

    Caso 1 - Superuser:
      Body: { "utente_id": 5, "data": "2026-01-15" }
      - Aggiorna validation_level da 1 a 2 (VALIDATO_UTENTE -> VALIDATO_ADMIN)
        per tutte le TimeEntry dell'utente nel mese indicato con validation_level=1
      - Aggiorna SOLO saldo validato (valore_saldo_validato) per type 3/4

    Caso 2 - Utente normale:
      Body: { "data": "2026-01-15" }
      - Aggiorna validation_level da 0 a 1 (AUTO -> VALIDATO_UTENTE) per le proprie TimeEntry nel mese
      - NON aggiorna il saldo
    """
    data_str = request.data.get("data")
    utente_id_param = request.data.get("utente_id")

    if not data_str:
        return Response({"errors": "Il parametro 'data' è obbligatorio."},
                        status=status.HTTP_400_BAD_REQUEST)

    try:
        data_date = date.fromisoformat(data_str)
    except ValueError:
        return Response({"errors": "Parametro 'data' non valido. Usa il formato YYYY-MM-DD."},
                        status=status.HTTP_400_BAD_REQUEST)

    is_super = request.user.is_superuser

    year, month = data_date.year, data_date.month
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])


    if is_super and utente_id_param is not None:
        try:
            utente_id = int(utente_id_param)
        except (TypeError, ValueError):
            return Response({"errors": "Parametro 'utente_id' non valido."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            target_user = Utente.objects.get(pk=utente_id)
        except Utente.DoesNotExist:
            return Response({"errors": f"Utente con id {utente_id} non trovato."},
                            status=status.HTTP_404_NOT_FOUND)

        qs = TimeEntry.objects.filter(
            utente_id=utente_id,
            data__gte=first_day,
            data__lte=last_day,
            validation_level=TimeEntry.ValidationLevel.VALIDATO_UTENTE
        )

        count_updated = qs.count()

        with transaction.atomic():
            saldo = Saldo.objects.select_for_update().get(utente_id=utente_id)

            banca_qs = qs.filter(
                type__in=[
                    TimeEntry.EntryType.VERSAMENTO_BANCA_ORE,
                    TimeEntry.EntryType.PRELIEVO_BANCA_ORE,
                ]
            ).values_list("type", "ore_tot")

            total_delta = Decimal("0.00")
            for entry_type, ore_tot in banca_qs:
                ore = Decimal(str(ore_tot))
                total_delta += ore if entry_type == TimeEntry.EntryType.VERSAMENTO_BANCA_ORE else -ore

            qs.update(validation_level=TimeEntry.ValidationLevel.VALIDATO_ADMIN)
            if total_delta != Decimal("0.00"):
                saldo.valore_saldo_validato += total_delta
                saldo.save(update_fields=["valore_saldo_validato", "data_upd"])

        return Response({
            "message": f"Aggiornate {count_updated} TimeEntry da validation_level 1 a 2.",
            "utente_id": utente_id,
            "utente_email": target_user.email,
            "mese": f"{year}-{month:02d}",
            "count_updated": count_updated,
            "delta_saldo_validato": str(total_delta),
        }, status=status.HTTP_200_OK)


    if utente_id_param is not None and not is_super:
        return Response({"errors": "Solo i superuser possono validare le TimeEntry di altri utenti."},
                        status=status.HTTP_403_FORBIDDEN)

    qs = TimeEntry.objects.filter(
        utente_id=request.user.id,
        data__gte=first_day,
        data__lte=last_day,
        validation_level=TimeEntry.ValidationLevel.AUTO
    )

    count_updated = qs.count()
    qs.update(validation_level=TimeEntry.ValidationLevel.VALIDATO_UTENTE)

    return Response({
        "message": f"Aggiornate {count_updated} TimeEntry da validation_level 0 a 1.",
        "utente_id": request.user.id,
        "utente_email": request.user.email,
        "mese": f"{year}-{month:02d}",
        "count_updated": count_updated
    }, status=status.HTTP_200_OK)

def presenze_mese_scorso_pdf(request):
    return PresenzeMeseScorsoPDFView.as_view()(request)

# ---------------------------
# Trasferte     
#  POST /presenze/api/trasferte/
#    Body: { "data": "2026-02-05", "utente": 5 (solo se superuser) }   
# --------------------------- 

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def trasferta_create(request):
    """
    POST api/presenze/trasferte/
    Crea una nuova trasferta. Richiede: data e azienda.
    L'indirizzo è opzionale.
    """
    data_str = request.data.get("data")
    azienda = request.data.get("azienda")
    utente_email_param = request.data.get("utente_email")
    is_super = request.user.is_superuser

    if not data_str:
        return Response(
            {"errors": "La data è obbligatoria."}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not azienda:
        return Response(
            {"errors": "Il nome azienda è obbligatorio."}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    data = {
        "data": data_str,
        "azienda": azienda,
        "validation_level": 1
    }
    
    if "indirizzo" in request.data:
        data["indirizzo"] = request.data.get("indirizzo")

    
    if is_super:
        if not utente_email_param:
            return Response(
                {"errors": "Come superuser devi passare utente_email."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            utente = Utente.objects.get(email=utente_email_param)
        except Utente.DoesNotExist:
            return Response(
                {"errors": "Utente non trovato."},
                status=status.HTTP_400_BAD_REQUEST
            )

        data["utente"] = utente.id

    else:
        data["utente"] = request.user.id

    serializer = TrasfertaSerializer(data=data)
    if serializer.is_valid():
        te = serializer.save()
        return Response(TrasfertaSerializer(te).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def trasferta_update(request, t_id: int):
    """
    PUT /api/presenze/trasferte/<t_id>/
    Permette di modificare i campi (coefficiente, note, automobile, data, azienda, indirizzo).
    L'utente normale non può cambiare il proprietario (utente).
    """
    try:
        trasferta = Trasferta.objects.get(pk=t_id)
    except Trasferta.DoesNotExist:
        return Response(
            {"errors": "Trasferta non trovata."}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    if trasferta.validation_level == Trasferta.ValidationLevel.VALIDATO_ADMIN:
        return Response(
            {"errors": "Trasferta già validata dal superadmin: non modificabile."},
            status=status.HTTP_403_FORBIDDEN,
        )
    
    is_super = request.user.is_superuser
    is_owner = (trasferta.utente_id == request.user.id)

    if not (is_super or is_owner):
        return Response(
            {"errors": "Non hai i permessi per modificare questa trasferta."}, 
            status=status.HTTP_403_FORBIDDEN
        )

    data = request.data.copy()

    serializer = TrasfertaSerializer(trasferta, data=data, partial=True)
    
    if serializer.is_valid():
        trasferta_aggiornata = serializer.save()
        return Response(
            TrasfertaSerializer(trasferta_aggiornata).data, 
            status=status.HTTP_200_OK
        )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def trasferte_validation_level(request, tr_id: int):
    """
    PATCH /api/presenze/trasferte/<tr_id>/validation/
    Valida una trasferta da livello 1 a 2 (solo superadmin).
    """
    try:
        tr = Trasferta.objects.select_related("utente").get(pk=tr_id)
    except Trasferta.DoesNotExist:
        return Response(
            {"errors": "Trasferta non trovata."}, 
            status=status.HTTP_404_NOT_FOUND
        )

    old_level = tr.validation_level

    if old_level == Trasferta.ValidationLevel.VALIDATO_ADMIN:
        return Response(
            {"errors": "Trasferta già validata dal superadmin: non modificabile."},
            status=status.HTTP_403_FORBIDDEN,
        )

    is_super = request.user.is_superuser

    if not is_super:
        return Response(
            {"errors": "Le trasferte sono validate solo da admin."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if old_level != Trasferta.ValidationLevel.VALIDATO_UTENTE:
        return Response(
            {"errors": "Solo le trasferte a livello 1 possono essere validate a 2."},
            status=status.HTTP_403_FORBIDDEN,
        )

    tr.validation_level = Trasferta.ValidationLevel.VALIDATO_ADMIN
    tr.save(update_fields=["validation_level"])
    return Response(TrasfertaSerializer(tr).data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def trasferta_list(request):
    """
    GET api/presenze/trasferte/
    Lista tutte le trasferte con filtri opzionali:
    - limit (int): numero massimo di record da restituire
    - date (string YYYY-MM-DD): filtra trasferte dalla data specificata in poi
    - uId (int): filtra per ID utente
    - validation (int): filtra per validation_level (1 o 2)
    - azienda (string): filtra per nome azienda (case-insensitive, parziale)
    - tId (int): filtra per ID trasferta
    
    Senza parametri mostra tutte le trasferte di tutti gli utenti.
    """
    queryset = Trasferta.objects.select_related('utente', 'automobile').all()

    # Filtro per ID trasferta
    t_id_param = request.query_params.get('tId')
    if t_id_param:
        try:
            t_id = int(t_id_param)
            queryset = queryset.filter(id=t_id)
        except ValueError:
            return Response(
                {"errors": "Il parametro 'tId' deve essere un numero intero."},
                status=status.HTTP_400_BAD_REQUEST
            )
    # Filtro per utente
    u_id = request.query_params.get('uId')
    if u_id:
        try:
            u_id = int(u_id)
            queryset = queryset.filter(utente_id=u_id)
        except ValueError:
            return Response(
                {"errors": "Il parametro 'uId' deve essere un numero intero."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Filtro per data (dalla data in poi)
    date_param = request.query_params.get('date')
    if date_param:
        try:
            queryset = queryset.filter(data__gte=date_param)
        except Exception:
            return Response(
                {"errors": "Il parametro 'date' deve essere nel formato YYYY-MM-DD."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Filtro per validation_level
    validation_param = request.query_params.get('validation')
    if validation_param:
        try:
            validation_level = int(validation_param)
            if validation_level not in [1, 2]:
                return Response(
                    {"errors": "Il parametro 'validation' deve essere 1 o 2."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            queryset = queryset.filter(validation_level=validation_level)
        except ValueError:
            return Response(
                {"errors": "Il parametro 'validation' deve essere un numero intero."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Filtro per azienda (case-insensitive, parziale)
    azienda_param = request.query_params.get('azienda')
    if azienda_param:
        queryset = queryset.filter(azienda__icontains=azienda_param)
    
    # Ordinamento per data (dalla più recente)
    queryset = queryset.order_by('-data')
    
    # Limite risultati
    limit_param = request.query_params.get('limit')
    if limit_param:
        try:
            limit = int(limit_param)
            if limit <= 0:
                return Response(
                    {"errors": "Il parametro 'limit' deve essere maggiore di 0."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            queryset = queryset[:limit]
        except ValueError:
            return Response(
                {"errors": "Il parametro 'limit' deve essere un numero intero."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    serializer = TrasfertaSerializer(queryset, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def trasferta_delete(request, t_id: int):
    """
    DELETE api/presenze/trasferte/<t_id>/
    Elimina una trasferta solo se validation_level non è 2.
    Solo il proprietario o un superadmin può eliminare.
    """
    try:
        trasferta = Trasferta.objects.get(pk=t_id)
    except Trasferta.DoesNotExist:
        return Response(
            {"errors": "Trasferta non trovata."}, 
            status=status.HTTP_404_NOT_FOUND
        )
    if trasferta.validation_level == Trasferta.ValidationLevel.VALIDATO_ADMIN:
        return Response(
            {"errors": "Trasferta validata dal superadmin: non eliminabile."},
            status=status.HTTP_403_FORBIDDEN,
        )
    is_super = request.user.is_superuser
    is_owner = (trasferta.utente_id == request.user.id)

    if not (is_super or is_owner):
        return Response(
            {"errors": "Non hai i permessi per eliminare questa trasferta."}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    trasferta.delete()
    return Response(
        {"message": "Trasferta eliminata con successo."}, 
        status=status.HTTP_204_NO_CONTENT
    )


# ---------------------------
# Spese  
# ---------------------------


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def spesa_list_by_trasferta(request, t_id: int):
    """
    GET /presenze/api/trasferte/<t_id>/spese/
    Lista tutte le spese associate a una specifica trasferta.
    """
    try:
        trasferta = Trasferta.objects.get(pk=t_id)
    except Trasferta.DoesNotExist:
        return Response(
            {"errors": "Trasferta non trovata."}, 
            status=status.HTTP_404_NOT_FOUND
        )
    is_super = request.user.is_superuser
    is_owner = (trasferta.utente_id == request.user.id)

    if not (is_super or is_owner):
        return Response(
            {"errors": "Non hai i permessi per visualizzare le spese di questa trasferta."}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    spese = Spesa.objects.filter(trasferta_id=t_id).order_by('-data_creaz')
    serializer = SpesaSerializer(spese, many=True)
    
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def spesa_manage(request, t_id: int = None, s_id: int = None):
    """
    POST /presenze/api/trasferte/<t_id>/spese/ - Crea una nuova spesa
    PUT /presenze/api/spese/<s_id>/ - Modifica una spesa esistente
    DELETE /presenze/api/spese/<s_id>/ - Elimina una spesa
    
    Non è possibile creare/modificare/eliminare spese di trasferte validate dall'admin.
    """
    if request.method == "POST":
        if not t_id:
            return Response(
                {"errors": "ID trasferta richiesto per la creazione."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            trasferta = Trasferta.objects.get(pk=t_id)
        except Trasferta.DoesNotExist:
            return Response(
                {"errors": "Trasferta non trovata."}, 
                status=status.HTTP_404_NOT_FOUND
            )

        if trasferta.validation_level == Trasferta.ValidationLevel.VALIDATO_ADMIN:
            return Response(
                {"errors": "Non è possibile aggiungere spese a una trasferta validata dall'admin."},
                status=status.HTTP_403_FORBIDDEN,
            )

        is_super = request.user.is_superuser
        is_owner = (trasferta.utente_id == request.user.id)

        if not (is_super or is_owner):
            return Response(
                {"errors": "Non hai i permessi per aggiungere spese a questa trasferta."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        data = request.data.copy()
        data['trasferta'] = t_id
        
        serializer = SpesaSerializer(data=data)
        if serializer.is_valid():
            spesa = serializer.save()
            return Response(SpesaSerializer(spesa).data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "PUT":
        if not s_id:
            return Response(
                {"errors": "ID spesa richiesto per la modifica."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            spesa = Spesa.objects.select_related('trasferta', 'trasferta__utente').get(pk=s_id)
        except Spesa.DoesNotExist:
            return Response(
                {"errors": "Spesa non trovata."}, 
                status=status.HTTP_404_NOT_FOUND
            )

        if spesa.trasferta.validation_level == Trasferta.ValidationLevel.VALIDATO_ADMIN:
            return Response(
                {"errors": "Non è possibile modificare spese di trasferte validate dall'admin."},
                status=status.HTTP_403_FORBIDDEN,
            )

        is_super = request.user.is_superuser
        is_owner = (spesa.trasferta.utente_id == request.user.id)

        if not (is_super or is_owner):
            return Response(
                {"errors": "Non hai i permessi per modificare questa spesa."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        data = request.data.copy()
        if 'trasferta' in data:
            del data['trasferta']
        
        serializer = SpesaSerializer(spesa, data=data, partial=True)
        if serializer.is_valid():
            spesa_aggiornata = serializer.save()
            return Response(SpesaSerializer(spesa_aggiornata).data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        if not s_id:
            return Response(
                {"errors": "ID spesa richiesto per l'eliminazione."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            spesa = Spesa.objects.select_related('trasferta', 'trasferta__utente').get(pk=s_id)
        except Spesa.DoesNotExist:
            return Response(
                {"errors": "Spesa non trovata."}, 
                status=status.HTTP_404_NOT_FOUND
            )

        if spesa.trasferta.validation_level == Trasferta.ValidationLevel.VALIDATO_ADMIN:
            return Response(
                {"errors": "Non è possibile eliminare spese di trasferte validate dall'admin."},
                status=status.HTTP_403_FORBIDDEN,
            )

        is_super = request.user.is_superuser
        is_owner = (spesa.trasferta.utente_id == request.user.id)

        if not (is_super or is_owner):
            return Response(
                {"errors": "Non hai i permessi per eliminare questa spesa."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        spesa.delete()
        return Response(
            {"message": "Spesa eliminata con successo."}, 
            status=status.HTTP_204_NO_CONTENT
        )