from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import calendar
from django.db import transaction
from decimal import Decimal
from datetime import date, timedelta
from django.db.models import Q
from ..models import TimeEntry, Utente, Saldo, Contratto
from ..serializer import TimeEntrySerializer, TimeEntryValidationSerializer
from ..pdfs import PresenzeMeseScorsoPDFView

def _is_staff_or_super(user):
    return user.is_staff or user.is_superuser

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


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def timeentry_create_range_override(request):
    """
    Body:
    {
      "utente_id": 5,
      "dataS": "2026-01-08",
      "dataE": "2026-01-12",
      "type": 2
    }

    Per ogni giorno lavorativo nel range [dataS, dataE]:
    - prende ore_tot da contratto.ore_sett[weekday]
    - garantisce UNA sola TimeEntry al giorno
    - se esistono più TimeEntry nel giorno: ne mantiene una, aggiorna type/ore_tot, elimina le altre
    """
    utente_id_param = request.data.get("utente_id")
    data_s_str = request.data.get("dataS")
    data_e_str = request.data.get("dataE")
    type_param = request.data.get("type")

    if utente_id_param is None or not data_s_str or not data_e_str or type_param is None:
        return Response(
            {"errors": "Parametri obbligatori: utente_id, dataS, dataE, type."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        utente_id = int(utente_id_param)
    except (TypeError, ValueError):
        return Response({"errors": "Parametro 'utente_id' non valido."}, status=status.HTTP_400_BAD_REQUEST)

    is_super = request.user.is_superuser
    is_owner = (utente_id == request.user.id)
    if not (is_super or is_owner):
        return Response(
            {"errors": "Non puoi modificare TimeEntry di altri utenti."},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        data_start = date.fromisoformat(data_s_str)
        data_end = date.fromisoformat(data_e_str)
    except ValueError:
        return Response(
            {"errors": "Parametri 'dataS'/'dataE' non validi. Usa il formato YYYY-MM-DD."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if data_start > data_end:
        return Response(
            {"errors": "'dataS' deve essere <= 'dataE'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        entry_type = int(type_param)
    except (TypeError, ValueError):
        return Response({"errors": "Parametro 'type' non valido."}, status=status.HTTP_400_BAD_REQUEST)

    valid_types = {choice[0] for choice in TimeEntry.EntryType.choices}
    if entry_type not in valid_types:
        return Response({"errors": "Parametro 'type' non valido."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        Utente.objects.only("id").get(pk=utente_id)
    except Utente.DoesNotExist:
        return Response({"errors": f"Utente con id {utente_id} non trovato."}, status=status.HTTP_404_NOT_FOUND)

    contract = (
        Contratto.objects
        .filter(utente_id=utente_id, is_active=True)
        .order_by("-data_ass", "-id")
        .first()
    )
    if not contract or not contract.ore_sett or len(contract.ore_sett) != 5:
        return Response(
            {"errors": "Nessun contratto attivo valido (ore_sett lun-ven) per l'utente."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    day_count = (data_end - data_start).days + 1
    giorni = [data_start + timedelta(days=i) for i in range(day_count)]

    created_count = 0
    updated_count = 0
    deleted_count = 0
    skipped_weekends = 0

    with transaction.atomic():
        for d in giorni:
            if d.weekday() > 4:  # sab/dom: non mappabili su ore_sett[0..4]
                skipped_weekends += 1
                continue

            ore_day = Decimal(str(contract.ore_sett[d.weekday()]))
            day_entries = list(
                TimeEntry.objects
                .select_for_update()
                .filter(utente_id=utente_id, data=d)
                .order_by("id")
            )

            keeper = None
            for te in day_entries:
                if te.type == entry_type:
                    keeper = te
                    break
            if keeper is None and day_entries:
                keeper = day_entries[0]

            if keeper is None:
                TimeEntry.objects.create(
                    utente_id=utente_id,
                    data=d,
                    type=entry_type,
                    ore_tot=ore_day,
                    validation_level=TimeEntry.ValidationLevel.VALIDATO_UTENTE,
                )
                created_count += 1
                continue

            if (
                keeper.type != entry_type
                or Decimal(str(keeper.ore_tot)) != ore_day
                or keeper.validation_level != TimeEntry.ValidationLevel.VALIDATO_UTENTE
            ):
                keeper.type = entry_type
                keeper.ore_tot = ore_day
                keeper.validation_level = TimeEntry.ValidationLevel.VALIDATO_UTENTE
                keeper.save(update_fields=["type", "ore_tot", "validation_level", "data_upd"])
                updated_count += 1

            for te in day_entries:
                if te.id == keeper.id:
                    continue
                te.delete()
                deleted_count += 1

    final_qs = (
        TimeEntry.objects
        .filter(utente_id=utente_id, data__gte=data_start, data__lte=data_end)
        .order_by("data", "id")
    )

    return Response(
        {
            "message": "Operazione completata.",
            "utente_id": utente_id,
            "periodo": {"dataS": data_start, "dataE": data_end},
            "type": entry_type,
            "created": created_count,
            "updated": updated_count,
            "deleted": deleted_count,
            "skipped_weekends": skipped_weekends,
            "count_final": final_qs.count(),
            "results": TimeEntrySerializer(final_qs, many=True).data,
        },
        status=status.HTTP_200_OK,
    )

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
    # --- 1. Validazione del body
    serializer = TimeEntryValidationSerializer(data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    new_level = serializer.validated_data.get("validation_level")
    if new_level is None:
        return Response(
            {"errors": "validation_level è obbligatorio."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    is_super = request.user.is_superuser

    # --- 2. Lettura, policy, scrittura sotto un unico lock ---
    with transaction.atomic():
        try:
            te = (
                TimeEntry.objects
                .select_for_update()
                .select_related("utente")
                .get(pk=te_id)
            )
        except TimeEntry.DoesNotExist:
            return Response(
                {"errors": "TimeEntry non trovato."},
                status=status.HTTP_404_NOT_FOUND,
            )

        old_level = te.validation_level
        is_owner = (te.utente_id == request.user.id)

        # --- 2a. Stato terminale ---
        if old_level == TimeEntry.ValidationLevel.VALIDATO_ADMIN:
            return Response(
                {"errors": "TimeEntry già validata dal superadmin: non modificabile."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # --- 2b. Policy sulla transizione ---
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

        # --- 2c. Scrittura ---
        te.validation_level = new_level
        te.save(update_fields=["validation_level", "data_upd"])

        # --- 2d. Aggiornamento saldo (solo quando diventa VALIDATO_ADMIN
        #         su versamento/prelievo banca ore) ---
        if (
            new_level == TimeEntry.ValidationLevel.VALIDATO_ADMIN
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


