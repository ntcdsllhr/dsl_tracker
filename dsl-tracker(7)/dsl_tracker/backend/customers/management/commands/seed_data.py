"""
Seed the database with lookup data (regions/cities/exchanges/MSAGs) and a handful
of sample government-subscriber customer records, for local dev and demos.

Usage:
    python manage.py seed_data
    python manage.py seed_data --flush   # wipe existing customer data first
"""
import random

from django.core.management.base import BaseCommand
from django.db import transaction

from customers.activity import copper_pair_snapshot, customer_snapshot, dsl_service_snapshot, log_activity
from customers.models import ActivityLog, CopperPair, Customer, DSLService, Exchange, MSAG, City, Region

SAMPLE_CUSTOMERS = [
    {
        "name": "Govt. College of Technology",
        "department": "Admin",
        "address_line": "GOR-III, Lahore",
        "phone_primary": "0559201351",
        "user_id": "lah9201640",
        "dsl_package": "Broadband 8Mbps Unlimited",
        "msag_card": "C04",
        "msag_port": 12,
        "pair_number": "214",
        "cabinet_code": "GOR3-CAB-02",
    },
    {
        "name": "WAPDA Wireless Office",
        "department": "Admin",
        "address_line": "WAPDA House, Lahore",
        "phone_primary": "04299202783",
        "user_id": "lah9202001",
        "dsl_package": "Broadband 4Mbps Unlimited",
        "msag_card": "C02",
        "msag_port": 5,
        "pair_number": "088",
        "cabinet_code": "WAPDA-CAB-01",
    },
    {
        "name": "Lahore Development Authority",
        "department": "Admin",
        "address_line": "LDA Plaza, Egerton Road, Lahore",
        "phone_primary": "04299204411",
        "user_id": "lah9204411",
        "dsl_package": "Broadband 8Mbps Unlimited",
        "msag_card": "C07",
        "msag_port": 3,
        "pair_number": "156",
        "cabinet_code": "EGRT-CAB-04",
    },
    {
        "name": "Punjab Secretariat",
        "department": "Admin",
        "address_line": "Civil Secretariat, Lahore",
        "phone_primary": "04299210020",
        "user_id": "lah9210020",
        "dsl_package": "Broadband 16Mbps Unlimited",
        "msag_card": "C01",
        "msag_port": 1,
        "pair_number": "002",
        "cabinet_code": "CSEC-CAB-01",
    },
]


class Command(BaseCommand):
    help = "Seed lookup tables and sample customer/DSL/copper-pair records"

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush", action="store_true",
            help="Delete existing Customer/DSLService/CopperPair rows before seeding",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["flush"]:
            self.stdout.write("Flushing existing customer data...")
            ActivityLog.objects.all().delete()
            CopperPair.objects.all().delete()
            DSLService.objects.all().delete()
            Customer.objects.all().delete()

        region, _ = Region.objects.get_or_create(name="Lahore Region")
        city, _ = City.objects.get_or_create(region=region, name="Lahore")
        exchange, _ = Exchange.objects.get_or_create(
            city=city, name="Lahore Directorate (WO)",
            defaults={"directorate": "Lahore Directorate (WO)", "sub_division": "DSL Lahore (WO)"},
        )
        msag, _ = MSAG.objects.get_or_create(
            exchange=exchange, code="GOR-III LHR MSAG",
            defaults={"location_description": "GOR-III, Lahore"},
        )

        created = 0
        first_customer = None
        for row in SAMPLE_CUSTOMERS:
            customer, was_created = Customer.objects.get_or_create(
                phone_primary=row["phone_primary"],
                defaults={
                    "name": row["name"],
                    "department": row["department"],
                    "address_line": row["address_line"],
                    "city": city,
                    "user_id": row["user_id"],
                },
            )
            if not was_created:
                continue

            log_activity(
                customer=customer, entity_type=ActivityLog.EntityType.CUSTOMER, entity_id=customer.id,
                action=ActivityLog.Action.CREATED, new_data=customer_snapshot(customer),
            )

            dsl_service = DSLService.objects.create(
                customer=customer,
                dsl_package=row["dsl_package"],
                msag=msag,
                msag_card=row["msag_card"],
                msag_port=row["msag_port"],
                status=DSLService.Status.ACTIVE,
            )
            log_activity(
                customer=customer, entity_type=ActivityLog.EntityType.DSL_SERVICE, entity_id=dsl_service.id,
                action=ActivityLog.Action.CREATED, new_data=dsl_service_snapshot(dsl_service),
            )

            pair = CopperPair.objects.create(
                dsl_service=dsl_service,
                cabinet_code=row["cabinet_code"],
                pair_number=row["pair_number"],
                condition=random.choice(CopperPair.Condition.values),
            )
            log_activity(
                customer=customer, entity_type=ActivityLog.EntityType.COPPER_PAIR, entity_id=pair.id,
                action=ActivityLog.Action.CREATED, new_data=copper_pair_snapshot(pair),
            )

            if first_customer is None:
                first_customer = (customer, dsl_service, pair)
            created += 1

        # Simulate a bit of history on the first seeded customer so the
        # History tab / Activity feed have something realistic to show
        # out of the box, instead of a flat "created" event each.
        if first_customer:
            customer, dsl_service, pair = first_customer

            old = dsl_service_snapshot(dsl_service)
            dsl_service.status = DSLService.Status.FAULTY
            dsl_service.status_reason = "Reported no sync by customer"
            dsl_service.save()
            log_activity(
                customer=customer, entity_type=ActivityLog.EntityType.DSL_SERVICE, entity_id=dsl_service.id,
                action=ActivityLog.Action.UPDATED, old_data=old, new_data=dsl_service_snapshot(dsl_service),
            )

            old = copper_pair_snapshot(pair)
            pair.condition = CopperPair.Condition.FAULTY
            pair.notes = "Water ingress suspected at cabinet joint"
            pair.save()
            log_activity(
                customer=customer, entity_type=ActivityLog.EntityType.COPPER_PAIR, entity_id=pair.id,
                action=ActivityLog.Action.UPDATED, old_data=old, new_data=copper_pair_snapshot(pair),
            )

            old = dsl_service_snapshot(dsl_service)
            dsl_service.status = DSLService.Status.ACTIVE
            dsl_service.status_reason = "Pair repaired and re-tested"
            dsl_service.save()
            log_activity(
                customer=customer, entity_type=ActivityLog.EntityType.DSL_SERVICE, entity_id=dsl_service.id,
                action=ActivityLog.Action.UPDATED, old_data=old, new_data=dsl_service_snapshot(dsl_service),
            )

            old = copper_pair_snapshot(pair)
            pair.condition = CopperPair.Condition.GOOD
            pair.save()
            log_activity(
                customer=customer, entity_type=ActivityLog.EntityType.COPPER_PAIR, entity_id=pair.id,
                action=ActivityLog.Action.UPDATED, old_data=old, new_data=copper_pair_snapshot(pair),
            )

        self.stdout.write(self.style.SUCCESS(
            f"Seed complete: {created} customer record(s) created "
            f"(region={region.name}, exchange={exchange.name}, msag={msag.code})."
        ))
