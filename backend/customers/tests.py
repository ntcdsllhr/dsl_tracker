"""
API test suite for the customers app.

Covers: auth requirement, CRUD on customers, nested DSL service/copper pair
creation, search + filtering, and a guardrail test asserting no billing/
financial fields ever leak into the API surface.
"""
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import ActivityLog, Complaint, CopperPair, Customer, DSLService, Exchange, MSAG, City, Region


class BaseAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tech1", password="testpass123")
        self.client.force_authenticate(user=self.user)

        self.region = Region.objects.create(name="Lahore Region")
        self.city = City.objects.create(region=self.region, name="Lahore")
        self.exchange = Exchange.objects.create(
            city=self.city, name="Lahore Directorate (WO)",
            directorate="Lahore Directorate (WO)", sub_division="DSL Lahore (WO)",
        )
        self.msag = MSAG.objects.create(
            exchange=self.exchange, code="GOR-III LHR MSAG", location_description="GOR-III, Lahore"
        )

    def make_customer(self, **overrides):
        defaults = dict(
            name="Govt. College of Technology",
            department="Admin",
            address_line="GOR-III, Lahore",
            city=self.city,
            phone_primary="0559201351",
            user_id="lah9201640",
        )
        defaults.update(overrides)
        return Customer.objects.create(**defaults)


