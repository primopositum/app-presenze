from rest_framework import serializers
import base64

from .models import Utente, TimeEntry, Saldo, Contratto, Cliente, ContrattoCliente, Periodicita, Trasferta, Spesa, Automobile, Signature, UtilitiesBar
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from .saldo_utils import decimal_to_json_number

class UtenteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    saldo = serializers.SerializerMethodField()
    contratti = serializers.SerializerMethodField()

    class Meta:
        model = Utente
        fields = [
            'id',
            'is_superuser',
            'is_staff',
            'email',
            'password',
            'nome',
            'cognome',
            'is_active',
            'dati_anagrafici',
            'data_creaz',
            'data_upd',
            'saldo',
            'contratti'
        ]
        read_only_fields = ['data_creaz', 'data_upd', 'is_superuser', 'is_staff']

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = Utente(**validated_data)
        if password:
            user.set_password(password)   # genera l'hash e lo salva in user.password
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
    
    def get_saldo(self, obj):
        try:
            saldo = obj.saldo  # OneToOne: singolo oggetto
        except ObjectDoesNotExist:
            return None
        return SaldoMiniSerializer(saldo).data
    
    def get_contratti(self, obj):
        qs = obj.contratti.order_by("-data_ass", "-id")
        return ContrattoMiniSerializer(qs, many=True).data

