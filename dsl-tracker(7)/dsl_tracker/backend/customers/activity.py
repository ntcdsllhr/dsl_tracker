"""
Activity logging service.

Explicitly called from viewsets (perform_create/perform_update/perform_destroy)
rather than wired through Django signals — this keeps "who did it" simple
(we have `request.user` right there) and keeps audit logging visible and
testable at the call site instead of hidden in signal handlers.

Usage pattern for an update:

    old_data = customer_snapshot(serializer.instance)   # BEFORE save
    instance = serializer.save()
    new_data = customer_snapshot(instance)
    log_activity(
        customer=instance, entity_type=ActivityLog.EntityType.CUSTOMER,
        entity_id=instance.id, action=ActivityLog.Action.UPDATED,
        actor=request.user, old_data=old_data, new_data=new_data,
    )
"""
from .models import ActivityLog

# Field labels used when building human-readable diff summaries.
_FIELD_LABELS = {
    "dsl_package": "DSL package",
    "msag_card": "MSAG card",
    "msag_port": "MSAG port",
    "ip_address": "IP address",
    "modem_serial": "Modem serial",
    "status_reason": "Status reason",
    "cable_length_meters": "Cable length (m)",
    "pair_number": "Pair number",
    "cabinet_code": "Cabinet code",
    "binder_group": "Binder group",
    "distribution_point": "Distribution point",
    "user_id": "User ID",
    "tax_code": "Tax code",
    "dept_code": "Dept code",
    "address_line": "Address",
    "phone_primary": "Primary phone",
    "phone_secondary": "Secondary phone",
    "is_active": "Active",
    "subscriber_type": "Subscriber type",
    "fault_description": "Fault description",
    "assigned_to": "Assigned to",
    "resolution_notes": "Resolution notes",
    "resolved_at": "Resolved at",
}


def _label(field):
    return _FIELD_LABELS.get(field, field.replace("_", " ").capitalize())


def customer_snapshot(instance):
    return {
        "name": instance.name,
        "department": instance.department,
        "subscriber_type": instance.get_subscriber_type_display(),
        "address_line": instance.address_line,
        "city": instance.city.name if instance.city_id else None,
        "postal_code": instance.postal_code,
        "contact_person": instance.contact_person,
        "phone_primary": instance.phone_primary,
        "phone_secondary": instance.phone_secondary,
        "email": instance.email,
        "user_id": instance.user_id,
        "tax_code": instance.tax_code,
        "dept_code": instance.dept_code,
        "is_active": instance.is_active,
    }


def dsl_service_snapshot(instance):
    return {
        "dsl_package": instance.dsl_package,
        "technology": instance.get_technology_display(),
        "operator": instance.operator,
        "msag": instance.msag.code if instance.msag_id else None,
        "msag_card": instance.msag_card,
        "msag_port": instance.msag_port,
        "ip_address": str(instance.ip_address) if instance.ip_address else None,
        "modem_serial": instance.modem_serial,
        "status": instance.get_status_display(),
        "status_reason": instance.status_reason,
        "activation_date": instance.activation_date.isoformat() if instance.activation_date else None,
    }


def copper_pair_snapshot(instance):
    return {
        "cabinet_code": instance.cabinet_code,
        "pair_number": instance.pair_number,
        "binder_group": instance.binder_group,
        "distribution_point": instance.distribution_point,
        "cable_length_meters": instance.cable_length_meters,
        "condition": instance.get_condition_display(),
        "notes": instance.notes,
    }


def complaint_snapshot(instance):
    return {
        "fault_description": instance.fault_description,
        "status": instance.get_status_display(),
        "assigned_to": instance.assigned_to,
        "resolution_notes": instance.resolution_notes,
    }


def _diff(old_data, new_data):
    changes = {}
    for key, new_val in new_data.items():
        old_val = (old_data or {}).get(key)
        if old_val != new_val:
            changes[key] = {"old": old_val, "new": new_val}
    return changes


def _build_summary(entity_label, instance_label, action, changes):
    if action == ActivityLog.Action.CREATED:
        return f"New {entity_label.lower()} added: {instance_label}"
    if action == ActivityLog.Action.DELETED:
        return f"{entity_label} removed: {instance_label}"
    if not changes:
        return f"{entity_label} updated: {instance_label} (no field changes detected)"
    parts = [
        f"{_label(field)} changed from '{delta['old'] if delta['old'] not in (None, '') else '—'}' "
        f"to '{delta['new'] if delta['new'] not in (None, '') else '—'}'"
        for field, delta in changes.items()
    ]
    return f"{entity_label} updated for {instance_label}: " + "; ".join(parts)


ENTITY_LABELS = {
    ActivityLog.EntityType.CUSTOMER: "Customer",
    ActivityLog.EntityType.DSL_SERVICE: "DSL service",
    ActivityLog.EntityType.COPPER_PAIR: "Copper pair",
    ActivityLog.EntityType.COMPLAINT: "Complaint",
}


def log_activity(*, customer, entity_type, entity_id, action, actor=None,
                  old_data=None, new_data=None, instance_label=None):
    """
    Write one ActivityLog row. `customer` may be None only for a just-deleted
    customer entity (the FK auto-nulls via SET_NULL once the row is gone, so
    pass the still-live instance here and delete it afterward).
    """
    changes = _diff(old_data, new_data) if action == ActivityLog.Action.UPDATED else {}
    entity_label = ENTITY_LABELS[entity_type]
    label = instance_label or (customer.name if customer else "record")
    summary = _build_summary(entity_label, label, action, changes)

    ActivityLog.objects.create(
        customer=customer,
        customer_name_snapshot=customer.name if customer else (instance_label or ""),
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        changes=changes,
        snapshot=new_data or old_data or {},
        actor=actor if (actor is not None and getattr(actor, "is_authenticated", False)) else None,
        actor_username_snapshot=actor.username if (actor is not None and getattr(actor, "is_authenticated", False)) else "",
        summary=summary,
    )
