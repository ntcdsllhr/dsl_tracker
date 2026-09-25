from rest_framework import serializers

from .models import ActivityLog, Complaint, CopperPair, Customer, DSLService, Exchange, MSAG, City, Region


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ["id", "name"]


class CitySerializer(serializers.ModelSerializer):
    region_name = serializers.CharField(source="region.name", read_only=True)

    class Meta:
        model = City
        fields = ["id", "region", "region_name", "name"]


class ExchangeSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source="city.name", read_only=True)

    class Meta:
        model = Exchange
        fields = ["id", "city", "city_name", "name", "directorate", "sub_division"]


class MSAGSerializer(serializers.ModelSerializer):
    exchange_name = serializers.CharField(source="exchange.name", read_only=True)

    class Meta:
        model = MSAG
        fields = ["id", "exchange", "exchange_name", "code", "location_description"]


class CopperPairSerializer(serializers.ModelSerializer):
    class Meta:
        model = CopperPair
        fields = [
            "id", "dsl_service", "cabinet_code", "pair_number", "binder_group",
            "distribution_point", "cable_length_meters", "condition", "notes",
            "last_tested_at", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class ComplaintSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)

    class Meta:
        model = Complaint
        fields = [
            "id", "customer", "customer_name", "fault_description", "status", "status_display",
            "assigned_to", "resolution_notes", "reported_at", "resolved_at", "updated_at",
        ]
        read_only_fields = ["reported_at", "resolved_at", "updated_at"]


class DSLServiceSerializer(serializers.ModelSerializer):
    copper_pair = CopperPairSerializer(read_only=True)
    msag_code = serializers.CharField(source="msag.code", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)

    class Meta:
        model = DSLService
        fields = [
            "id", "customer", "customer_name", "dsl_package", "technology", "operator",
            "msag", "msag_code", "msag_card", "msag_port", "ip_address", "modem_serial",
            "status", "status_reason", "activation_date", "last_fault_date",
            "copper_pair", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class CustomerListSerializer(serializers.ModelSerializer):
    """Lean serializer for the technician's search/list view."""
    city_name = serializers.CharField(source="city.name", read_only=True)
    dsl_status = serializers.CharField(source="dsl_service.status", read_only=True, default=None)
    dsl_package = serializers.CharField(source="dsl_service.dsl_package", read_only=True, default=None)
    msag_code = serializers.CharField(source="dsl_service.msag.code", read_only=True, default=None)
    msag_port = serializers.IntegerField(source="dsl_service.msag_port", read_only=True, default=None)
    pair_number = serializers.CharField(source="dsl_service.copper_pair.pair_number", read_only=True, default=None)
    open_complaint_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Customer
        fields = [
            "id", "name", "department", "subscriber_type", "address_line", "city",
            "city_name", "phone_primary", "user_id", "is_active",
            "dsl_status", "dsl_package", "msag_code", "msag_port", "pair_number", "open_complaint_count",
        ]


class CustomerDetailSerializer(serializers.ModelSerializer):
    """Full nested record — everything a field tech needs on one screen."""
    city_name = serializers.CharField(source="city.name", read_only=True)
    dsl_service = DSLServiceSerializer(read_only=True)
    open_complaint_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Customer
        fields = [
            "id", "name", "department", "subscriber_type", "address_line", "city",
            "city_name", "postal_code", "contact_person", "phone_primary",
            "phone_secondary", "email", "user_id", "tax_code", "dept_code",
            "is_active", "dsl_service", "open_complaint_count", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class CustomerWriteSerializer(serializers.ModelSerializer):
    """Used for create/update of the Customer record itself (DSL/pair have their own endpoints)."""

    class Meta:
        model = Customer
        fields = [
            "id", "name", "department", "subscriber_type", "address_line", "city",
            "postal_code", "contact_person", "phone_primary", "phone_secondary",
            "email", "user_id", "tax_code", "dept_code", "is_active",
        ]


class ActivityLogSerializer(serializers.ModelSerializer):
    """Read-only representation of an audit trail entry — powers both the
    per-customer History tab and the org-wide Activity/Reporting feed."""

    action_display = serializers.CharField(source="get_action_display", read_only=True)
    entity_type_display = serializers.CharField(source="get_entity_type_display", read_only=True)
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = ActivityLog
        fields = [
            "id", "customer", "customer_name", "customer_name_snapshot",
            "entity_type", "entity_type_display", "entity_id", "action", "action_display",
            "changes", "snapshot", "actor", "actor_username_snapshot", "summary", "created_at",
        ]

    def get_customer_name(self, obj):
        # Prefer the live customer's current name; fall back to the snapshot
        # taken at log time (covers the case where the customer was later deleted).
        return obj.customer.name if obj.customer_id else obj.customer_name_snapshot
