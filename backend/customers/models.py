"""
Core data models for the DSL Customer Technical Information system.

Design notes
------------
- No billing / financial fields anywhere in this app, by design (see spec).
- Field choices are informed by the reference CRM screenshots: region/city/
  location groupings, MSAG identifiers, technology/operator, and complaint-style
  status tracking — but re-purposed here for a *technical reference* record
  rather than a billing/complaint system.
- `Customer` <-> `DSLService` is one-to-one: in this ISP's model, a customer
  premise has a single active DSL line. `DSLService` <-> `CopperPair` is
  one-to-one as well (one pair feeds one line at a time), but is modeled as
  its own table so pair swaps/history can be tracked later without touching
  the service row.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class Region(models.Model):
    """Top-level geography, e.g. 'Lahore Region' (from GI_REGION in legacy CRM)."""
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class City(models.Model):
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="cities")
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["name"]
        unique_together = ("region", "name")

    def __str__(self):
        return f"{self.name} ({self.region.name})"


class Exchange(models.Model):
    """Telephone exchange / directorate — e.g. 'Lahore Directorate (WO)', 'GOR-III LHR MSAG'.

    Corresponds loosely to the legacy system's Directorate / Sub Division / GI_LOCATION.
    """
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name="exchanges")
    name = models.CharField(max_length=150)
    directorate = models.CharField(max_length=150, blank=True, help_text="e.g. Lahore Directorate (WO)")
    sub_division = models.CharField(max_length=150, blank=True, help_text="e.g. DSL Lahore (WO)")

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Exchanges"

    def __str__(self):
        return self.name


class MSAG(models.Model):
    """Main Site/Street Address Guide cabinet — groups MSAG cards/ports.

    e.g. 'GOR-III LHR MSAG'
    """
    exchange = models.ForeignKey(Exchange, on_delete=models.PROTECT, related_name="msags")
    code = models.CharField(max_length=50, help_text="MSAG identifier / cabinet code")
    location_description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["code"]
        unique_together = ("exchange", "code")
        verbose_name = "MSAG"
        verbose_name_plural = "MSAGs"

    def __str__(self):
        return f"{self.code} — {self.exchange.name}"


class Customer(models.Model):
    """A government subscriber premise. No billing/financial data lives here."""

    class SubscriberType(models.TextChoices):
        GOVERNMENT = "GOV", "Government"
        SEMI_GOVERNMENT = "SEMI_GOV", "Semi-Government"

    name = models.CharField(max_length=200)
    department = models.CharField(max_length=200, blank=True, help_text="e.g. Admin, GOVT. COLLEGE OF TECHNOLOGY")
    subscriber_type = models.CharField(
        max_length=20, choices=SubscriberType.choices, default=SubscriberType.GOVERNMENT
    )

    # Address
    address_line = models.CharField(max_length=255)
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name="customers")
    postal_code = models.CharField(max_length=20, blank=True)

    # Contact info
    contact_person = models.CharField(max_length=150, blank=True)
    phone_primary = models.CharField(max_length=30, help_text="Landline / customer phone, e.g. 0559201351")
    phone_secondary = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)

    user_id = models.CharField(
        max_length=50, blank=True, unique=False,
        help_text="ISP subscriber/user ID, e.g. lah9201640",
    )
    tax_code = models.CharField(max_length=50, blank=True)
    dept_code = models.CharField(max_length=50, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="customers_created",
    )

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["phone_primary"]),
            models.Index(fields=["user_id"]),
        ]

    def __str__(self):
        return f"{self.name} — {self.phone_primary}"


class DSLService(models.Model):
    """The DSL line technical record for a customer premise."""

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        SUSPENDED = "SUSPENDED", "Suspended"
        FAULTY = "FAULTY", "Faulty"
        DECOMMISSIONED = "DECOMMISSIONED", "Decommissioned"

    class Technology(models.TextChoices):
        ADSL2PLUS = "ADSL2+", "ADSL2+"
        VDSL2 = "VDSL2", "VDSL2"
        SHDSL = "SHDSL", "SHDSL"

    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name="dsl_service")

    dsl_package = models.CharField(max_length=100, help_text="e.g. 'Broadband 8Mbps Unlimited'")
    technology = models.CharField(max_length=20, choices=Technology.choices, default=Technology.ADSL2PLUS)
    operator = models.CharField(max_length=100, blank=True)

    msag = models.ForeignKey(MSAG, on_delete=models.PROTECT, related_name="dsl_services")
    msag_card = models.CharField(max_length=20, help_text="MSAG card number, e.g. 'C04'")
    msag_port = models.CharField(max_length=20, help_text="MSAG port number, e.g. 'P12'")

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    modem_serial = models.CharField(max_length=100, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    status_reason = models.CharField(max_length=255, blank=True)

    activation_date = models.DateField(null=True, blank=True)
    last_fault_date = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["customer__name"]
        indexes = [
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"DSL for {self.customer.name} ({self.status})"


class CopperPair(models.Model):
    """Physical copper pair feeding a DSL service — the field tech's core lookup."""

    class Condition(models.TextChoices):
        GOOD = "GOOD", "Good"
        DEGRADED = "DEGRADED", "Degraded"
        FAULTY = "FAULTY", "Faulty"
        UNKNOWN = "UNKNOWN", "Unknown"

    dsl_service = models.OneToOneField(DSLService, on_delete=models.CASCADE, related_name="copper_pair")

    cabinet_code = models.CharField(max_length=50, blank=True, help_text="Street cabinet / DP identifier")
    pair_number = models.CharField(max_length=20, help_text="Copper pair number, e.g. '214'")
    binder_group = models.CharField(max_length=50, blank=True)
    distribution_point = models.CharField(max_length=100, blank=True, help_text="Pole/DP reference")

    cable_length_meters = models.PositiveIntegerField(null=True, blank=True)
    condition = models.CharField(max_length=20, choices=Condition.choices, default=Condition.UNKNOWN)
    notes = models.TextField(blank=True)

    last_tested_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["pair_number"]

    def __str__(self):
        return f"Pair {self.pair_number} ({self.dsl_service.customer.name})"


