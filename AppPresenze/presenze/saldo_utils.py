from decimal import Decimal, InvalidOperation

from django.utils import timezone


ZERO = Decimal("0.00")


def periodo_from_date(value):
    return f"{value.month:02d}-{value.year}"


def decimal_to_json_number(value):
    quantized = Decimal(str(value)).quantize(Decimal("0.01"))
    if quantized == quantized.to_integral_value():
        return int(quantized)
    return float(quantized)


def coerce_saldo_decimal(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return ZERO


def latest_saldo_decimal(records):
    if not records:
        return ZERO
    return coerce_saldo_decimal(records[-1].get("saldo", ZERO))


def upsert_saldo_mensile(saldo_obj, periodo, nuovo_saldo, at=None):
    now = at or timezone.now()
    records = list(saldo_obj.saldo or [])
    existing_index = next(
        (idx for idx, record in enumerate(records) if record.get("periodo") == periodo),
        None,
    )

    if existing_index is None:
        validazioni = 1
    else:
        existing = records.pop(existing_index)
        validazioni = int(existing.get("validazioni") or 1) + 1

    records.append({
        "periodo": periodo,
        "saldo": decimal_to_json_number(nuovo_saldo),
        "aggiornatoIl": now.isoformat(),
        "validazioni": validazioni,
    })
    saldo_obj.saldo = records
    return saldo_obj


def apply_saldo_delta(saldo_obj, periodo, delta, at=None):
    nuovo_saldo = latest_saldo_decimal(list(saldo_obj.saldo or [])) + Decimal(str(delta))
    return upsert_saldo_mensile(saldo_obj, periodo, nuovo_saldo, at=at)
