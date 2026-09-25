from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import filters, permissions, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .activity import complaint_snapshot, copper_pair_snapshot, customer_snapshot, dsl_service_snapshot, log_activity
from .filters import ActivityLogFilter, ComplaintFilter, CustomerFilter
from .models import ActivityLog, Complaint, CopperPair, Customer, DSLService, Exchange, MSAG, City, Region
from .serializers import (
    ActivityLogSerializer,
    CitySerializer,
    ComplaintSerializer,
    CopperPairSerializer,
    CustomerDetailSerializer,
    CustomerListSerializer,
    CustomerWriteSerializer,
    DSLServiceSerializer,
    ExchangeSerializer,
    MSAGSerializer,
    RegionSerializer,
)


def _actor(request):
    return request.user if request.user.is_authenticated else None


class RegionViewSet(viewsets.ModelViewSet):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    permission_classes = [permissions.IsAuthenticated]


class CityViewSet(viewsets.ModelViewSet):
    queryset = City.objects.select_related("region").all()
    serializer_class = CitySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["region"]


class ExchangeViewSet(viewsets.ModelViewSet):
    queryset = Exchange.objects.select_related("city", "city__region").all()
    serializer_class = ExchangeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["city"]


class MSAGViewSet(viewsets.ModelViewSet):
    queryset = MSAG.objects.select_related("exchange").all()
    serializer_class = MSAGSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["exchange"]


