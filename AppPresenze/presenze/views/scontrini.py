import os
import re
import uuid
import mimetypes
from pathlib import Path
    

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
from django.http import FileResponse
from django.utils import timezone
from ..models import Trasferta, Automobile


SCONTRINI_ROOT: Path = Path(settings.SCONTRINI_ROOT)
SCONTRINI_ROOT.mkdir(parents=True, exist_ok=True)

TPDF_ROOT: Path = Path(settings.PDF_ROOT)
TPDF_ROOT.mkdir(parents=True, exist_ok=True)

def _folder_name(trasferta: Trasferta) -> str:
    """Restituisce il nome cartella nel formato {data}_{t_id}."""
    data = trasferta.data.strftime("%Y-%m-%d")
    return f"{data}_{trasferta.pk}"


def _scontrino_upload_logic(request, t_id: int):
    """
    POST /presenze/api/trasferte/<t_id>/scontrini/
    Carica uno scontrino (.jpeg, .png o .pdf) associato a una trasferta.
    I file vengono salvati in SCONTRINI_ROOT/{data_inizio}_{t_id}/.
    Non è possibile caricare scontrini su trasferte validate dall'admin.
    """
    try:
        trasferta = Trasferta.objects.get(pk=t_id)
    except Trasferta.DoesNotExist:
        return Response(
            {"errors": "Trasferta non trovata."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if trasferta.validation_level == Trasferta.ValidationLevel.VALIDATO_ADMIN:
        return Response(
            {"errors": "Non è possibile caricare scontrini su una trasferta validata dall'admin."},
            status=status.HTTP_403_FORBIDDEN,
        )

    is_super = request.user.is_superuser
    is_owner = trasferta.utente_id == request.user.id

    if not (is_super or is_owner):
        return Response(
            {"errors": "Non hai i permessi per caricare scontrini su questa trasferta."},
            status=status.HTTP_403_FORBIDDEN,
        )

    file_obj = request.FILES.get("file")
    if not file_obj:
        return Response(
            {"errors": "Nessun file fornito. Usa il campo 'file'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "application/pdf"}
    if file_obj.content_type not in ALLOWED_CONTENT_TYPES:
        return Response(
            {"errors": "Formato non supportato. Sono accettati solo .jpeg, .png e .pdf."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    first_letter = request.user.nome[0].upper() if request.user.nome else "X"
    ext = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "application/pdf": "pdf",
    }[file_obj.content_type]
    trasferta_date = trasferta.data.strftime("%Y-%m-%d")
    dest_dir = SCONTRINI_ROOT / _folder_name(trasferta)
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Usa un id univoco nel nome e rigenera solo in caso di collisione reale.
    while True:
        unique_id = uuid.uuid4().hex[:12]
        filename = (
            f"giustificativo_{unique_id}_{first_letter}_{request.user.cognome}_"
            f"{trasferta_date}.{ext}"
        )
        dest_path = dest_dir / filename
        if not dest_path.exists():
            break

    with open(dest_path, "wb") as f:
        for chunk in file_obj.chunks():
            f.write(chunk)

    return Response(
        {
            "message": "Scontrino caricato con successo.",
            "filename": filename,
            "path": str(dest_path),
        },
        status=status.HTTP_201_CREATED,
    )


def _scontrini_list_logic(request, t_id: int):
    """
    GET /presenze/api/trasferte/<t_id>/scontrini/
    Ritorna tutti i file della cartella corrispondente alla trasferta.
    """
    try:
        trasferta = Trasferta.objects.get(pk=t_id)
    except Trasferta.DoesNotExist:
        return Response(
            {"errors": "Trasferta non trovata."},
            status=status.HTTP_404_NOT_FOUND,
        )

    is_super = request.user.is_superuser
    is_owner = trasferta.utente_id == request.user.id

    if not (is_super or is_owner):
        return Response(
            {"errors": "Non hai i permessi per visualizzare gli scontrini di questa trasferta."},
            status=status.HTTP_403_FORBIDDEN,
        )

    folder = SCONTRINI_ROOT / _folder_name(trasferta)

    if not folder.exists():
        return Response([], status=status.HTTP_200_OK)

    files = []
    for entry in sorted(folder.iterdir()):
        if entry.is_file():
            st = entry.stat()
            files.append(
                {
                    "filename": entry.name,
                    "path": str(entry.relative_to(SCONTRINI_ROOT)),
                    "size_bytes": st.st_size,
                    "created_at": st.st_ctime,
                    "modified_at": st.st_mtime,
                }
            )

    return Response(files, status=status.HTTP_200_OK)


def _scontrino_get_or_delete_logic(request, t_id: int, filename: str, delete: bool = False):
    """
    GET/DELETE /presenze/api/trasferte/<t_id>/scontrini/<filename>/
    - GET: restituisce lo scontrino specifico
    - DELETE: elimina lo scontrino specifico
    """
    try:
        trasferta = Trasferta.objects.get(pk=t_id)
    except Trasferta.DoesNotExist:
        return Response(
            {"errors": "Trasferta non trovata."},
            status=status.HTTP_404_NOT_FOUND,
        )

    is_super = request.user.is_superuser
    is_owner = trasferta.utente_id == request.user.id
    if not (is_super or is_owner):
        return Response(
            {"errors": "Non hai i permessi per accedere agli scontrini di questa trasferta."},
            status=status.HTTP_403_FORBIDDEN,
        )
    if delete and trasferta.validation_level == Trasferta.ValidationLevel.VALIDATO_ADMIN:
        return Response(
            {"errors": "Non è possibile eliminare scontrini di una trasferta validata dall'admin."},
            status=status.HTTP_403_FORBIDDEN,
        )

    safe_filename = Path(filename).name
    if not safe_filename or safe_filename != filename:
        return Response(
            {"errors": "Nome file non valido."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    folder = SCONTRINI_ROOT / _folder_name(trasferta)
    file_path = folder / safe_filename
    if not file_path.exists() or not file_path.is_file():
        return Response(
            {"errors": "Scontrino non trovato."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if delete:
        file_path.unlink()
        return Response(
            {"message": "Scontrino eliminato con successo.", "filename": safe_filename},
            status=status.HTTP_200_OK,
        )

    content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    response = FileResponse(open(file_path, "rb"), content_type=content_type)
    response["Content-Disposition"] = f'inline; filename="{safe_filename}"'
    return response


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def scontrini_endpoint(request, t_id: int):
    if request.method == "GET":
        return _scontrini_list_logic(request, t_id)
    return _scontrino_upload_logic(request, t_id)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def scontrino_upload(request, t_id: int):
    return _scontrino_upload_logic(request, t_id)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def scontrini_list(request, t_id: int):
    return _scontrini_list_logic(request, t_id)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def scontrino_get(request, t_id: int, filename: str):
    return _scontrino_get_or_delete_logic(request, t_id, filename, delete=False)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def scontrino_delete(request, t_id: int, filename: str):
    return _scontrino_get_or_delete_logic(request, t_id, filename, delete=True)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def pdf_auto_upload(request, auto_id: int):
    """
    POST /presenze/api/automobili/<auto_id>/PDFauto/
    Carica un PDF associato a un'automobile e lo salva in:
    TPDF_ROOT/<mese_anno>/<auto_id>.pdf

    Campo richiesto:
    - file: PDF

    Campo opzionale:
    - mese_anno: formato MM_YYYY (default: mese corrente)
    """
    try:
        auto = Automobile.objects.get(pk=auto_id)
    except Automobile.DoesNotExist:
        return Response(
            {"errors": "Automobile non trovata."},
            status=status.HTTP_404_NOT_FOUND,
        )

    file_obj = request.FILES.get("file")
    if not file_obj:
        return Response(
            {"errors": "Nessun file fornito. Usa il campo 'file'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    filename = (file_obj.name or "").lower()
    if file_obj.content_type != "application/pdf" and not filename.endswith(".pdf"):
        return Response(
            {"errors": "Formato non supportato. Carica un file PDF."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    mese_anno = (request.data.get("mese_anno") or "").strip()
    if not mese_anno:
        mese_anno = timezone.localdate().strftime("%m_%Y")

    if not re.fullmatch(r"\d{2}_\d{4}", mese_anno):
        return Response(
            {"errors": "Formato mese_anno non valido. Usa MM_YYYY (es. 03_2026)."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    dest_dir = TPDF_ROOT / mese_anno
    dest_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"{auto_id}.pdf"
    dest_path = dest_dir / safe_name

    with open(dest_path, "wb") as f:
        for chunk in file_obj.chunks():
            f.write(chunk)

    return Response(
        {
            "message": "PDF caricato con successo.",
            "filename": safe_name,
            "path": str(dest_path),
            "mese_anno": mese_anno,
            "auto_id": auto_id,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def pdf_auto_delete(request, auto_id: int):
    """
    DELETE /presenze/api/automobili/<auto_id>/PDFauto/delete/
    Elimina il PDF dell'automobile per il mese indicato.

    Parametro opzionale:
    - mese_anno: formato MM_YYYY (default: mese corrente)
    """
    try:
        Automobile.objects.get(pk=auto_id)
    except Automobile.DoesNotExist:
        return Response(
            {"errors": "Automobile non trovata."},
            status=status.HTTP_404_NOT_FOUND,
        )

    mese_anno = (request.data.get("mese_anno") or request.query_params.get("mese_anno") or "").strip()
    if not mese_anno:
        mese_anno = timezone.localdate().strftime("%m_%Y")

    if not re.fullmatch(r"\d{2}_\d{4}", mese_anno):
        return Response(
            {"errors": "Formato mese_anno non valido. Usa MM_YYYY (es. 03_2026)."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    file_path = TPDF_ROOT / mese_anno / f"{auto_id}.pdf"
    if not file_path.exists() or not file_path.is_file():
        return Response(
            {"errors": "PDF non trovato."},
            status=status.HTTP_404_NOT_FOUND,
        )

    file_path.unlink()

    return Response(
        {
            "message": "PDF eliminato con successo.",
            "filename": file_path.name,
            "auto_id": auto_id,
            "mese_anno": mese_anno,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def pdf_auto_current_month_list(request):
    """
    GET /presenze/api/automobili/PDFauto/mese-corrente/
    Ritorna i PDF presenti nella cartella del mese corrente:
    TPDF_ROOT/<MM_YYYY>/

    Tutti gli utenti autenticati vedono tutti i PDF del mese.
    """
    mese_anno = timezone.localdate().strftime("%m_%Y")
    month_dir = TPDF_ROOT / mese_anno

    if not month_dir.exists():
        return Response(
            {
                "mese_anno": mese_anno,
                "files": [],
            },
            status=status.HTTP_200_OK,
        )

    files = []
    for entry in sorted(month_dir.iterdir()):
        if not entry.is_file() or entry.suffix.lower() != ".pdf":
            continue

        auto_id_str = entry.stem
        if not auto_id_str.isdigit():
            continue

        auto_id = int(auto_id_str)

        st = entry.stat()
        files.append(
            {
                "filename": entry.name,
                "auto_id": auto_id,
                "path": str(entry.relative_to(TPDF_ROOT)),
                "size_bytes": st.st_size,
                "created_at": st.st_ctime,
                "modified_at": st.st_mtime,
            }
        )

    return Response(
        {
            "mese_anno": mese_anno,
            "files": files,
        },
        status=status.HTTP_200_OK,
    )

# ══════════════════════════════════════════════════════════════════════════════
#  FUNZIONE DI MIGRAZIONE VERSO SHAREPOINT (non utilizzata)
#  Chiama questa funzione quando avrai configurato Azure AD.
#  Documentazione Graph: https://learn.microsoft.com/graph/api/driveitem-put-content
# ══════════════════════════════════════════════════════════════════════════════

def _migrate_scontrini_to_sharepoint() -> dict:
    """
    Legge tutti i file da SCONTRINI_ROOT e li carica su SharePoint
    mantenendo la struttura di cartelle per trasferta.

    NON è collegata ad alcun endpoint — chiamala manualmente (es. management
    command) quando hai le credenziali Azure pronte.

    Configura le variabili qui sotto prima di usarla.
    """
    import requests  # noqa: PLC0415  (import locale intenzionale — funzione non usata)

    # ── Credenziali SharePoint ─────────────────────────────────────────────
    # SHAREPOINT_SITE_ID  = "contoso.sharepoint.com,abc123,xyz789"
    # SHAREPOINT_DRIVE_ID = "b!abc123..."
    # SHAREPOINT_FOLDER   = "Scontrini"
    # SHAREPOINT_TOKEN    = _get_graph_token()   # vedi commento sotto
    #
    # Per ottenere il token automaticamente con msal:
    #   import msal
    #   def _get_graph_token():
    #       app = msal.ConfidentialClientApplication(
    #           client_id="<client-id>",
    #           client_credential="<client-secret>",
    #           authority="https://login.microsoftonline.com/<tenant-id>",
    #       )
    #       return app.acquire_token_for_client(
    #           scopes=["https://graph.microsoft.com/.default"]
    #       )["access_token"]
    # ──────────────────────────────────────────────────────────────────────

    SHAREPOINT_SITE_ID  = "CAMBIA_ME"
    SHAREPOINT_DRIVE_ID = "CAMBIA_ME"
    SHAREPOINT_FOLDER   = "Scontrini"
    SHAREPOINT_TOKEN    = "CAMBIA_ME"

    headers = {"Authorization": f"Bearer {SHAREPOINT_TOKEN}"}
    results = {"uploaded": [], "failed": []}

    for root, _dirs, filenames in os.walk(SCONTRINI_ROOT):
        for name in filenames:
            local_path = Path(root) / name
            # Mantiene la struttura  Scontrini/<t_id>/<filename>
            relative = local_path.relative_to(SCONTRINI_ROOT)
            remote_path = f"{SHAREPOINT_FOLDER}/{relative}"

            upload_url = (
                f"https://graph.microsoft.com/v1.0"
                f"/sites/{SHAREPOINT_SITE_ID}"
                f"/drives/{SHAREPOINT_DRIVE_ID}"
                f"/items/root:/{remote_path}:/content"
            )

            with open(local_path, "rb") as f:
                resp = requests.put(
                    upload_url,
                    headers={**headers, "Content-Type": "application/octet-stream"},
                    data=f,
                )

            if resp.status_code in (200, 201):
                results["uploaded"].append(str(relative))
            else:
                results["failed"].append(
                    {"file": str(relative), "error": resp.text}
                )

    return results
