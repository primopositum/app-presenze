from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict
import calendar
from datetime import timedelta
from dateutil.relativedelta import relativedelta

from django.conf import settings
from django.http import FileResponse, Http404
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework import status
from rest_framework.response import Response

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, BooleanObject

from .models import TimeEntry, Utente


# --- Config ---
PDF_TEMPLATE_PATH = Path(
    getattr(
        settings,
        "PDF_TEMPLATES_DIR",
        settings.BASE_DIR / "presenze" / "templates",
    )
) / "Presenze.pdf"

ITALIAN_WEEKDAYS = ["lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato", "domenica"]
ITALIAN_MONTHS = [
    "",
    "gennaio",
    "febbraio",
    "marzo",
    "aprile",
    "maggio",
    "giugno",
    "luglio",
    "agosto",
    "settembre",
    "ottobre",
    "novembre",
    "dicembre",
]


@dataclass
class DayData:
    data_label: str = ""
    ore: str = ""
    motivo: str = ""

def expected_hours_for_month(start_date, end_date, ore_sett):
    # ore_sett: [lun, mar, mer, gio, ven] come Decimal
    weekday_to_hours = {
        0: ore_sett[0],
        1: ore_sett[1],
        2: ore_sett[2],
        3: ore_sett[3],
        4: ore_sett[4],
    }

    total = Decimal("0.00")
    d = start_date
    while d <= end_date:
        if d.weekday() in weekday_to_hours:
            total += weekday_to_hours[d.weekday()]
        d += timedelta(days=1)

    return total

def previous_month_range(today=None) -> Tuple[timezone.datetime.date, timezone.datetime.date]:
    """
    Ritorna (start_date, end_date) del mese precedente.
    end_date è l'ultimo giorno del mese scorso.
    """
    if today is None:
        today = timezone.localdate()
    first_this_month = today.replace(day=1)
    last_prev_month = first_this_month - relativedelta(days=1)
    start_prev_month = last_prev_month.replace(day=1)
    return start_prev_month, last_prev_month


def month_range_from_date(value: timezone.datetime.date) -> Tuple[timezone.datetime.date, timezone.datetime.date]:
    first_day = value.replace(day=1)
    last_day = value.replace(day=calendar.monthrange(value.year, value.month)[1])
    return first_day, last_day


def format_date_label(d: timezone.datetime.date) -> str:
    return f"{ITALIAN_WEEKDAYS[d.weekday()]} {d.day} {ITALIAN_MONTHS[d.month]} {d.year}"


def build_days_data(entries: List[TimeEntry], start_date, end_date) -> Tuple[Dict[int, DayData], Decimal]:
    """
    Aggrega le TimeEntry per giorno (1..31) del mese e costruisce
    i valori da scrivere nelle 3 colonne:
      - data_label: "nome giorno settimana" + giorno + mese + anno
      - ore: somma delle ore per type 1 e 4
      - motivo: tipi non ordinari (esclude 1,3,4)
    Ritorna anche il totale interno (somma di tutte le entry tranne type 3).
    """
    by_day = defaultdict(list)
    for te in entries:
        by_day[te.data.day].append(te)

    days_in_month = calendar.monthrange(start_date.year, start_date.month)[1]

    out: Dict[int, DayData] = {}
    internal_total = Decimal("0.00")

    for day in range(1, 32):
        if day > days_in_month:
            out[day] = DayData("", "", "")
            continue

        day_date = start_date.replace(day=day)
        label = format_date_label(day_date)

        day_entries = by_day.get(day, [])
        if not day_entries:
            out[day] = DayData(label, "", "")
            continue

        total_hours_display = sum(
            (Decimal(te.ore_tot) for te in day_entries if te.type in (TimeEntry.EntryType.LAVORO_ORDINARIO, TimeEntry.EntryType.PRELIEVO_BANCA_ORE)),
            Decimal("0.00"),
        )
        total_hours_internal = sum(
            (Decimal(te.ore_tot) for te in day_entries if te.type != TimeEntry.EntryType.VERSAMENTO_BANCA_ORE),
            Decimal("0.00"),
        )
        internal_total += total_hours_internal

        reasons = [
            te.get_type_display()
            for te in day_entries
            if te.type not in (
                TimeEntry.EntryType.LAVORO_ORDINARIO,
                TimeEntry.EntryType.VERSAMENTO_BANCA_ORE,
                TimeEntry.EntryType.PRELIEVO_BANCA_ORE,
            )
        ]
        motivo = ", ".join(reasons)

        out[day] = DayData(
            data_label=label,
            ore=f"{total_hours_display:.2f}" if total_hours_display > 0 else "",
            motivo=motivo,
        )

    return out, internal_total