class AuthenticationTests(APITestCase):
    def test_unauthenticated_requests_are_rejected(self):
        resp = self.client.get("/api/customers/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_login_returns_token(self):
        User.objects.create_user(username="tech1", password="testpass123")
        resp = self.client.post("/api/auth/token/", {"username": "tech1", "password": "testpass123"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("token", resp.data)

    def test_token_login_rejects_bad_credentials(self):
        User.objects.create_user(username="tech1", password="testpass123")
        resp = self.client.post("/api/auth/token/", {"username": "tech1", "password": "wrong"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class CustomerCRUDTests(BaseAPITestCase):
    def test_create_customer(self):
        payload = {
            "name": "WAPDA Wireless Office",
            "department": "Admin",
            "address_line": "WAPDA House, Lahore",
            "city": self.city.id,
            "phone_primary": "04299202783",
            "user_id": "lah9202001",
        }
        resp = self.client.post("/api/customers/", payload)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(Customer.objects.count(), 1)
        customer = Customer.objects.get()
        self.assertEqual(customer.created_by, self.user)

    def test_create_customer_requires_name_and_address(self):
        resp = self.client.post("/api/customers/", {"city": self.city.id, "phone_primary": "123"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", resp.data)
        self.assertIn("address_line", resp.data)

    def test_list_customers(self):
        self.make_customer()
        self.make_customer(name="Punjab Secretariat", phone_primary="04299210020", user_id="lah9210020")
        resp = self.client.get("/api/customers/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 2)

    def test_retrieve_customer_detail_includes_nested_dsl_and_pair(self):
        customer = self.make_customer()
        dsl = DSLService.objects.create(
            customer=customer, dsl_package="Broadband 8Mbps Unlimited",
            msag=self.msag, msag_card="C04", msag_port="P12",
        )
        CopperPair.objects.create(dsl_service=dsl, pair_number="214", cabinet_code="GOR3-CAB-02")

        resp = self.client.get(f"/api/customers/{customer.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["dsl_service"]["dsl_package"], "Broadband 8Mbps Unlimited")
        self.assertEqual(resp.data["dsl_service"]["copper_pair"]["pair_number"], "214")

    def test_update_customer(self):
        customer = self.make_customer()
        resp = self.client.patch(f"/api/customers/{customer.id}/", {"contact_person": "M. Aslam"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        customer.refresh_from_db()
        self.assertEqual(customer.contact_person, "M. Aslam")

    def test_delete_customer_cascades_to_dsl_and_pair(self):
        customer = self.make_customer()
        dsl = DSLService.objects.create(
            customer=customer, dsl_package="Broadband 8Mbps Unlimited",
            msag=self.msag, msag_card="C04", msag_port="P12",
        )
        CopperPair.objects.create(dsl_service=dsl, pair_number="214")

        resp = self.client.delete(f"/api/customers/{customer.id}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Customer.objects.count(), 0)
        self.assertEqual(DSLService.objects.count(), 0)
        self.assertEqual(CopperPair.objects.count(), 0)


class SearchAndFilterTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.c1 = self.make_customer()
        self.c2 = self.make_customer(
            name="WAPDA Wireless Office", phone_primary="04299202783", user_id="lah9202001",
        )
        self.dsl1 = DSLService.objects.create(
            customer=self.c1, dsl_package="Broadband 8Mbps Unlimited",
            msag=self.msag, msag_card="C04", msag_port="P12", status=DSLService.Status.ACTIVE,
        )
        self.dsl2 = DSLService.objects.create(
            customer=self.c2, dsl_package="Broadband 4Mbps Unlimited",
            msag=self.msag, msag_card="C02", msag_port="P05", status=DSLService.Status.FAULTY,
        )

    def test_search_by_name(self):
        resp = self.client.get("/api/customers/?search=WAPDA")
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["name"], "WAPDA Wireless Office")

    def test_search_by_phone(self):
        resp = self.client.get("/api/customers/?search=0559201351")
        self.assertEqual(resp.data["count"], 1)

    def test_filter_by_status(self):
        resp = self.client.get("/api/customers/?status=FAULTY")
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["name"], "WAPDA Wireless Office")

    def test_filter_by_city(self):
        other_city = City.objects.create(region=self.region, name="Faisalabad")
        self.make_customer(name="Other City Office", city=other_city, phone_primary="111", user_id="fsd1")

        resp = self.client.get(f"/api/customers/?city={self.city.id}")
        self.assertEqual(resp.data["count"], 2)


class NoBillingFieldsGuardrailTests(BaseAPITestCase):
    """Explicit guardrail: this app must never expose billing/financial data."""

    BLOCKED_TERMS = ["bill", "invoice", "payment", "balance", "price", "amount_due", "arrears"]

    def test_customer_detail_response_has_no_billing_terms(self):
        customer = self.make_customer()
        resp = self.client.get(f"/api/customers/{customer.id}/")
        keys = " ".join(resp.data.keys()).lower()
        for term in self.BLOCKED_TERMS:
            self.assertNotIn(term, keys, f"Unexpected billing-related field: {term}")

    def test_dsl_service_response_has_no_billing_terms(self):
        customer = self.make_customer()
        dsl = DSLService.objects.create(
            customer=customer, dsl_package="Broadband 8Mbps Unlimited",
            msag=self.msag, msag_card="C04", msag_port="P12",
        )
        resp = self.client.get(f"/api/dsl-services/{dsl.id}/")
        keys = " ".join(resp.data.keys()).lower()
        for term in self.BLOCKED_TERMS:
            self.assertNotIn(term, keys, f"Unexpected billing-related field: {term}")

    def test_complaint_response_has_no_billing_terms(self):
        customer = self.make_customer()
        complaint = Complaint.objects.create(customer=customer, fault_description="No dial tone")
        resp = self.client.get(f"/api/complaints/{complaint.id}/")
        keys = " ".join(resp.data.keys()).lower()
        for term in self.BLOCKED_TERMS:
            self.assertNotIn(term, keys, f"Unexpected billing-related field: {term}")


class NestedServiceCreationTests(BaseAPITestCase):
    def test_create_dsl_service_for_existing_customer(self):
        customer = self.make_customer()
        payload = {
            "customer": customer.id,
            "dsl_package": "Broadband 8Mbps Unlimited",
            "msag": self.msag.id,
            "msag_card": "C04",
            "msag_port": "P12",
        }
        resp = self.client.post("/api/dsl-services/", payload)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

    def test_create_copper_pair_for_dsl_service(self):
        customer = self.make_customer()
        dsl = DSLService.objects.create(
            customer=customer, dsl_package="Broadband 8Mbps Unlimited",
            msag=self.msag, msag_card="C04", msag_port="P12",
        )
        payload = {"dsl_service": dsl.id, "pair_number": "214", "cabinet_code": "GOR3-CAB-02"}
        resp = self.client.post("/api/copper-pairs/", payload)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)


class DashboardStatsTests(BaseAPITestCase):
    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get("/api/dashboard/stats/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_stats_reflect_seeded_data(self):
        customer = self.make_customer()
        dsl = DSLService.objects.create(
            customer=customer, dsl_package="Broadband 8Mbps Unlimited",
            msag=self.msag, msag_card="C04", msag_port="P12",
            status=DSLService.Status.FAULTY,
        )
        CopperPair.objects.create(dsl_service=dsl, pair_number="214", condition=CopperPair.Condition.DEGRADED)

        resp = self.client.get("/api/dashboard/stats/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["total_customers"], 1)
        self.assertEqual(resp.data["faulty_dsl_services"], 1)
        self.assertEqual(resp.data["total_copper_pairs"], 1)
        self.assertIn({"status": "FAULTY", "count": 1}, resp.data["status_breakdown"])
        self.assertIn({"condition": "DEGRADED", "count": 1}, resp.data["condition_breakdown"])


class ActivityLoggingTests(BaseAPITestCase):
    """Covers the audit trail: creation, field-diff updates, deletion, and
    the per-customer history + org-wide activity feed endpoints."""

    def test_creating_customer_writes_created_log(self):
        payload = {
            "name": "WAPDA Wireless Office", "address_line": "WAPDA House, Lahore",
            "city": self.city.id, "phone_primary": "04299202783",
        }
        resp = self.client.post("/api/customers/", payload)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        log = ActivityLog.objects.get(entity_type=ActivityLog.EntityType.CUSTOMER, action=ActivityLog.Action.CREATED)
        self.assertEqual(log.customer_id, resp.data["id"])
        self.assertEqual(log.actor, self.user)
        self.assertIn("WAPDA Wireless Office", log.summary)
        self.assertEqual(log.changes, {})  # no diff on creation

    def test_updating_customer_writes_field_level_diff(self):
        customer = self.make_customer()
        resp = self.client.patch(f"/api/customers/{customer.id}/", {"contact_person": "M. Aslam"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        log = ActivityLog.objects.get(entity_type=ActivityLog.EntityType.CUSTOMER, action=ActivityLog.Action.UPDATED)
        self.assertIn("contact_person", log.changes)
        self.assertEqual(log.changes["contact_person"]["new"], "M. Aslam")
        self.assertIn("contact person changed", log.summary.lower())

    def test_unchanged_update_produces_empty_diff(self):
        customer = self.make_customer()
        self.client.patch(f"/api/customers/{customer.id}/", {"name": customer.name})
        log = ActivityLog.objects.filter(
            entity_type=ActivityLog.EntityType.CUSTOMER, action=ActivityLog.Action.UPDATED
        ).latest("created_at")
        self.assertEqual(log.changes, {})

    def test_deleting_customer_writes_deleted_log_and_survives_fk_nulling(self):
        customer = self.make_customer()
        customer_id = customer.id
        resp = self.client.delete(f"/api/customers/{customer_id}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

        log = ActivityLog.objects.get(entity_type=ActivityLog.EntityType.CUSTOMER, entity_id=customer_id)
        self.assertEqual(log.action, ActivityLog.Action.DELETED)
        self.assertIsNone(log.customer_id)  # SET_NULL fired since the customer row is gone
        self.assertEqual(log.customer_name_snapshot, "Govt. College of Technology")

    def test_dsl_service_status_change_is_logged_against_the_customer(self):
        customer = self.make_customer()
        dsl = DSLService.objects.create(
            customer=customer, dsl_package="Broadband 8Mbps Unlimited",
            msag=self.msag, msag_card="C04", msag_port="P12", status=DSLService.Status.ACTIVE,
        )
        resp = self.client.patch(f"/api/dsl-services/{dsl.id}/", {"status": "FAULTY"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        log = ActivityLog.objects.get(entity_type=ActivityLog.EntityType.DSL_SERVICE, action=ActivityLog.Action.UPDATED)
        self.assertEqual(log.customer_id, customer.id)
        self.assertEqual(log.changes["status"], {"old": "Active", "new": "Faulty"})

    def test_copper_pair_condition_change_is_logged(self):
        customer = self.make_customer()
        dsl = DSLService.objects.create(
            customer=customer, dsl_package="Broadband 8Mbps Unlimited",
            msag=self.msag, msag_card="C04", msag_port="P12",
        )
        pair = CopperPair.objects.create(dsl_service=dsl, pair_number="214", condition=CopperPair.Condition.GOOD)
        resp = self.client.patch(f"/api/copper-pairs/{pair.id}/", {"condition": "FAULTY"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        log = ActivityLog.objects.get(entity_type=ActivityLog.EntityType.COPPER_PAIR, action=ActivityLog.Action.UPDATED)
        self.assertEqual(log.customer_id, customer.id)
        self.assertEqual(log.changes["condition"], {"old": "Good", "new": "Faulty"})

    def test_customer_history_endpoint_returns_all_related_entity_events(self):
        customer = self.make_customer()
        dsl_resp = self.client.post("/api/dsl-services/", {
            "customer": customer.id, "dsl_package": "Broadband 8Mbps Unlimited",
            "msag": self.msag.id, "msag_card": "C04", "msag_port": "P12",
        })
        self.assertEqual(dsl_resp.status_code, status.HTTP_201_CREATED)
        pair_resp = self.client.post("/api/copper-pairs/", {
            "dsl_service": dsl_resp.data["id"], "pair_number": "214",
        })
        self.assertEqual(pair_resp.status_code, status.HTTP_201_CREATED)
        self.client.patch(f"/api/customers/{customer.id}/", {"contact_person": "M. Aslam"})

        resp = self.client.get(f"/api/customers/{customer.id}/history/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        entity_types = {row["entity_type"] for row in resp.data["results"]}
        self.assertEqual(entity_types, {"CUSTOMER", "DSL_SERVICE", "COPPER_PAIR"})
        # newest first
        timestamps = [row["created_at"] for row in resp.data["results"]]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))

    def test_activity_feed_filters_by_entity_type_and_action(self):
        customer = self.make_customer()
        self.client.patch(f"/api/customers/{customer.id}/", {"contact_person": "M. Aslam"})

        resp = self.client.get("/api/activity/?entity_type=CUSTOMER&action=UPDATED")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(all(r["entity_type"] == "CUSTOMER" and r["action"] == "UPDATED" for r in resp.data["results"]))

    def test_activity_feed_search(self):
        self.client.post("/api/customers/", {
            "name": "Govt. College of Technology", "address_line": "GOR-III, Lahore",
            "city": self.city.id, "phone_primary": "0559201351",
        })
        resp = self.client.get("/api/activity/?search=Govt. College")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(resp.data["count"], 1)

    def test_activity_log_is_read_only(self):
        create_resp = self.client.post("/api/customers/", {
            "name": "Govt. College of Technology", "address_line": "GOR-III, Lahore",
            "city": self.city.id, "phone_primary": "0559201351",
        })
        log = ActivityLog.objects.get(entity_type=ActivityLog.EntityType.CUSTOMER, entity_id=create_resp.data["id"])
        resp = self.client.patch(f"/api/activity/{log.id}/", {"summary": "tampered"})
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        resp = self.client.delete(f"/api/activity/{log.id}/")
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_activity_stats_endpoint(self):
        self.make_customer()
        resp = self.client.get("/api/activity/stats/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("total_events", resp.data)
        self.assertIn("daily_counts", resp.data)
        self.assertEqual(len(resp.data["daily_counts"]), 14)


class ComplaintTests(BaseAPITestCase):
    """Covers the fault/complaint tracking: lifecycle, auto-managed resolved_at,
    activity logging integration, and the open-complaint count/filter."""

    def test_create_complaint(self):
        customer = self.make_customer()
        resp = self.client.post("/api/complaints/", {
            "customer": customer.id, "fault_description": "No dial tone", "assigned_to": "Amjad Hussain",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data["status"], "OPEN")
        self.assertIsNone(resp.data["resolved_at"])

    def test_resolving_complaint_auto_sets_resolved_at(self):
        customer = self.make_customer()
        complaint = Complaint.objects.create(customer=customer, fault_description="No dial tone")
        self.assertIsNone(complaint.resolved_at)

        resp = self.client.patch(f"/api/complaints/{complaint.id}/", {"status": "RESOLVED"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(resp.data["resolved_at"])

    def test_reopening_complaint_clears_resolved_at(self):
        customer = self.make_customer()
        complaint = Complaint.objects.create(customer=customer, fault_description="No dial tone", status=Complaint.Status.RESOLVED)
        complaint.refresh_from_db()
        self.assertIsNotNone(complaint.resolved_at)

        resp = self.client.patch(f"/api/complaints/{complaint.id}/", {"status": "OPEN"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsNone(resp.data["resolved_at"])

    def test_open_complaint_count_on_customer_list(self):
        customer = self.make_customer()
        resp = self.client.get("/api/customers/")
        self.assertEqual(resp.data["results"][0]["open_complaint_count"], 0)

        self.client.post("/api/complaints/", {"customer": customer.id, "fault_description": "No dial tone"})
        resp = self.client.get("/api/customers/")
        self.assertEqual(resp.data["results"][0]["open_complaint_count"], 1)

    def test_open_complaint_count_excludes_resolved_and_irrelevant(self):
        customer = self.make_customer()
        Complaint.objects.create(customer=customer, fault_description="A", status=Complaint.Status.RESOLVED)
        Complaint.objects.create(customer=customer, fault_description="B", status=Complaint.Status.IRRELEVANT)
        Complaint.objects.create(customer=customer, fault_description="C", status=Complaint.Status.OPEN)
        Complaint.objects.create(customer=customer, fault_description="D", status=Complaint.Status.IN_PROGRESS)

        resp = self.client.get(f"/api/customers/{customer.id}/")
        self.assertEqual(resp.data["open_complaint_count"], 2)

    def test_has_open_complaint_filter(self):
        with_open = self.make_customer()
        without_open = self.make_customer(name="Other", phone_primary="999", user_id="u999")
        Complaint.objects.create(customer=with_open, fault_description="No dial tone")
        Complaint.objects.create(customer=without_open, fault_description="Fixed already", status=Complaint.Status.RESOLVED)

        resp = self.client.get("/api/customers/?has_open_complaint=true")
        ids = {r["id"] for r in resp.data["results"]}
        self.assertEqual(ids, {with_open.id})

    def test_complaint_lifecycle_is_logged_and_appears_in_customer_history(self):
        customer = self.make_customer()
        create_resp = self.client.post("/api/complaints/", {
            "customer": customer.id, "fault_description": "No dial tone",
        })
        complaint_id = create_resp.data["id"]
        self.client.patch(f"/api/complaints/{complaint_id}/", {"status": "RESOLVED", "resolution_notes": "Pair replaced"})

        resp = self.client.get(f"/api/customers/{customer.id}/history/")
        complaint_events = [e for e in resp.data["results"] if e["entity_type"] == "COMPLAINT"]
        self.assertEqual(len(complaint_events), 2)
        actions = {e["action"] for e in complaint_events}
        self.assertEqual(actions, {"CREATED", "UPDATED"})

    def test_complaint_filter_by_status(self):
        customer = self.make_customer()
        Complaint.objects.create(customer=customer, fault_description="A", status=Complaint.Status.OPEN)
        Complaint.objects.create(customer=customer, fault_description="B", status=Complaint.Status.RESOLVED)

        resp = self.client.get("/api/complaints/?status=OPEN")
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["fault_description"], "A")

    def test_complaint_filter_by_customer(self):
        c1 = self.make_customer()
        c2 = self.make_customer(name="Other", phone_primary="999", user_id="u999")
        Complaint.objects.create(customer=c1, fault_description="A")
        Complaint.objects.create(customer=c2, fault_description="B")

        resp = self.client.get(f"/api/complaints/?customer={c1.id}")
        self.assertEqual(resp.data["count"], 1)

    def test_dashboard_stats_include_complaint_data(self):
        customer = self.make_customer()
        Complaint.objects.create(customer=customer, fault_description="A", status=Complaint.Status.OPEN)

        resp = self.client.get("/api/dashboard/stats/")
        self.assertEqual(resp.data["open_complaints"], 1)
        self.assertIn({"status": "OPEN", "count": 1}, resp.data["complaint_status_breakdown"])