class TimeEntrySerializer(serializers.ModelSerializer):
    utente_id = serializers.IntegerField(write_only=True)
    utente = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = TimeEntry
        fields = [
            "id",
            "utente",
            "utente_id",
            "type",
            "ore_tot",
            "data",
            "note",
            "validation_level",
            "data_creaz",
            "data_upd",
        ]
        read_only_fields = ["id", "utente", "data_creaz", "data_upd"]

    def _get_contract_day_hours(self, utente_id: int, target_date):
        if target_date.weekday() > 4:
            return None

        contract = (
            Contratto.objects
            .filter(utente_id=utente_id, is_active=True, data_ass__lte=target_date)
            .filter(Q(data_fine__isnull=True) | Q(data_fine__gte=target_date))
            .order_by("-data_ass", "-id")
            .first()
        )
        if not contract or not contract.ore_sett or len(contract.ore_sett) != 5:
            return None
        return Decimal(str(contract.ore_sett[target_date.weekday()]))

    def _sync_prelievo_under_contract(self, lavoro_entry: TimeEntry):
        if lavoro_entry.type != TimeEntry.EntryType.LAVORO_ORDINARIO:
            return

        expected_hours = self._get_contract_day_hours(lavoro_entry.utente_id, lavoro_entry.data)
        if expected_hours is None:
            return

        # Lock di TUTTE le TimeEntry dell'utente per quel giorno (in ordine di id
        # per consistenza con altri lock e prevenzione deadlock).
        # Include anche eventuali PRELIEVO/VERSAMENTO esistenti, così nessun altro
        # processo può modificarli mentre ricalcoliamo.
        day_entries = list(
            TimeEntry.objects
            .select_for_update()
            .filter(utente_id=lavoro_entry.utente_id, data=lavoro_entry.data)
            .order_by("id")
        )

        # Calcolo covered_total escludendo banca ore
        covered_total = sum(
            (Decimal(str(te.ore_tot)) for te in day_entries
            if te.type not in (
                TimeEntry.EntryType.PRELIEVO_BANCA_ORE,
                TimeEntry.EntryType.VERSAMENTO_BANCA_ORE,
            )),
            Decimal("0.00"),
        )
        delta = expected_hours - covered_total

        # Cerca prelievo esistente nelle entry già lockate
        prelievo_entry = next(
            (te for te in day_entries
            if te.type == TimeEntry.EntryType.PRELIEVO_BANCA_ORE
            and te.pk != lavoro_entry.pk),
            None,
        )

        if delta > 0:
            if prelievo_entry:
                prelievo_entry.ore_tot = delta
                prelievo_entry.validation_level = lavoro_entry.validation_level
                prelievo_entry.save(update_fields=["ore_tot", "validation_level", "data_upd"])
            else:
                TimeEntry.objects.create(
                    utente_id=lavoro_entry.utente_id,
                    data=lavoro_entry.data,
                    type=TimeEntry.EntryType.PRELIEVO_BANCA_ORE,
                    ore_tot=delta,
                    validation_level=lavoro_entry.validation_level,
                )
        elif prelievo_entry:
            prelievo_entry.delete()

    @transaction.atomic
    def create(self, validated_data):
        utente_id = validated_data.pop("utente_id")
        entry_type = validated_data.get('type')
        ore_tot = validated_data.get('ore_tot')
        target_date = validated_data.get('data')
        expected_hours = self._get_contract_day_hours(utente_id, target_date) if target_date else None
        
        # Se è lavoro ordinario e supera le ore contrattuali del giorno, split automatico
        if (
            entry_type == TimeEntry.EntryType.LAVORO_ORDINARIO
            and expected_hours is not None
            and ore_tot > expected_hours
        ):
            ore_lavoro = expected_hours
            ore_banca = ore_tot - ore_lavoro
            
            # Crea entry lavoro ordinario (max ore contrattuali del giorno)
            validated_data['ore_tot'] = ore_lavoro
            validated_data["utente_id"] = utente_id
            time_entry = super().create(validated_data)
            
            # Crea entry versamento banca ore (ore eccedenti)
            TimeEntry.objects.create(
                utente_id=utente_id,
                data=validated_data['data'],
                type=TimeEntry.EntryType.VERSAMENTO_BANCA_ORE,
                ore_tot=ore_banca,
                validation_level=validated_data.get('validation_level', TimeEntry.ValidationLevel.AUTO)
            )
            self._sync_prelievo_under_contract(time_entry)
            return time_entry
        
        # Comportamento normale
        validated_data["utente_id"] = utente_id
        time_entry = super().create(validated_data)
        self._sync_prelievo_under_contract(time_entry)
        return time_entry

    @transaction.atomic
    def update(self, instance, validated_data):
        validated_data.pop("utente_id", None)

        entry_type = validated_data.get('type', instance.type)
        ore_tot = validated_data.get('ore_tot', instance.ore_tot)
        target_date = validated_data.get('data', instance.data)
        expected_hours = self._get_contract_day_hours(instance.utente_id, target_date)

        if entry_type == TimeEntry.EntryType.LAVORO_ORDINARIO:
            # Lock di tutte le TimeEntry dell'utente per quel giorno
            day_entries = list(
                TimeEntry.objects
                .select_for_update()
                .filter(utente_id=instance.utente_id, data=target_date)
                .order_by("id")
            )

            # Cerca la banca_entry esistente nelle entry lockate (esclusa l'istanza corrente)
            banca_entry = next(
                (te for te in day_entries
                if te.type == TimeEntry.EntryType.VERSAMENTO_BANCA_ORE
                and te.pk != instance.pk),
                None,
            )

            if expected_hours is not None and ore_tot > expected_hours:
                # Split: lavoro al massimo delle ore contrattuali, eccedenza in banca ore
                ore_lavoro = expected_hours
                ore_banca = ore_tot - ore_lavoro

                validated_data['ore_tot'] = ore_lavoro
                instance = super().update(instance, validated_data)

                if banca_entry:
                    banca_entry.ore_tot = ore_banca
                    banca_entry.validation_level = validated_data.get(
                        'validation_level', instance.validation_level
                    )
                    banca_entry.save(update_fields=["ore_tot", "validation_level", "data_upd"])
                else:
                    TimeEntry.objects.create(
                        utente=instance.utente,
                        data=instance.data,
                        type=TimeEntry.EntryType.VERSAMENTO_BANCA_ORE,
                        ore_tot=ore_banca,
                        validation_level=validated_data.get(
                            'validation_level', instance.validation_level
                        ),
                    )
                self._sync_prelievo_under_contract(instance)
                return instance

            # Caso: ore <= contrattuali, eliminiamo eventuale banca_entry residua
            if banca_entry:
                banca_entry.delete()
            instance = super().update(instance, validated_data)
            self._sync_prelievo_under_contract(instance)
            return instance

        # Non è lavoro ordinario: comportamento normale
        return super().update(instance, validated_data)

