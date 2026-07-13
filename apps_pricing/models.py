from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import CheckConstraint, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models import LogManager, LogModel, LogQuerySet


class PriceHistoryQuerySet(LogQuerySet):  # NEW
    """
    Наследует LogQuerySet — сохраняет защиту от bulk update/delete логов
    (core.models), добавляет одну удобную выборку поверх неё.
    """

    def effective_on(self, target_date, *, listing=None, room=None):
        """
        Формализует правило "какая цена реально действует на дату X":
        максимальный valid_from <= target_date, а при нескольких записях с
        одинаковым valid_from (например, будущую цену поправили до того, как
        она вступила в силу) — самая свежая по created_at. created_at — это
        DateTimeField(auto_now_add=True) из LogModel, на MySQL Django хранит
        его как datetime(6) — с точностью до микросекунды, так что "какая
        запись внесена позже" определяется однозначно даже при почти
        одновременной записи.

        Без этого метода правило было бы неявным следствием Meta.ordering,
        которое пришлось бы держать в голове в каждом месте, где нужна
        "цена на дату X" (крон, будущий расчёт Booking.total_price, API).
        """
        qs = self.filter(valid_from__lte=target_date)
        if listing is not None:
            qs = qs.filter(listing=listing)
        if room is not None:
            qs = qs.filter(room=room)
        # Meta.ordering = ["-valid_from", "-created_at"] уже задаёт этот
        # порядок по умолчанию, order_by() здесь — не решает лишний раз
        # положиться на Meta и не сломаться, если ordering когда-то поменяют.
        return qs.order_by("-valid_from", "-created_at")


class PriceHistoryManager(LogManager):  # NEW
    def get_queryset(self) -> PriceHistoryQuerySet:
        return PriceHistoryQuerySet(self.model, using=self._db)


class PriceHistory(LogModel):
    """
    Append-only лог цен. CHANGED: раньше save() удалял предыдущую запись на
    ту же дату перед вставкой новой ("перезапись") — это прямо противоречит
    ТЗ ("запись только append-only, удаление запрещено") и физически
    конфликтует с core.LogQuerySet.delete(), которая теперь всегда бросает
    ValidationError на bulk-delete логов. Здесь больше нет удаления вообще:
    для одной valid_from может существовать несколько строк (например,
    арендодатель поправил ошибочно введённую будущую цену до того, как она
    вступила в силу) — актуальной всегда считается самая свежая по
    created_at среди них. Meta.ordering ниже уже отдаёт записи в этом порядке,
    а PriceHistoryQuerySet.effective_on() выше формализует само правило.
    """

    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.CASCADE, null=True, blank=True
    )
    room = models.ForeignKey(
        "listings.Room", on_delete=models.CASCADE, null=True, blank=True
    )

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],  # NEW
        verbose_name=_("Price"),
    )
    currency = models.CharField(max_length=3, default="EUR")
    # CHANGED: было effective_date — переименовано под точное имя из ТЗ.
    valid_from = models.DateField(default=timezone.now, verbose_name=_("Valid from"))

    # NEW: отсутствовал целиком. По ТЗ — арендодатель вручную либо системный
    # пользователь при автоустановке кроном; поле обязательное (не nullable),
    # в отличие от cancelled_by/resolved_by в других приложениях — там сама
    # ТЗ явно помечает их nullable, здесь — нет.
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="price_changes",
        verbose_name=_("Changed by"),
    )

    objects = (
        PriceHistoryManager()
    )  # NEW: даёт .effective_on(), сохраняя защиты LogQuerySet

    class Meta:
        # CHANGED: unique_together убран целиком — в MySQL NULL не считается
        # равным NULL в уникальном индексе, так что для room=NULL (все
        # listing-записи) он всё равно не защищал от дублей — ложное чувство
        # защиты. С переходом на append-only (см. докстринг класса) дубли на
        # одну дату — это не ошибка, а легитимная история правок.
        ordering = ["-valid_from", "-created_at"]
        indexes = [
            models.Index(fields=["valid_from"], name="idx_price_date"),
            models.Index(
                fields=["listing", "valid_from"], name="idx_listing_price_date"
            ),
            models.Index(fields=["room", "valid_from"], name="idx_room_price_date"),
        ]
        constraints = [
            CheckConstraint(
                condition=Q(listing__isnull=False, room__isnull=True)
                | Q(listing__isnull=True, room__isnull=False),
                name="price_history_xor_listing_or_room",
            )
        ]

    def clean(self):
        # XOR validation for admin panel
        if (self.listing and self.room) or (not self.listing and not self.room):
            raise ValidationError(
                _("The price must be linked either to the listing or to the room.")
            )

        today = timezone.now().date()

        if self.valid_from < today:
            raise ValidationError(
                {"valid_from": _("You cannot set prices for past dates.")}
            )

        # NEW: "нельзя сегодня на сегодня, кроме самой первой цены при
        # создании объявления" — раньше проверялось только строгое прошлое,
        # valid_from == today разрешался всегда, что противоречит ТЗ.
        is_first_price = not PriceHistory.objects.filter(
            listing=self.listing, room=self.room
        ).exists()
        if self.valid_from == today and not is_first_price:
            raise ValidationError(
                {
                    "valid_from": _(
                        "Cannot set a price effective today, except for the very "
                        "first price when the listing is created."
                    )
                }
            )

    def save(self, *args, **kwargs):
        # CHANGED: раньше здесь был .filter(...).delete() — см. докстринг
        # класса. Теперь просто append, ничего не удаляется и не переписывается.
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        target = self.listing_id or self.room_id
        return f"{target}: {self.price} {self.currency} from {self.valid_from}"
