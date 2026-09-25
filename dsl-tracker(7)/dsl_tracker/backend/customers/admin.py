from django.contrib import admin

from .models import ActivityLog, Complaint, CopperPair, Customer, DSLService, Exchange, MSAG, City, Region


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ["name", "region"]
    list_filter = ["region"]
    search_fields = ["name"]


@admin.register(Exchange)
class ExchangeAdmin(admin.ModelAdmin):
    list_display = ["name", "city", "directorate", "sub_division"]
    list_filter = ["city__region", "city"]
    search_fields = ["name", "directorate", "sub_division"]


@admin.register(MSAG)
class MSAGAdmin(admin.ModelAdmin):
    list_display = ["code", "exchange", "location_description"]
    list_filter = ["exchange"]
    search_fields = ["code", "location_description"]


class DSLServiceInline(admin.StackedInline):
    model = DSLService
    extra = 0


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["name", "department", "phone_primary", "city", "user_id", "is_active"]
    list_filter = ["is_active", "subscriber_type", "city__region", "city"]
    search_fields = ["name", "phone_primary", "phone_secondary", "user_id", "address_line"]
    inlines = [DSLServiceInline]


class CopperPairInline(admin.StackedInline):
    model = CopperPair
    extra = 0


@admin.register(DSLService)
class DSLServiceAdmin(admin.ModelAdmin):
    list_display = ["customer", "dsl_package", "status", "msag", "msag_card", "msag_port"]
    list_filter = ["status", "technology", "msag__exchange"]
    search_fields = ["customer__name", "customer__phone_primary", "modem_serial"]
    inlines = [CopperPairInline]


@admin.register(CopperPair)
class CopperPairAdmin(admin.ModelAdmin):
    list_display = ["pair_number", "dsl_service", "cabinet_code", "condition"]
    list_filter = ["condition"]
    search_fields = ["pair_number", "cabinet_code", "distribution_point"]


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ["customer", "fault_description", "status", "assigned_to", "reported_at", "resolved_at"]
    list_filter = ["status"]
    search_fields = ["fault_description", "customer__name", "assigned_to"]


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ["created_at", "action", "entity_type", "customer_name_snapshot", "actor_username_snapshot", "summary"]
    list_filter = ["action", "entity_type"]
    search_fields = ["summary", "customer_name_snapshot", "actor_username_snapshot"]
    readonly_fields = [f.name for f in ActivityLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
