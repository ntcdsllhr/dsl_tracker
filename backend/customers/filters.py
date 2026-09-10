import django_filters as df

from .models import ActivityLog, Complaint, Customer


class CustomerFilter(df.FilterSet):
    """Powers the technician search screen — mirrors the legacy CRM's search panel
    (region / city / location / status / phone) but scoped to technical fields only."""

    region = df.NumberFilter(field_name="city__region_id")
    city = df.NumberFilter(field_name="city_id")
    status = df.CharFilter(field_name="dsl_service__status", lookup_expr="iexact")
    phone = df.CharFilter(field_name="phone_primary", lookup_expr="icontains")
    user_id = df.CharFilter(field_name="user_id", lookup_expr="icontains")
    msag = df.CharFilter(field_name="dsl_service__msag__code", lookup_expr="icontains")
    pair_number = df.CharFilter(field_name="dsl_service__copper_pair__pair_number", lookup_expr="icontains")
    is_active = df.BooleanFilter(field_name="is_active")
    has_open_complaint = df.BooleanFilter(method="filter_has_open_complaint")

    def filter_has_open_complaint(self, queryset, name, value):
        open_statuses = [Complaint.Status.OPEN, Complaint.Status.IN_PROGRESS]
        if value:
            return queryset.filter(complaints__status__in=open_statuses).distinct()
        return queryset.exclude(complaints__status__in=open_statuses).distinct()

    class Meta:
        model = Customer
        fields = ["region", "city", "status", "phone", "user_id", "msag", "pair_number", "is_active", "has_open_complaint"]


class ActivityLogFilter(df.FilterSet):
    """Powers the Activity/Reporting feed: by customer, entity/action type,
    actor, and a created_at date range."""

    customer = df.NumberFilter(field_name="customer_id")
    entity_type = df.CharFilter(field_name="entity_type", lookup_expr="iexact")
    action = df.CharFilter(field_name="action", lookup_expr="iexact")
    actor = df.CharFilter(field_name="actor_username_snapshot", lookup_expr="icontains")
    created_after = df.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = df.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = ActivityLog
        fields = ["customer", "entity_type", "action", "actor", "created_after", "created_before"]


class ComplaintFilter(df.FilterSet):
    """Powers the fault/complaint history views: by customer and status."""

    customer = df.NumberFilter(field_name="customer_id")
    status = df.CharFilter(field_name="status", lookup_expr="iexact")

    class Meta:
        model = Complaint
        fields = ["customer", "status"]