class TrasfertaSerializer(serializers.ModelSerializer):
    utente_email = serializers.ReadOnlyField(source='utente.email')
    utente_nome = serializers.ReadOnlyField(source='utente.nome')
    utente_cognome = serializers.ReadOnlyField(source='utente.cognome')
    totale_spese = serializers.ReadOnlyField()

    class Meta:
        model = Trasferta
        fields = [
            'id', 'utente', 'utente_email', 'utente_nome', 'utente_cognome', 'automobile',
            'data', 'azienda', 'indirizzo', 'tragitto',
            'data_creaz', 'data_upd', 'note', 'totale_spese', 'validation_level'
        ]
        read_only_fields = ['id', 'data_creaz', 'data_upd', 'validation_level']


class TimeEntryValidationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeEntry
        fields = ["validation_level"]

class SaldoRecordSerializer(serializers.Serializer):
    periodo = serializers.RegexField(regex=r"^(0[1-9]|1[0-2])-\d{4}$")
    saldo = serializers.FloatField()
    aggiornatoIl = serializers.DateTimeField(required=False)
    validazioni = serializers.IntegerField(min_value=1, required=False)


class SaldoMiniSerializer(serializers.ModelSerializer):
    utente_id = serializers.IntegerField(read_only=True)
    saldo = SaldoRecordSerializer(many=True, required=False)

    class Meta:
        model = Saldo
        fields = ("utente_id", "saldo")

    def validate_saldo(self, value):
        periods = [record["periodo"] for record in value]
        if len(periods) != len(set(periods)):
            raise serializers.ValidationError("Ogni periodo deve comparire una sola volta.")
        return value

    def _json_records(self, records):
        result = []
        for record in records:
            next_record = {
                "periodo": record["periodo"],
                "saldo": decimal_to_json_number(record["saldo"]),
                "validazioni": int(record.get("validazioni") or 1),
            }
            aggiornato_il = record.get("aggiornatoIl")
            if aggiornato_il is not None:
                next_record["aggiornatoIl"] = aggiornato_il.isoformat()
            result.append(next_record)
        return result

    def update(self, instance, validated_data):
        if "saldo" in validated_data:
            instance.saldo = self._json_records(validated_data["saldo"])
        instance.save()
        return instance


class SaldoPatchSerializer(serializers.Serializer):
    periodo = serializers.RegexField(regex=r"^(0[1-9]|1[0-2])-\d{4}$")
    saldo = serializers.FloatField()

class ContrattoMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contratto
        # ore_sett è una lista di float
        fields = ("data_ass", "data_fine", "is_active", "tipologia", "ore_sett")

class SpesaSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    trasferta_data = serializers.DateField(source='trasferta.data', read_only=True)
    trasferta_azienda = serializers.CharField(source='trasferta.azienda', read_only=True)

    class Meta:
        model = Spesa
        fields = [
            'id', 'trasferta', 'trasferta_data', 'trasferta_azienda',
            'type', 'type_display', 'importo', 'tragitto', 'data_creaz', 'data_upd'
        ]
        read_only_fields = ['id', 'data_creaz', 'data_upd']

    def validate_importo(self, value):
        if value < 0:
            raise serializers.ValidationError("L'importo non puo essere negativo.")
        return value

    def validate(self, attrs):
        tipo = attrs.get('type', getattr(self.instance, 'type', None))
        tragitto = attrs.get('tragitto', getattr(self.instance, 'tragitto', [])) or []
        tragitto_clean = [str(place).strip() for place in tragitto if str(place).strip()]

        if tipo == Spesa.TrasfertaType.KM:
            if not tragitto_clean:
                raise serializers.ValidationError({'tragitto': 'Per Rimborso km il tragitto e obbligatorio.'})
            attrs['tragitto'] = tragitto_clean
        else:
            attrs['tragitto'] = []

        return attrs

class AutomobileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Automobile
        fields = "__all__"
        read_only_fields = ("id", "data_creaz", "data_upd")


