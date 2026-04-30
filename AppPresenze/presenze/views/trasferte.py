import zipfile
import tempfile
import uuid
import hashlib
from calendar import monthrange
from datetime import date
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ..models import Utente, Trasferta, Signature, SignatureEvent
from ..serializer import TrasfertaSerializer
from ..TrasfertePDF import (
    TrasfertePDFView,
    build_trasferte_pdf_bytes,
    _get_client_ip,
    _signature_to_temp_file,
)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def trasferta_create(request):
    """
    POST api/presenze/trasferte/
    Crea una nuova trasferta. Richiede: data e azienda.
    L'indirizzo Ã¨ opzionale.
    """
    data_str = request.data.get("data")
    azienda = request.data.get("azienda")
    utente_email_param = request.data.get("utente_email")
    is_super = request.user.is_superuser

    if not data_str:
        return Response(
            {"errors": "La data Ã¨ obbligatoria."}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not azienda:
        return Response(
            {"errors": "Il nome azienda Ã¨ obbligatorio."}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    data = {
        "data": data_str,
        "azienda": azienda,
        "validation_level": Trasferta.ValidationLevel.AUTO
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
    Permette di modificare i campi (note, automobile, data, azienda, indirizzo).
    L'utente normale non puÃ² cambiare il proprietario (utente).
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
            {"errors": "Trasferta giÃ  validata dal superadmin: non modificabile."},
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
    if not is_super and "utente" in data:
        data.pop("utente")

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

    Policy:
    - Owner non-superuser: validazione automatica 0 -> 1 sulla propria trasferta
    - Superuser: validazione automatica 1 -> 2
    - Se già a 2: non modificabile
    """
    try:
        tr = Trasferta.objects.select_related("utente").get(pk=tr_id)
    except Trasferta.DoesNotExist:
        return Response(
            {"errors": "Trasferta non trovata."},
            status=status.HTTP_404_NOT_FOUND
        )

    old_level = tr.validation_level
    is_super = request.user.is_superuser
    is_owner = tr.utente_id == request.user.id

    if old_level == Trasferta.ValidationLevel.VALIDATO_ADMIN:
        return Response(
            {"errors": "Trasferta già validata dal superadmin: non modificabile."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if is_super:
        if old_level != Trasferta.ValidationLevel.VALIDATO_UTENTE:
            return Response(
                {"errors": "Il superuser può solo validare da 1 a 2."},
                status=status.HTTP_403_FORBIDDEN,
            )
        new_level = Trasferta.ValidationLevel.VALIDATO_ADMIN
    elif is_owner:
        if old_level != Trasferta.ValidationLevel.AUTO:
            return Response(
                {"errors": "Puoi solo validare da 0 a 1 sulle tue trasferte."},
                status=status.HTTP_403_FORBIDDEN,
            )
        new_level = Trasferta.ValidationLevel.VALIDATO_UTENTE
    else:
        return Response(
            {"errors": "Non puoi validare trasferte altrui."},
            status=status.HTTP_403_FORBIDDEN,
        )

    tr.validation_level = new_level
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
    - validation (int): filtra per validation_level (0, 1 o 2)
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
            if validation_level not in [0, 1, 2]:
                return Response(
                    {"errors": "Il parametro 'validation' deve essere 0, 1 o 2."},
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
    
    # Ordinamento per data (dalla piÃ¹ recente)
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
    Elimina una trasferta solo se validation_level non Ã¨ 2.
    Solo il proprietario o un superadmin puÃ² eliminare.
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

@permission_classes([IsAuthenticated])
def trasferte_mese_scorso_pdf(request):
    return TrasfertePDFView.as_view()(request)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def trasferta_dossier(request, u_id: int, data: str):
    """
    GET /api/presenze/trasferte/<u_id>/<data>/dossier/
    Crea un dossier ZIP contenente, per l'utente e il mese della data indicata:
    - PDF trasferte del mese
    - tutti gli scontrini delle trasferte del mese
    - tutti i PDF auto presenti in PDF_ROOT/<MM_YYYY>/<auto_id>.pdf
    """
    try:
        reference_date = date.fromisoformat(data)
    except ValueError:
        return Response(
            {"errors": "Parametro 'data' non valido. Usa YYYY-MM-DD."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    is_super = request.user.is_superuser
    is_owner = request.user.id == u_id
    if not (is_super or is_owner):
        return Response(
            {"errors": "Non hai i permessi per questo utente."},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        user = Utente.objects.get(pk=u_id)
    except Utente.DoesNotExist:
        return Response(
            {"errors": "Utente non trovato."},
            status=status.HTTP_404_NOT_FOUND,
        )

    month_start = reference_date.replace(day=1)
    month_end = date(
        reference_date.year,
        reference_date.month,
        monthrange(reference_date.year, reference_date.month)[1],
    )

    trasferte_mese = list(
        Trasferta.objects.filter(
            utente_id=u_id,
            data__range=(month_start, month_end),
        )
        .select_related("utente", "automobile")
        .prefetch_related("spese")
        .order_by("data", "id")
    )

    if not trasferte_mese:
        return Response(
            {"errors": "Nessuna trasferta trovata per utente e mese richiesti."},
            status=status.HTTP_404_NOT_FOUND,
        )

    reference_trasferta = trasferte_mese[0]
    firma_status = "ok"
    signature_used = (
        Signature.objects
        .filter(user_id=user.id)
        .order_by("-updated_at", "-created_at")
        .first()
    )
    firma_enabled = signature_used is not None
    if not firma_enabled:
        firma_status = "firma mancante"

    temp_dir = None
    firma_path = None
    if signature_used is not None:
        temp_dir = tempfile.TemporaryDirectory()
        firma_path = _signature_to_temp_file(signature_used, temp_dir.name)
        if firma_path is None:
            firma_enabled = False
            firma_status = "firma mancante"

    signature_applied = False
    try:
        try:
            pdf_trasferte = build_trasferte_pdf_bytes(
                user=user,
                trasferte=trasferte_mese,
                period_start=month_start,
                firma=firma_enabled,
                firma_path=firma_path,
                reference_trasferta=reference_trasferta,
            )
            signature_applied = firma_enabled
        except ValidationError:
            # Fallback: se la firma non Ã¨ utilizzabile (es. SVG non supportato in docx),
            # genera comunque il dossier senza firma.
            firma_status = "firma mancante"
            signature_applied = False
            pdf_trasferte = build_trasferte_pdf_bytes(
                user=user,
                trasferte=trasferte_mese,
                period_start=month_start,
                firma=False,
                firma_path=None,
                reference_trasferta=reference_trasferta,
            )
    except Http404 as exc:
        if temp_dir is not None:
            temp_dir.cleanup()
        return Response({"errors": str(exc)}, status=status.HTTP_404_NOT_FOUND)
    except ValidationError as exc:
        if temp_dir is not None:
            temp_dir.cleanup()
        return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)
    except Exception as exc:
        if temp_dir is not None:
            temp_dir.cleanup()
        return Response(
            {"errors": f"Errore generazione PDF: {exc}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()

    if signature_applied and signature_used is not None:
        SignatureEvent.objects.create(
            signature=signature_used,
            user=request.user,
            event_type=SignatureEvent.EventType.USED,
            document_id=uuid.uuid4(),
            document_sha256=hashlib.sha256(pdf_trasferte).hexdigest(),
            ip_address=_get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

    scontrini_root: Path = Path(settings.SCONTRINI_ROOT)
    scontrini_pairs: list[tuple[Path, str]] = []
    for tr in trasferte_mese:
        folder_name = f"{tr.data.strftime('%Y-%m-%d')}_{tr.id}"
        scontrini_folder = scontrini_root / folder_name
        if not scontrini_folder.exists():
            continue
        for file_path in sorted(scontrini_folder.iterdir()):
            if file_path.is_file():
                scontrini_pairs.append((file_path, f"scontrini/{folder_name}/{file_path.name}"))

    pdf_root: Path = Path(settings.PDF_ROOT)
    mese_anno = month_start.strftime("%m_%Y")
    auto_ids = sorted({tr.automobile_id for tr in trasferte_mese if tr.automobile_id})
    auto_pdf_expected = len(auto_ids) > 0
    auto_pdf_paths = []
    for auto_id in auto_ids:
        candidate = pdf_root / mese_anno / f"{auto_id}.pdf"
        if candidate.exists():
            auto_pdf_paths.append(candidate)

    has_scontrini = len(scontrini_pairs) > 0
    has_auto_pdf = len(auto_pdf_paths) > 0

    if has_scontrini and has_auto_pdf:
        dossier_message = "Dossier creato correttamente: inclusi PDF trasferte, scontrini e PDF auto."
    elif has_scontrini and not auto_pdf_expected:
        dossier_message = "Dossier creato: inclusi PDF trasferte e scontrini. Nessuna automobile associata alle trasferte del mese."
    elif has_scontrini and not has_auto_pdf:
        dossier_message = "Dossier creato: inclusi PDF trasferte e scontrini. PDF auto mancanti."
    elif (not has_scontrini) and has_auto_pdf:
        dossier_message = "Dossier creato: inclusi PDF trasferte e PDF auto. Scontrini mancanti."
    elif (not has_scontrini) and (not auto_pdf_expected):
        dossier_message = "Dossier creato: incluso solo PDF trasferte. Nessuna automobile associata e scontrini mancanti."
    else:
        dossier_message = "Dossier creato: incluso solo PDF trasferte. Scontrini e PDF auto mancanti."

    out = BytesIO()
    with zipfile.ZipFile(out, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            f"trasferte_{u_id}_{month_start.strftime('%Y_%m')}.pdf",
            pdf_trasferte,
        )

        for file_path, arcname in scontrini_pairs:
            zf.write(file_path, arcname=arcname)

        for auto_pdf_path in auto_pdf_paths:
            zf.write(auto_pdf_path, arcname=f"auto/{auto_pdf_path.name}")

    out.seek(0)
    data_audit = timezone.localdate().isoformat()
    zip_filename = (
        f"dossier_trasferte_{user.nome}_{user.cognome}_"
        f"{month_start.strftime('%Y_%m')}.zip"
    )
    response = FileResponse(out, as_attachment=True, filename=zip_filename)
    response["X-Dossier-Message"] = dossier_message
    response["X-Dossier-Has-Scontrini"] = "1" if has_scontrini else "0"
    response["X-Dossier-Has-Auto-Pdf"] = "1" if has_auto_pdf else "0"
    response["X-Dossier-Auto-Pdf-Expected"] = "1" if auto_pdf_expected else "0"
    response["X-Dossier-Data-Audit"] = data_audit
    response["X-Firma-Status"] = firma_status
    response["Access-Control-Expose-Headers"] = (
        "X-Dossier-Message, X-Dossier-Has-Scontrini, "
        "X-Dossier-Has-Auto-Pdf, X-Dossier-Auto-Pdf-Expected, "
        "X-Dossier-Data-Audit, X-Firma-Status"
    )
    return response