class CustomerViewSet(viewsets.ModelViewSet):
    """
    Primary endpoint for the field technician UI.

    - list: lean fields + filters (?region=&city=&status=&phone=&user_id=&msag=&pair_number=)
      plus free-text `?search=` across name/phone/address/user_id.
    - retrieve: full nested record (customer + dsl_service + copper_pair).
    - create/update: customer fields only; DSL/copper-pair are separate nested endpoints
      so a technician can update pair condition without touching customer contact info.
    - history: GET /api/customers/<id>/history/ — that customer's full audit trail
      (customer profile changes + its DSL service + its copper pair, newest first).

    Every create/update/delete writes an ActivityLog row (see .activity) so the
    full change history is available for the History tab and the reporting feed.
    """

    queryset = Customer.objects.select_related(
        "city", "city__region", "dsl_service", "dsl_service__msag", "dsl_service__copper_pair"
    ).annotate(
        open_complaint_count=Count(
            "complaints", filter=Q(complaints__status__in=[Complaint.Status.OPEN, Complaint.Status.IN_PROGRESS])
        )
    ).all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CustomerFilter
    search_fields = ["name", "phone_primary", "phone_secondary", "address_line", "user_id", "department"]
    # DRF's OrderingFilter maps the `?ordering=` query value directly to a
    # queryset field/lookup path — these are the fields a technician can
    # sort the customer list by (dsl_service__msag__code / __msag_port let
    # sorting group by MSAG cabinet, and within it by port number).
    ordering_fields = [
        "name", "created_at", "updated_at",
        "dsl_service__msag__code", "dsl_service__msag_port",
    ]
    ordering = ["name"]

    def get_serializer_class(self):
        if self.action == "list":
            return CustomerListSerializer
        if self.action in ("create", "update", "partial_update"):
            return CustomerWriteSerializer
        return CustomerDetailSerializer

    def perform_create(self, serializer):
        instance = serializer.save(created_by=_actor(self.request))
        log_activity(
            customer=instance, entity_type=ActivityLog.EntityType.CUSTOMER, entity_id=instance.id,
            action=ActivityLog.Action.CREATED, actor=_actor(self.request),
            new_data=customer_snapshot(instance),
        )

    def perform_update(self, serializer):
        old_data = customer_snapshot(serializer.instance)
        instance = serializer.save()
        log_activity(
            customer=instance, entity_type=ActivityLog.EntityType.CUSTOMER, entity_id=instance.id,
            action=ActivityLog.Action.UPDATED, actor=_actor(self.request),
            old_data=old_data, new_data=customer_snapshot(instance),
        )

    def perform_destroy(self, instance):
        log_activity(
            customer=instance, entity_type=ActivityLog.EntityType.CUSTOMER, entity_id=instance.id,
            action=ActivityLog.Action.DELETED, actor=_actor(self.request),
            old_data=customer_snapshot(instance), instance_label=instance.name,
        )
        instance.delete()

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        customer = self.get_object()
        logs = ActivityLog.objects.filter(customer=customer).select_related("actor")
        page = self.paginate_queryset(logs)
        serializer = ActivityLogSerializer(page if page is not None else logs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class DSLServiceViewSet(viewsets.ModelViewSet):
    queryset = DSLService.objects.select_related("customer", "msag", "copper_pair").all()
    serializer_class = DSLServiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["customer", "status", "msag"]

    def perform_create(self, serializer):
        instance = serializer.save()
        log_activity(
            customer=instance.customer, entity_type=ActivityLog.EntityType.DSL_SERVICE, entity_id=instance.id,
            action=ActivityLog.Action.CREATED, actor=_actor(self.request),
            new_data=dsl_service_snapshot(instance),
        )

    def perform_update(self, serializer):
        old_data = dsl_service_snapshot(serializer.instance)
        instance = serializer.save()
        log_activity(
            customer=instance.customer, entity_type=ActivityLog.EntityType.DSL_SERVICE, entity_id=instance.id,
            action=ActivityLog.Action.UPDATED, actor=_actor(self.request),
            old_data=old_data, new_data=dsl_service_snapshot(instance),
        )

    def perform_destroy(self, instance):
        log_activity(
            customer=instance.customer, entity_type=ActivityLog.EntityType.DSL_SERVICE, entity_id=instance.id,
            action=ActivityLog.Action.DELETED, actor=_actor(self.request),
            old_data=dsl_service_snapshot(instance),
        )
        instance.delete()


class CopperPairViewSet(viewsets.ModelViewSet):
    queryset = CopperPair.objects.select_related("dsl_service", "dsl_service__customer").all()
    serializer_class = CopperPairSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["dsl_service", "condition"]

    def perform_create(self, serializer):
        instance = serializer.save()
        log_activity(
            customer=instance.dsl_service.customer, entity_type=ActivityLog.EntityType.COPPER_PAIR,
            entity_id=instance.id, action=ActivityLog.Action.CREATED, actor=_actor(self.request),
            new_data=copper_pair_snapshot(instance),
        )

    def perform_update(self, serializer):
        old_data = copper_pair_snapshot(serializer.instance)
        instance = serializer.save()
        log_activity(
            customer=instance.dsl_service.customer, entity_type=ActivityLog.EntityType.COPPER_PAIR,
            entity_id=instance.id, action=ActivityLog.Action.UPDATED, actor=_actor(self.request),
            old_data=old_data, new_data=copper_pair_snapshot(instance),
        )

    def perform_destroy(self, instance):
        log_activity(
            customer=instance.dsl_service.customer, entity_type=ActivityLog.EntityType.COPPER_PAIR,
            entity_id=instance.id, action=ActivityLog.Action.DELETED, actor=_actor(self.request),
            old_data=copper_pair_snapshot(instance),
        )
        instance.delete()


class ComplaintViewSet(viewsets.ModelViewSet):
    """
    Fault/complaint history for customers. Kept as its own lean endpoint
    (rather than nested under DSLService) since a complaint can be filed
    even when the underlying DSL/pair records haven't changed — it's the
    "something was reported wrong" record, tracked as a first-class entity
    so its own status changes get the same field-level audit trail as
    everything else (see ActivityLog, entity_type=COMPLAINT).
    """
    queryset = Complaint.objects.select_related("customer").all()
    serializer_class = ComplaintSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ComplaintFilter

    def perform_create(self, serializer):
        instance = serializer.save()
        log_activity(
            customer=instance.customer, entity_type=ActivityLog.EntityType.COMPLAINT, entity_id=instance.id,
            action=ActivityLog.Action.CREATED, actor=_actor(self.request),
            new_data=complaint_snapshot(instance), instance_label=instance.fault_description,
        )

    def perform_update(self, serializer):
        old_data = complaint_snapshot(serializer.instance)
        instance = serializer.save()
        log_activity(
            customer=instance.customer, entity_type=ActivityLog.EntityType.COMPLAINT, entity_id=instance.id,
            action=ActivityLog.Action.UPDATED, actor=_actor(self.request),
            old_data=old_data, new_data=complaint_snapshot(instance), instance_label=instance.fault_description,
        )

    def perform_destroy(self, instance):
        log_activity(
            customer=instance.customer, entity_type=ActivityLog.EntityType.COMPLAINT, entity_id=instance.id,
            action=ActivityLog.Action.DELETED, actor=_actor(self.request),
            old_data=complaint_snapshot(instance), instance_label=instance.fault_description,
        )
        instance.delete()


class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Org-wide activity/reporting feed — read-only by design (it's an audit
    trail, not editable data). Supports filtering by customer, entity type,
    action, actor, and a date range (?created_after=&created_before=), plus
    free-text `?search=` over the human-readable summary.
    """
    queryset = ActivityLog.objects.select_related("customer", "actor").all()
    serializer_class = ActivityLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = ActivityLogFilter
    search_fields = ["summary", "customer_name_snapshot"]


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def dashboard_stats(request):
    """
    Aggregate counts powering the dashboard's charts and summary tiles.
    Kept as a single endpoint (rather than making the frontend compute this
    from a full customer list) so it stays fast as the dataset grows.
    """
    total_customers = Customer.objects.count()
    active_customers = Customer.objects.filter(is_active=True).count()

    status_breakdown = list(
        DSLService.objects.values("status").annotate(count=Count("id")).order_by("status")
    )
    technology_breakdown = list(
        DSLService.objects.values("technology").annotate(count=Count("id")).order_by("technology")
    )
    condition_breakdown = list(
        CopperPair.objects.values("condition").annotate(count=Count("id")).order_by("condition")
    )
    complaint_status_breakdown = list(
        Complaint.objects.values("status").annotate(count=Count("id")).order_by("status")
    )
    customers_by_city = list(
        Customer.objects.values("city__name")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    customers_by_region = list(
        Customer.objects.values("city__region__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    customers_by_msag = list(
        DSLService.objects.values("msag__code")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    # Port utilization per physical card (msag + card), out of the 64-port
    # cap enforced by the model — surfaces which cards are nearly full so a
    # technician knows where capacity is running out before a port-conflict
    # error happens at provisioning time.
    card_utilization = list(
        DSLService.objects.values("msag__code", "msag_card")
        .annotate(used_ports=Count("id"))
        .order_by("-used_ports")[:10]
    )

    since_24h = timezone.now() - timedelta(hours=24)
    since_7d = timezone.now() - timedelta(days=7)
    recent_activity = ActivityLog.objects.select_related("customer", "actor").all()[:8]

    return Response({
        "total_customers": total_customers,
        "active_customers": active_customers,
        "inactive_customers": total_customers - active_customers,
        "total_dsl_services": DSLService.objects.count(),
        "faulty_dsl_services": DSLService.objects.filter(status=DSLService.Status.FAULTY).count(),
        "total_copper_pairs": CopperPair.objects.count(),
        "status_breakdown": status_breakdown,
        "technology_breakdown": technology_breakdown,
        "condition_breakdown": condition_breakdown,
        "open_complaints": Complaint.objects.filter(
            status__in=[Complaint.Status.OPEN, Complaint.Status.IN_PROGRESS]
        ).count(),
        "complaint_status_breakdown": complaint_status_breakdown,
        "customers_by_city": [
            {"city": row["city__name"], "count": row["count"]} for row in customers_by_city
        ],
        "customers_by_region": [
            {"region": row["city__region__name"], "count": row["count"]} for row in customers_by_region
        ],
        "customers_by_msag": [
            {"msag": row["msag__code"], "count": row["count"]} for row in customers_by_msag
        ],
        "card_utilization": [
            {
                "msag": row["msag__code"], "card": row["msag_card"],
                "used_ports": row["used_ports"], "capacity": 64,
                "percent_full": round(row["used_ports"] / 64 * 100, 1),
            }
            for row in card_utilization
        ],
        "changes_last_24h": ActivityLog.objects.filter(created_at__gte=since_24h).count(),
        "changes_last_7d": ActivityLog.objects.filter(created_at__gte=since_7d).count(),
        "new_customers_last_7d": ActivityLog.objects.filter(
            entity_type=ActivityLog.EntityType.CUSTOMER, action=ActivityLog.Action.CREATED, created_at__gte=since_7d
        ).count(),
        "recent_activity": ActivityLogSerializer(recent_activity, many=True).data,
    })


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def activity_stats(request):
    """
    Reporting view over the activity log: totals by action/entity type, plus
    a 14-day daily trend for an "activity over time" chart.
    """
    action_breakdown = list(
        ActivityLog.objects.values("action").annotate(count=Count("id")).order_by("action")
    )
    entity_breakdown = list(
        ActivityLog.objects.values("entity_type").annotate(count=Count("id")).order_by("entity_type")
    )

    today = timezone.localdate()
    daily_counts = []
    for i in range(13, -1, -1):
        day = today - timedelta(days=i)
        count = ActivityLog.objects.filter(created_at__date=day).count()
        daily_counts.append({"date": day.isoformat(), "count": count})

    top_actors = list(
        ActivityLog.objects.exclude(actor_username_snapshot="")
        .values("actor_username_snapshot")
        .annotate(count=Count("id"))
        .order_by("-count")[:5]
    )

    return Response({
        "total_events": ActivityLog.objects.count(),
        "action_breakdown": action_breakdown,
        "entity_breakdown": entity_breakdown,
        "daily_counts": daily_counts,
        "top_actors": [
            {"actor": row["actor_username_snapshot"], "count": row["count"]} for row in top_actors
        ],
    })


PERIOD_DAYS = {"weekly": 7, "fortnightly": 15, "monthly": 30}
PERIOD_LABELS = {"weekly": "Last 7 days", "fortnightly": "Last 15 days", "monthly": "Last 30 days"}


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def activity_report(request):
    """
    Periodic business report over the activity log — the "what happened
    this week / fortnight / month" view for a supervisor, as opposed to
    activity_stats' rolling 14-day trend chart. Pass ?period=weekly (default),
    ?period=fortnightly (15 days), or ?period=monthly (30 days).
    """
    period = request.query_params.get("period", "weekly")
    days = PERIOD_DAYS.get(period)
    if days is None:
        return Response(
            {"detail": "period must be one of: weekly, fortnightly, monthly"},
            status=400,
        )

    end = timezone.now()
    start = end - timedelta(days=days)
    qs = ActivityLog.objects.filter(created_at__gte=start, created_at__lte=end)

    action_breakdown = list(qs.values("action").annotate(count=Count("id")).order_by("action"))
    entity_breakdown = list(qs.values("entity_type").annotate(count=Count("id")).order_by("entity_type"))

    new_customers = qs.filter(
        entity_type=ActivityLog.EntityType.CUSTOMER, action=ActivityLog.Action.CREATED
    ).count()
    complaints_opened = qs.filter(
        entity_type=ActivityLog.EntityType.COMPLAINT, action=ActivityLog.Action.CREATED
    ).count()
    complaints_resolved = Complaint.objects.filter(resolved_at__gte=start, resolved_at__lte=end).count()

    top_actors = list(
        qs.exclude(actor_username_snapshot="")
        .values("actor_username_snapshot")
        .annotate(count=Count("id"))
        .order_by("-count")[:5]
    )

    return Response({
        "period": period,
        "period_label": PERIOD_LABELS[period],
        "start": start.isoformat(),
        "end": end.isoformat(),
        "total_events": qs.count(),
        "action_breakdown": action_breakdown,
        "entity_breakdown": entity_breakdown,
        "new_customers": new_customers,
        "complaints_opened": complaints_opened,
        "complaints_resolved": complaints_resolved,
        "top_actors": [
            {"actor": row["actor_username_snapshot"], "count": row["count"]} for row in top_actors
        ],
    })