class AutomobilePatchSerializer(serializers.ModelSerializer):
    """Serializer dedicato al PATCH dei campi consentiti su Automobile."""

    class Meta:
        model = Automobile
        fields = ("coefficiente", "is_active")

    def validate_coefficiente(self, value):
        if value < 0:
            raise serializers.ValidationError("Il coefficiente non può essere negativo.")
        return value

class SignatureSerializer(serializers.ModelSerializer):
    preview_data_url = serializers.SerializerMethodField()

    class Meta:
        model = Signature
        fields = [
            "id",
            "mime_type",
            "file_name",
            "preview_data_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "mime_type", "file_name", "preview_data_url", "created_at", "updated_at"]

    def get_preview_data_url(self, obj: Signature):
        if obj.image_data:
            mime = (obj.mime_type or "image/png").strip() or "image/png"
            payload = base64.b64encode(bytes(obj.image_data)).decode("ascii")
            return f"data:{mime};base64,{payload}"
        if obj.svg:
            payload = base64.b64encode(obj.svg.encode("utf-8")).decode("ascii")
            return f"data:image/svg+xml;base64,{payload}"
        return None


class UtilitiesBarSerializer(serializers.ModelSerializer):
    class Meta:
        model = UtilitiesBar
        fields = ["id", "nome", "link", "colore", "icon", "posizione"]
        read_only_fields = ["id", "nome", "link", "colore", "icon", "posizione"]


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = ("id", "nome", "indirizzo", "telefono")
        read_only_fields = ("id",)


class PeriodicitaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Periodicita
        fields = (
            "periodic_value",
            "period_days",
            "first_meeting_date",
            "notification_days",
        )


class ContrattoClienteSerializer(serializers.ModelSerializer):
    current_value = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    client_id = serializers.PrimaryKeyRelatedField(
        source="client",
        queryset=Cliente.objects.all(),
    )
    client = ClienteSerializer(read_only=True)
    periodicity = PeriodicitaSerializer(required=False, allow_null=True)

    class Meta:
        model = ContrattoCliente
        fields = (
            "id",
            "contract_id",
            "client",
            "client_id",
            "value",
            "current_value",
            "pool_task",
            "start_date",
            "end_date",
            "periodicity",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_pool_task(self, value):
        normalized_tasks = []
        for raw_task in value:
            task = raw_task.strip() if isinstance(raw_task, str) else ""
            if not task:
                raise serializers.ValidationError("Ogni task deve essere una stringa non vuota.")
            if task in normalized_tasks:
                raise serializers.ValidationError("La stessa task non puo comparire piu volte.")
            normalized_tasks.append(task)
        return normalized_tasks

    def validate(self, attrs):
        periodicity = attrs.get("periodicity", serializers.empty)
        if periodicity is not serializers.empty and periodicity is not None:
            required_fields = ("periodic_value", "period_days", "first_meeting_date", "notification_days")
            missing_fields = [field for field in required_fields if field not in periodicity]
            if missing_fields:
                raise serializers.ValidationError(
                    {"periodicity": {field: "This field is required when periodicity is supplied." for field in missing_fields}}
                )

        start_date = attrs.get("start_date", self.instance.start_date if self.instance else None)
        end_date = attrs.get("end_date", self.instance.end_date if self.instance else None)
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({"end_date": "End date must be on or after start date."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        periodicity = validated_data.pop("periodicity", None)
        contract = ContrattoCliente.objects.create(**validated_data)
        if periodicity:
            Periodicita.objects.create(contract=contract, **periodicity)
        return contract

    @transaction.atomic
    def update(self, instance, validated_data):
        periodicity = validated_data.pop("periodicity", serializers.empty)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()

        if periodicity is not serializers.empty:
            if periodicity is None:
                Periodicita.objects.filter(contract=instance).delete()
            else:
                Periodicita.objects.update_or_create(contract=instance, defaults=periodicity)
            # select_related("periodicity") ha già messo in cache la relazione inversa:
            # senza svuotarla la risposta restituirebbe la periodicità precedente.
            periodicity_rel = instance._meta.get_field("periodicity")
            if periodicity_rel.is_cached(instance):
                periodicity_rel.delete_cached_value(instance)
        return instance

