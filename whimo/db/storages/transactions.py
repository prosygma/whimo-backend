from collections import defaultdict
from dataclasses import dataclass
from typing import Any, cast
from uuid import UUID

from django.db.models import Count, Q, QuerySet
from django.utils import timezone

from whimo.common.schemas.errors import NotFound
from whimo.common.utils import get_user_model
from whimo.db.enums import TransactionAction, TransactionStatus, TransactionType
from whimo.db.enums.transactions import TransactionTraceability
from whimo.db.models import Transaction
from whimo.transactions.schemas.requests import TransactionListRequest

User = get_user_model()


@dataclass(slots=True)
class TransactionsStorage:
    @staticmethod
    def get_user_transaction_with_relations(user_id: UUID, transaction_id: UUID) -> Transaction:
        try:
            return (
                Transaction.objects.filter(Q(buyer_id=user_id) | Q(seller_id=user_id), pk=transaction_id)
                .select_related("commodity__group", "commodity", "buyer", "seller")
                .prefetch_related(
                    User.objects.generate_prefetch_gadgets("buyer__"),
                    User.objects.generate_prefetch_gadgets("seller__"),
                )
                .get()
            )
        except Transaction.DoesNotExist as err:
            raise NotFound(errors={"transaction": [transaction_id]}) from err

    @staticmethod
    def select_user_transaction(user_id: UUID, transaction_id: UUID) -> QuerySet[Transaction]:
        query = Transaction.objects.filter(Q(buyer_id=user_id) | Q(seller_id=user_id), pk=transaction_id)
        return cast(QuerySet[Transaction], query)

    @staticmethod
    def get_incoming_transaction(user_id: UUID, transaction_id: UUID, allow_created_by: bool) -> Transaction:
        queryset = Transaction.objects.select_related("commodity").filter(
            Q(buyer_id=user_id) | Q(seller_id=user_id),
            Q(expires_at__gte=timezone.now()) | Q(expires_at__isnull=True),
            pk=transaction_id,
            type=TransactionType.DOWNSTREAM,
            status=TransactionStatus.PENDING,
        )

        if not allow_created_by:
            queryset = queryset.exclude(created_by_id=user_id)

        try:
            return queryset.get()
        except Transaction.DoesNotExist as err:
            raise NotFound(errors={"transaction": [transaction_id]}) from err

    @staticmethod
    def filter_transactions(user_id: UUID, request: TransactionListRequest) -> QuerySet[Transaction]:
        queryset = Transaction.objects.select_related(
            "commodity__group",
            "commodity",
            "buyer",
            "seller",
        ).prefetch_related(
            User.objects.generate_prefetch_gadgets("buyer__"),
            User.objects.generate_prefetch_gadgets("seller__"),
        )

        _filter = Q(buyer_id=request.buyer_id) if request.buyer_id else Q(buyer_id=user_id) | Q(seller_id=user_id)

        if search := request.search:
            _filter &= (
                Q(commodity__name__icontains=search)
                | Q(commodity__code__icontains=search)
                | Q(commodity__name_variants__icontains=search)
            )

        if status := request.status:
            _filter &= Q(status=status)

        if request.action == TransactionAction.BUYING:
            _filter &= Q(buyer_id=user_id)

        if request.action == TransactionAction.SELLING:
            _filter &= Q(seller_id=user_id)

        if created_at_from := request.created_at_from:
            _filter &= Q(created_at__gte=created_at_from)

        if created_at_to := request.created_at_to:
            _filter &= Q(created_at__lte=created_at_to)

        if commodity_group_id := request.commodity_group_id:
            _filter &= Q(commodity__group_id=commodity_group_id)

        if commodity_id := request.commodity_id:
            _filter &= Q(commodity_id=commodity_id)

        queryset = queryset.filter(_filter)

        if orderings := request.get_orderings():
            queryset = queryset.order_by(*orderings)

        return cast(QuerySet[Transaction], queryset)

    @staticmethod
    def get_traceability_counts(transaction_id: UUID) -> dict[TransactionTraceability, int]:
        chain_transactions = TransactionsStorage.get_chain_transactions(transaction_id)

        counts = {TransactionTraceability(traceability): 0 for traceability in TransactionTraceability}
        counts_query = chain_transactions.values("traceability").annotate(count=Count("id"))
        for item in counts_query:
            if traceability := item["traceability"]:
                counts[TransactionTraceability(traceability)] += item["count"]

        return counts

    @staticmethod
    def get_first_chain_transactions(transaction_id: UUID) -> QuerySet[Transaction]:
        chain_transactions = TransactionsStorage.get_chain_transactions(transaction_id)
        first_transactions = chain_transactions.filter(seller_id__isnull=True).exclude(type=TransactionType.CONVERSION)

        return cast(QuerySet[Transaction], first_transactions)

    @staticmethod
    def get_downstream_traceability(seller_id: UUID | None, commodity_id: UUID) -> TransactionTraceability:
        seller_transactions_traceability = Transaction.objects.filter(
            buyer_id=seller_id,
            status=TransactionStatus.ACCEPTED,
            commodity_id=commodity_id,
        ).values_list("traceability", flat=True)

        if seller_transactions_traceability:
            traceability = [TransactionTraceability(trace) for trace in seller_transactions_traceability if trace]
            return min(traceability)

        return TransactionTraceability.INCOMPLETE

    @staticmethod
    def get_conversion_traceability(user_id: UUID, input_commodity_ids: list[UUID]) -> TransactionTraceability:
        user_transactions = Transaction.objects.filter(
            buyer_id=user_id,
            status=TransactionStatus.ACCEPTED,
            commodity_id__in=input_commodity_ids,
            traceability__isnull=False,
        ).values_list("commodity_id", "traceability")

        commodity_traceabilities_map: dict[UUID, list[TransactionTraceability]] = defaultdict(list)
        for commodity_id, traceability in user_transactions:
            if traceability is None:
                continue
            commodity_traceabilities_map[commodity_id].append(TransactionTraceability(traceability))

        min_traceabilities = []
        for commodity_id in input_commodity_ids:
            if traceabilities := commodity_traceabilities_map[commodity_id]:
                min_traceabilities.append(min(traceabilities))

        return min(min_traceabilities) if min_traceabilities else TransactionTraceability.INCOMPLETE

    @staticmethod
    def get_chain_transactions(transaction_id: UUID) -> QuerySet[Transaction]:
        chain_transactions = Transaction.objects.none()
        base_query = Transaction.objects.all()

        transactions_ids = {transaction_id}
        filters: dict[str, Any] = {}
        visited: set[UUID] = set()

        while transactions_ids:
            filters["pk__in"] = transactions_ids
            transactions_query = base_query.filter(**filters).exclude(pk__in=visited)
            chain_transactions |= transactions_query

            filters["status"] = TransactionStatus.ACCEPTED
            visited |= transactions_ids

            sellers_ids = transactions_query.filter(seller_id__isnull=False).values_list("seller_id", flat=True)
            transactions_ids = set(base_query.filter(buyer_id__in=sellers_ids).values_list("pk", flat=True))

            conversion_outputs = transactions_query.filter(
                type=TransactionType.CONVERSION,
                seller_id__isnull=True,
            )

            for conversion_output in conversion_outputs:
                input_transactions = Transaction.objects.filter(
                    type=TransactionType.CONVERSION,
                    buyer_id__isnull=True,
                    group_id=conversion_output.group_id,
                ).exclude(pk__in=visited)

                chain_transactions |= input_transactions

                transactions_ids |= set(input_transactions.values_list("pk", flat=True))

        return cast(QuerySet[Transaction], chain_transactions)