def fill_pdf(template_path: Path, full_name: str, days_data: Dict[int, DayData]) -> BytesIO:
    if not template_path.exists():
        raise Http404(f"Template PDF non trovato: {template_path}")

    reader = PdfReader(str(template_path))
    writer = PdfWriter()
    
    # Clona il documento mantenendo la struttura del form
    writer.clone_reader_document_root(reader)

    # Verifica presenza AcroForm
    if "/AcroForm" not in writer._root_object:
        raise ValidationError({"detail": "Template PDF senza campi modulo (AcroForm)."})

    # Costruisci field_values con i nomi corretti dei campi
    field_values: Dict[str, str] = {"NomeCompleto": full_name or ""}

    for day in range(1, 32):
        dd = days_data.get(day, DayData())
        # Usa i nomi corretti: data1-31, ore1-31, mot1-31
        field_values[f"PresenzeRow{day}"] = dd.data_label
        field_values[f"Ore in busta pagaRow{day}"] = dd.ore
        field_values[f"Motivo assenzaRow{day}"] = dd.motivo

    # Metodo diretto: aggiorna campo per campo
    if "/AcroForm" in writer._root_object and "/Fields" in writer._root_object["/AcroForm"]:
        fields = writer._root_object["/AcroForm"]["/Fields"]
        
        # Log dei primi 10 campi per debugging
        actual_field_names = []
        for i, field_ref in enumerate(fields[:10]):
            field_obj = field_ref.get_object()
            field_name = field_obj.get("/T")
            actual_field_names.append(str(field_name))
        
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Primi 10 campi del PDF: {actual_field_names}")
        logger.debug(f"Primi 10 campi attesi: {list(field_values.keys())[:10]}")
        
        for field_ref in fields:
            field_obj = field_ref.get_object()
            field_name = field_obj.get("/T")
            
            if field_name and field_name in field_values:
                value = field_values[field_name]
                if value:  # Solo se c'è un valore
                    from pypdf.generic import TextStringObject
                    field_obj.update({
                        NameObject("/V"): TextStringObject(value)
                    })
 
    # Imposta NeedAppearances per forzare il rendering dei campi
    if "/AcroForm" in writer._root_object:
        writer._root_object["/AcroForm"].update(
            {NameObject("/NeedAppearances"): BooleanObject(True)}
        )

    out = BytesIO()
    writer.write(out)
    out.seek(0)
    return out


class PresenzeMeseScorsoPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data_str = request.query_params.get("data")
        utente_id_param = request.query_params.get("u_id")

        if not data_str:
            return Response(
                {"errors": "Parametro 'data' obbligatorio (YYYY-MM-DD)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            data_date = date.fromisoformat(data_str)
        except ValueError:
            return Response(
                {"errors": "Parametro 'data' non valido. Usa il formato YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        utente_id = None
        if utente_id_param:
            try:
                utente_id = int(utente_id_param)
            except (TypeError, ValueError):
                return Response(
                    {"errors": "Parametro 'u_id' non valido."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        is_super = request.user.is_superuser
        is_owner = utente_id is not None and request.user.id == utente_id

        if utente_id is not None and not (is_super or is_owner):
            return Response(
                {"errors": "Non hai i permessi per questo utente."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if utente_id is None:
            user = request.user
        else:
            try:
                user = Utente.objects.get(pk=utente_id)
            except Utente.DoesNotExist:
                return Response(
                    {"errors": "Utente non trovato."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        start_date, end_date = month_range_from_date(data_date)

        # Prendi le TimeEntry del mese per questo utente
        entries = list(
            TimeEntry.objects.filter(
                utente_id=user.id,
                data__range=(start_date, end_date),
            ).order_by("data", "type")
        )

        # Aggrega valori
        days_data, total_hours_internal = build_days_data(entries, start_date, end_date)

        contratto = user.contratti.filter(is_active=True).first()
        if contratto and contratto.ore_sett:
            expected_hours = expected_hours_for_month(
        start_date=start_date,
        end_date=end_date,
        ore_sett=[Decimal(x) for x in contratto.ore_sett],
    )
            if total_hours_internal.quantize(Decimal("0.01")) != expected_hours.quantize(Decimal("0.01")):
                raise ValidationError(
                    {"detail": f"Ore inserite ({total_hours_internal:.2f}) non coerenti con il contratto ({expected_hours:.2f})."}
                )

        nome = getattr(user, "nome", "") or ""
        cognome = getattr(user, "cognome", "") or ""
        full_name = f"{nome} {cognome}".strip() or getattr(user, "email", "")

        pdf_io = fill_pdf(PDF_TEMPLATE_PATH, full_name, days_data)

        filename = f"presenze_{user.nome}_{user.cognome}_{start_date.strftime('%Y_%m')}.pdf"
        return FileResponse(pdf_io, as_attachment=True, filename=filename)