class Complaint(models.Model):
    """
    A fault/complaint ticket for a customer — the technician-facing record of
    "something was wrong, here's what, who's on it, and when it was fixed."

    Deliberately minimal: a handful of fields cover the full lifecycle
    (reported → assigned → resolved) without duplicating data already on
    DSLService/CopperPair. `assigned_to` is a plain text field rather than a
    FK to auth.User because field technicians (linemen) frequently don't
    have login accounts in a system like this — matches the legacy CRM's
    "Assigned Lineman" free-text pattern.

    Every status change is separately captured in ActivityLog (entity_type
    COMPLAINT) via the same audit trail as Customer/DSLService/CopperPair,
    so "who marked this resolved and when" is always answerable without
    needing extra fields here.
    """

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        RESOLVED = "RESOLVED", "Resolved"
        IRRELEVANT = "IRRELEVANT", "Irrelevant"

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="complaints")

    fault_description = models.CharField(max_length=255, help_text="e.g. 'No dial tone', 'DSL not syncing'")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    assigned_to = models.CharField(max_length=150, blank=True, help_text="Assigned lineman/technician name")
    resolution_notes = models.CharField(max_length=500, blank=True)

    reported_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-reported_at"]
        indexes = [
            models.Index(fields=["customer", "-reported_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"[{self.get_status_display()}] {self.fault_description} — {self.customer.name}"

    def save(self, *args, **kwargs):
        # resolved_at tracks itself: set the moment status becomes RESOLVED,
        # cleared if it's reopened — one less field for the technician to
        # remember to fill in by hand.
        if self.status == self.Status.RESOLVED and self.resolved_at is None:
            self.resolved_at = timezone.now()
        elif self.status != self.Status.RESOLVED:
            self.resolved_at = None
        super().save(*args, **kwargs)


class ActivityLog(models.Model):
    """
    Append-only audit trail for every create/update/delete on Customer,
    DSLService, and CopperPair. This is the source of truth for both the
    per-customer "History" timeline and the org-wide Activity/Reporting feed.

    Design choices:
    - `customer` is a nullable FK (SET_NULL) so a log entry survives the
      customer being deleted — `customer_name_snapshot` keeps it readable.
    - `changes` stores a field-level diff as {field: {"old": ..., "new": ...}}
      using human-readable values (choice display labels, related object
      names) rather than raw DB values, so the feed reads naturally without
      the frontend needing to know each model's choices.
    - `snapshot` stores the full post-change state, so a point-in-time view
      of "what did this record look like after this event" is always
      available even if the live record has since changed further.
    - Never updated or deleted via the API once written (see views.py) —
      it's an audit log, not editable data.
    """

    class Action(models.TextChoices):
        CREATED = "CREATED", "Created"
        UPDATED = "UPDATED", "Updated"
        DELETED = "DELETED", "Deleted"

    class EntityType(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer"
        DSL_SERVICE = "DSL_SERVICE", "DSL Service"
        COPPER_PAIR = "COPPER_PAIR", "Copper Pair"
        COMPLAINT = "COMPLAINT", "Complaint"

    customer = models.ForeignKey(
        Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name="activity_logs"
    )
    customer_name_snapshot = models.CharField(max_length=200, blank=True)

    entity_type = models.CharField(max_length=20, choices=EntityType.choices)
    entity_id = models.PositiveIntegerField()
    action = models.CharField(max_length=10, choices=Action.choices)

    changes = models.JSONField(default=dict, blank=True)
    snapshot = models.JSONField(default=dict, blank=True)

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="activity_logs"
    )
    actor_username_snapshot = models.CharField(max_length=150, blank=True)

    summary = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer", "-created_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["-created_at"]),
            models.Index(fields=["action"]),
        ]

    def __str__(self):
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {self.get_action_display()} {self.get_entity_type_display()} — {self.summary}"
