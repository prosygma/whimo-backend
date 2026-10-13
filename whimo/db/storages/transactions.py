from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from django.db.models import Count, Exists, OuterRef, Q, QuerySet, Subquery
from django.utils import timezone

from whimo.common.schemas.errors import NotFound
from whimo.common.utils import get_user_model
from whimo.db.enums import TransactionAction, TransactionStatus, TransactionType
from whimo.db.enums.transactions import TransactionTraceability
from whimo.db.models import Transaction
from whimo.transactions.constants import CHAIN_TIER_FIELD
from whimo.transactions.schemas.requests import TransactionListRequest

User = get_user_model()


@dataclass(slots=True)
class TransactionsStorage:
    @staticmethod
    def get_user_transaction_with_relations(user_id: UUID, transaction_id: UUID) -> Transaction:
        try:
            return (
                Transaction.objects.filter(Q(buyer_id=user_id) | Q(seller_id=user_id), pk=transaction_id)
                .select_related("commodity__group", "commodity", "harvest_season", "buyer", "seller")
                .prefetch_related(
                    User.objects.generate_prefetch_gadgets("buyer__"),
                    User.objects.generate_prefetch_gadgets("seller__"),
                )
                .get()
            )
        except Transaction.DoesNotExist as err:
            raise NotFound(errors={"transaction": [transaction_id]}) from err

    @staticmethod
    def get_transaction_with_relations(transaction_id: UUID) -> Transaction:
        return (
            Transaction.objects.select_related("commodity__group", "commodity", "harvest_season", "buyer", "seller")
            .prefetch_related(
                User.objects.generate_prefetch_gadgets("buyer__"),
                User.objects.generate_prefetch_gadgets("seller__"),
            )
            .get(pk=transaction_id)
        )

    @staticmethod
    def select_user_transaction(user_id: UUID, transaction_id: UUID) -> QuerySet[Transaction]:
        query = Transaction.objects.filter(Q(buyer_id=user_id) | Q(seller_id=user_id), pk=transaction_id)
        return cast(QuerySet[Transaction], query)

    @staticmethod
    def get_incoming_transaction(user_id: UUID, transaction_id: UUID, allow_created_by: bool) -> Transaction:
        queryset = (
            Transaction.objects.select_related("commodity", "harvest_season", "buyer", "seller")
            .prefetch_related(
                User.objects.generate_prefetch_gadgets("buyer__"),
                User.objects.generate_prefetch_gadgets("seller__"),
            )
            .filter(
                Q(buyer_id=user_id) | Q(seller_id=user_id),
                Q(expires_at__gte=timezone.now()) | Q(expires_at__isnull=True),
                pk=transaction_id,
                type=TransactionType.DOWNSTREAM,
                status=TransactionStatus.PENDING,
            )
        )

        if not allow_created_by:
            queryset = queryset.exclude(created_by_id=user_id)

        try:
            return queryset.get()
        except Transaction.DoesNotExist as err:
            raise NotFound(errors={"transaction": [transaction_id]}) from err

    @staticmethod
    def get_conversions(group_ids: set[UUID]) -> dict[UUID, list[Transaction]]:
        conversions: dict[UUID, list[Transaction]] = defaultdict(list)
        rows = Transaction.objects.select_related("commodity__group", "commodity", "harvest_season").filter(
            type=TransactionType.CONVERSION,
            group_id__in=group_ids,
        )
        for row in rows:
            conversions[cast(UUID, row.group_id)].append(row)

        return conversions

    @staticmethod
    def get_user_conversion(user_id: UUID, group_id: UUID) -> list[Transaction]:
        conversion = TransactionsStorage.get_conversions({group_id}).get(group_id)
        if not conversion or user_id not in {conversion[0].buyer_id, conversion[0].seller_id}:
            raise NotFound(errors={"conversion": [group_id]})

        return conversion

    @staticmethod
    def filter_transactions(
        user_id: UUID,
        request: TransactionListRequest,
        collapse_conversions: bool = False,
    ) -> QuerySet[Transaction]:
        queryset = Transaction.objects.select_related(
            "commodity__group",
            "commodity",
            "harvest_season",
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

        if request.action == TransactionAction.BUYING:
            _filter &= Q(buyer_id=user_id)

        if request.action == TransactionAction.SELLING:
            _filter &= Q(seller_id=user_id)

        if request.action and request.group_conversions:
            _filter &= ~Q(type=TransactionType.CONVERSION)

        lookups = {
            "type": request.type,
            "status": request.status,
            "created_at__gte": request.created_at_from,
            "created_at__lte": request.created_at_to,
            "commodity__group_id": request.commodity_group_id,
            "commodity_id": request.commodity_id,
            "harvest_season_id": request.harvest_season_id,
            "harvest_season__status": request.harvest_season_status,
        }
        for lookup, value in lookups.items():
            if value:
                _filter &= Q(**{lookup: value})

        if collapse_conversions:
            grouped = Q(type=TransactionType.CONVERSION, group_id__isnull=False)
            matched_groups = Transaction.objects.filter(_filter & grouped).values("group_id")
            heads = (
                Transaction.objects.filter(type=TransactionType.CONVERSION, group_id__in=matched_groups)
                .order_by("group_id", "-volume", "id")
                .distinct("group_id")
                .values("id")
            )
            _filter = (_filter & ~grouped) | Q(pk__in=heads)

        queryset = queryset.filter(_filter)

        if orderings := request.get_orderings():
            queryset = queryset.order_by(*orderings)

        return cast(QuerySet[Transaction], queryset)

    @staticmethod
    def filter_chain_roots(user_id: UUID, request: TransactionListRequest) -> list[Transaction]:
        queryset = TransactionsStorage.filter_transactions(user_id, request)
        return list(queryset.select_related(None).prefetch_related(None))

    @staticmethod
    def get_filtered_chains_farms(user_id: UUID, request: TransactionListRequest) -> list[Transaction]:
        roots = TransactionsStorage.filter_chain_roots(user_id, request)
        return TransactionsStorage.get_chains_farms(roots)

    @staticmethod
    def get_chains_farms(roots: list[Transaction]) -> list[Transaction]:
        chain = TransactionsStorage.get_chains_transactions(roots)
        return [
            transaction
            for transaction in chain
            if transaction.seller_id is None and transaction.type != TransactionType.CONVERSION
        ]

    @staticmethod
    def get_chains_transactions(roots: list[Transaction]) -> list[Transaction]:
        # Every root bounds its own chain at its updated_at, the way a single-root
        # traversal does. A transaction several roots reach keeps the latest of their
        # cutoffs, and is walked again only when a later cutoff opens up more of its
        # own history. One query per depth level, whatever the number of roots.
        collected: dict[UUID, Transaction] = {}
        walked: dict[UUID, datetime] = {}
        frontier = [(root, root.updated_at) for root in roots]
        tier = 0

        while frontier:
            for transaction, cutoff in frontier:
                collected.setdefault(transaction.pk, transaction)
                walked[transaction.pk] = max(cutoff, walked.get(transaction.pk, cutoff))
                # A transaction several chains reach keeps the shortest way to a root.
                reached = collected[transaction.pk]
                setattr(reached, CHAIN_TIER_FIELD, min(tier, getattr(reached, CHAIN_TIER_FIELD, tier)))

            frontier = [
                (transaction, cutoff)
                for transaction, cutoff in TransactionsStorage._chain_predecessors(frontier)
                if transaction.pk not in walked or walked[transaction.pk] < cutoff
            ]
            tier += 1

        return list(collected.values())

    @staticmethod
    def _chain_predecessors(frontier: list[tuple[Transaction, datetime]]) -> list[tuple[Transaction, datetime]]:
        sales: dict[tuple[UUID | None, UUID, UUID], datetime] = {}
        conversions: dict[UUID, datetime] = {}

        for transaction, cutoff in frontier:
            if transaction.seller_id:
                sale = (transaction.seller_id, transaction.commodity_id, transaction.harvest_season_id)
                sales[sale] = max(cutoff, sales.get(sale, cutoff))
            elif transaction.type == TransactionType.CONVERSION and transaction.group_id:
                conversions[transaction.group_id] = max(cutoff, conversions.get(transaction.group_id, cutoff))

        predecessors = []

        if sales:
            # The query is deliberately looser than the keys it serves: it asks for
            # every combination of the sellers, commodities and seasons in one go and
            # the exact triples are matched here, so a level costs one query.
            candidates = Transaction.objects.filter(
                status=TransactionStatus.ACCEPTED,
                buyer_id__in={sale[0] for sale in sales},
                commodity_id__in={sale[1] for sale in sales},
                harvest_season_id__in={sale[2] for sale in sales},
                created_at__lte=max(sales.values()),
            )
            for candidate in candidates:
                purchase = (candidate.buyer_id, candidate.commodity_id, candidate.harvest_season_id)
                purchase_cutoff = sales.get(purchase)
                if purchase_cutoff and candidate.created_at <= purchase_cutoff:
                    predecessors.append((candidate, purchase_cutoff))

        if conversions:
            candidates = Transaction.objects.filter(
                type=TransactionType.CONVERSION,
                buyer_id__isnull=True,
                group_id__in=conversions,
                created_at__lte=max(conversions.values()),
            )
            for candidate in candidates:
                conversion_cutoff = conversions[cast(UUID, candidate.group_id)]
                if candidate.created_at <= conversion_cutoff:
                    predecessors.append((candidate, conversion_cutoff))

        return predecessors

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
    def get_downstream_traceability(
        seller_id: UUID | None,
        commodity_id: UUID,
        harvest_season_id: UUID,
    ) -> TransactionTraceability:
        seller_transactions_traceability = Transaction.objects.filter(
            buyer_id=seller_id,
            status=TransactionStatus.ACCEPTED,
            commodity_id=commodity_id,
            harvest_season_id=harvest_season_id,
        ).values_list("traceability", flat=True)

        if seller_transactions_traceability:
            traceability = [TransactionTraceability(trace) for trace in seller_transactions_traceability if trace]
            return min(traceability)

        return TransactionTraceability.INCOMPLETE

    @staticmethod
    def get_conversion_traceability(
        user_id: UUID,
        input_commodity_ids: list[UUID],
        harvest_season_id: UUID,
    ) -> TransactionTraceability:
        user_transactions = Transaction.objects.filter(
            buyer_id=user_id,
            status=TransactionStatus.ACCEPTED,
            commodity_id__in=input_commodity_ids,
            harvest_season_id=harvest_season_id,
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
        cutoff = Subquery(Transaction.objects.filter(pk=transaction_id).values("updated_at")[:1])
        base_query = Transaction.objects.filter(created_at__lte=cutoff)

        transactions_ids = {transaction_id}
        filters: dict[str, Any] = {}
        visited: set[UUID] = set()

        while transactions_ids:
            filters["pk__in"] = transactions_ids
            transactions_query = base_query.filter(**filters).exclude(pk__in=visited)
            chain_transactions |= transactions_query

            filters["status"] = TransactionStatus.ACCEPTED
            visited |= transactions_ids

            matching_sellers = transactions_query.filter(
                seller_id__isnull=False,
                seller_id=OuterRef("buyer_id"),
                commodity_id=OuterRef("commodity_id"),
                harvest_season_id=OuterRef("harvest_season_id"),
            )
            transactions_ids = set(base_query.filter(Exists(matching_sellers)).values_list("pk", flat=True))

            # Without a group_id there is no way to tell which inputs fed this output:
            # group_id=None would match every ungrouped input of the season, from any user.
            conversion_outputs = transactions_query.filter(
                type=TransactionType.CONVERSION,
                seller_id__isnull=True,
                group_id__isnull=False,
            )

            for conversion_output in conversion_outputs:
                input_transactions = Transaction.objects.filter(
                    type=TransactionType.CONVERSION,
                    buyer_id__isnull=True,
                    group_id=conversion_output.group_id,
                    harvest_season_id=conversion_output.harvest_season_id,
                    created_at__lte=cutoff,
                ).exclude(pk__in=visited)

                chain_transactions |= input_transactions

                transactions_ids |= set(input_transactions.values_list("pk", flat=True))

        return cast(QuerySet[Transaction], chain_transactions)
