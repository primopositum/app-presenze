class PeriodicitaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Periodicita
        fields = ["valore_periodico", "periodo", "data_primo_incontro", "periodo_notifica"]

class ContrattoSerializer(serializers.ModelSerializer):
    periodicita = PeriodicitaSerializer(required=False, allow_null=True)

    class Meta:
        model = Contratto
        fields = ["id", "data_inizio", "data_fine", "value", "periodicita", "pool_task", "cliente", "created_at", "updated_at, "]

    def create(self, validated_data):
        periodicita = validated_data.pop("periodicita", None)
        contratto = Contratto.objects.create(**validated_data)
        if periodicita:
            Periodicita.objects.create(contratto=contratto, **periodicita)
        return contratto

    def update(self, instance, validated_data):
        periodicita = validated_data.pop("periodicita", serializers.empty)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()

        if periodicita is not serializers.empty:
            if periodicita is None:
                Periodicita.objects.filter(contratto=instance).delete()
            else:
                Periodicita.objects.update_or_create(contratto=instance, defaults=periodicita)
        return instance



from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class TimeStampedModel(models.Model):
    """Base astratta: nessuna tabella, solo i due campi di audit."""

    created_at = models.DateTimeField(_("creato il"), auto_now_add=True)
    updated_at = models.DateTimeField(_("aggiornato il"), auto_now=True)

    class Meta:
        abstract = True


class Contratto(TimeStampedModel):
    data_inizio = models.DateField(_("data inizio"))
    data_fine = models.DateField(_("data fine"), null=True, blank=True)
    valore = models.DecimalField(
        _("valore"),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text=_("Valore complessivo del contratto, come firmato."),
    )

    class Meta:
        verbose_name = _("contratto")
        verbose_name_plural = _("contratti")
        ordering = ("-data_inizio", "-id")
        constraints = [
            models.CheckConstraint(
                name="contratto_date_coerenti",
                check=(
                    models.Q(data_fine__isnull=True)
                    | models.Q(data_fine__gte=models.F("data_inizio"))
                ),
            ),
            models.CheckConstraint(
                name="contratto_valore_positivo",
                check=models.Q(valore__gt=0),
            ),
        ]
        indexes = [
            models.Index(fields=("data_inizio",), name="contratto_data_inizio_idx"),
        ]

    def __str__(self):
        return f"Contratto #{self.pk} dal {self.data_inizio:%d/%m/%Y}"

    @property
    def is_periodico(self) -> bool:
        """Attenzione: costa una query se il queryset non ha select_related('periodicita')."""
        return hasattr(self, "periodicita")


class Periodicita(TimeStampedModel):
    contratto = models.OneToOneField(
        Contratto,
        on_delete=models.CASCADE,
        related_name="periodicita",
        verbose_name=_("contratto"),
        primary_key=True,
    )
    valore_periodico = models.DecimalField(
        _("valore periodico"),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    periodo = models.PositiveIntegerField(
        _("periodo"),
        validators=[MinValueValidator(1)],
        help_text=_("Durata del periodo in giorni (es. 30 = mensile, 365 = annuale)."),
    )
    periodo_notifica = models.PositiveIntegerField(
        _("periodo notifica"),
        validators=[MinValueValidator(1)],
        help_text=_("Giorni di preavviso per la notifica (es. 7 = settimanale, 30 = mensile)."),
    )
    data_primo_incontro = models.DateField(_("data primo incontro"))

    class Meta:
        verbose_name = _("periodicità")
        verbose_name_plural = _("periodicità")
        constraints = [
            models.CheckConstraint(
                name="periodicita_valore_positivo",
                check=models.Q(valore_periodico__gt=0),
            ),
            models.CheckConstraint(
                name="periodicita_periodo_positivo",
                check=models.Q(periodo__gte=1),
            ),
            models.CheckConstraint(
                name="periodicita_periodo_notifica_positivo",
                check=models.Q(periodo_notifica__gte=1),
            ),
        ]

    def __str__(self):
        return f"{self.periodo_label} — {self.valore_periodico} €"

    @property
    def periodo_label(self) -> str:
        return str(self.ETICHETTE_NOTE.get(self.periodo, _("ogni %(n)d giorni") % {"n": self.periodo}))