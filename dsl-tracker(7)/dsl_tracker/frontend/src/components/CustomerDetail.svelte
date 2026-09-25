<script>
  import { onMount } from "svelte";
  import { createEventDispatcher } from "svelte";
  import { api } from "../lib/api.js";
  import ActivityTimeline from "./ActivityTimeline.svelte";

  export let customerId = null; // null => creating a new customer

  const dispatch = createEventDispatcher();
  const isNew = customerId === null;

  const STATUS_OPTIONS = ["ACTIVE", "SUSPENDED", "FAULTY", "DECOMMISSIONED"];
  const TECH_OPTIONS = ["ADSL2+", "VDSL2", "SHDSL"];
  const CONDITION_OPTIONS = ["GOOD", "DEGRADED", "FAULTY", "UNKNOWN"];
  const COMPLAINT_STATUS_OPTIONS = ["OPEN", "IN_PROGRESS", "RESOLVED", "IRRELEVANT"];

  let loading = !isNew;
  let saving = false;
  let error = "";
  let notice = "";

  let history = [];
  let historyLoading = false;

  let complaints = [];
  let complaintsLoading = false;
  let complaintSaving = {}; // { [complaintId]: bool }
  let newComplaint = { fault_description: "", assigned_to: "" };
  let addingComplaint = false;

  let cities = [];
  let msags = [];

  // Customer form fields
  let customer = {
    name: "",
    department: "",
    subscriber_type: "GOV",
    address_line: "",
    city: "",
    postal_code: "",
    contact_person: "",
    phone_primary: "",
    phone_secondary: "",
    email: "",
    user_id: "",
    tax_code: "",
    dept_code: "",
    is_active: true,
  };

  // Nested DSL service + copper pair (only present once the customer exists)
  let dslService = null; // full nested object from detail endpoint, or null
  let copperPair = null;

  // Editable DSL/pair form state (separate from the read model so Save is explicit)
  let dslForm = {
    dsl_package: "",
    technology: "ADSL2+",
    operator: "",
    msag: "",
    msag_card: "",
    msag_port: "",
    ip_address: "",
    modem_serial: "",
    status: "ACTIVE",
    status_reason: "",
  };

  let pairForm = {
    cabinet_code: "",
    pair_number: "",
    binder_group: "",
    distribution_point: "",
    cable_length_meters: "",
    condition: "UNKNOWN",
    notes: "",
  };

  async function loadLookups() {
    try {
      const [cityData, msagData] = await Promise.all([api.listCities(), api.listMsags()]);
      cities = cityData.results ?? cityData;
      msags = msagData.results ?? msagData;
    } catch {
      // filter/lookup dropdowns just stay empty; not fatal
    }
  }

  async function loadCustomer() {
    loading = true;
    error = "";
    try {
      const data = await api.getCustomer(customerId);
      customer = {
        name: data.name,
        department: data.department,
        subscriber_type: data.subscriber_type,
        address_line: data.address_line,
        city: data.city,
        postal_code: data.postal_code,
        contact_person: data.contact_person,
        phone_primary: data.phone_primary,
        phone_secondary: data.phone_secondary,
        email: data.email,
        user_id: data.user_id,
        tax_code: data.tax_code,
        dept_code: data.dept_code,
        is_active: data.is_active,
      };
      dslService = data.dsl_service;
      if (dslService) {
        dslForm = {
          dsl_package: dslService.dsl_package,
          technology: dslService.technology,
          operator: dslService.operator,
          msag: dslService.msag,
          msag_card: dslService.msag_card,
          msag_port: dslService.msag_port,
          ip_address: dslService.ip_address ?? "",
          modem_serial: dslService.modem_serial,
          status: dslService.status,
          status_reason: dslService.status_reason,
        };
        copperPair = dslService.copper_pair;
        if (copperPair) {
          pairForm = {
            cabinet_code: copperPair.cabinet_code,
            pair_number: copperPair.pair_number,
            binder_group: copperPair.binder_group,
            distribution_point: copperPair.distribution_point,
            cable_length_meters: copperPair.cable_length_meters ?? "",
            condition: copperPair.condition,
            notes: copperPair.notes,
          };
        }
      }
    } catch (e) {
      error = e.message || "Failed to load customer.";
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    loadLookups();
    if (!isNew) {
      loadCustomer();
      loadHistory();
      loadComplaints();
    }
  });

  async function loadHistory() {
    historyLoading = true;
    try {
      const data = await api.getCustomerHistory(customerId);
      history = data.results ?? data;
    } catch {
      // history is supplementary — don't block the rest of the page on it
    } finally {
      historyLoading = false;
    }
  }

  async function loadComplaints() {
    complaintsLoading = true;
    try {
      const data = await api.listComplaints({ customer: customerId });
      complaints = data.results ?? data;
    } catch {
      // non-fatal — the rest of the page still works without it
    } finally {
      complaintsLoading = false;
    }
  }

  async function addComplaint() {
    if (!newComplaint.fault_description.trim()) return;
    addingComplaint = true;
    error = "";
    try {
      await api.createComplaint({
        customer: customerId,
        fault_description: newComplaint.fault_description.trim(),
        assigned_to: newComplaint.assigned_to.trim(),
      });
      newComplaint = { fault_description: "", assigned_to: "" };
      await loadComplaints();
      await loadHistory();
    } catch (e) {
      error = e.message || "Failed to report fault.";
    } finally {
      addingComplaint = false;
    }
  }

  async function saveComplaint(complaint) {
    complaintSaving = { ...complaintSaving, [complaint.id]: true };
    error = "";
    try {
      await api.updateComplaint(complaint.id, {
        status: complaint.status,
        assigned_to: complaint.assigned_to,
        resolution_notes: complaint.resolution_notes,
      });
      await loadComplaints();
      await loadHistory();
    } catch (e) {
      error = e.message || "Failed to update complaint.";
    } finally {
      complaintSaving = { ...complaintSaving, [complaint.id]: false };
    }
  }

  async function saveCustomer() {
    saving = true;
    error = "";
    notice = "";
    try {
      if (isNew) {
        const created = await api.createCustomer(customer);
        customerId = created.id;
        notice = "Customer created. You can now add DSL service details below.";
        await loadCustomer();
        await loadHistory();
      } else {
        await api.updateCustomer(customerId, customer);
        notice = "Customer details saved.";
        await loadHistory();
      }
    } catch (e) {
      error = e.message || "Failed to save customer.";
    } finally {
      saving = false;
    }
  }

  async function saveDslService() {
    if (!customerId) {
      error = "Save the customer record first.";
      return;
    }
    saving = true;
    error = "";
    notice = "";
    try {
      const body = { ...dslForm, customer: customerId, ip_address: dslForm.ip_address || null };
      if (dslService) {
        await api.updateDslService(dslService.id, body);
      } else {
        await api.createDslService(body);
      }
      notice = "DSL service details saved.";
      await loadCustomer();
      await loadHistory();
    } catch (e) {
      error = e.message || "Failed to save DSL service.";
    } finally {
      saving = false;
    }
  }

  async function saveCopperPair() {
    if (!dslService) {
      error = "Save DSL service details first.";
      return;
    }
    saving = true;
    error = "";
    notice = "";
    try {
      const body = {
        ...pairForm,
        dsl_service: dslService.id,
        cable_length_meters: pairForm.cable_length_meters || null,
      };
      if (copperPair) {
        await api.updateCopperPair(copperPair.id, body);
      } else {
        await api.createCopperPair(body);
      }
      notice = "Copper pair details saved.";
      await loadCustomer();
      await loadHistory();
    } catch (e) {
      error = e.message || "Failed to save copper pair.";
    } finally {
      saving = false;
    }
  }

  async function deleteCustomer() {
    if (!confirm(`Delete "${customer.name}"? This cannot be undone.`)) return;
    saving = true;
    try {
      await api.deleteCustomer(customerId);
      dispatch("back");
    } catch (e) {
      error = e.message || "Failed to delete customer.";
    } finally {
      saving = false;
    }
  }
</script>

<button class="link-btn back-btn" on:click={() => dispatch("back")}>← Back to list</button>

{#if loading}
  <p class="muted">Loading...</p>
{:else}
  {#if error}<p class="error-text">{error}</p>{/if}
  {#if notice}<p class="notice-text">{notice}</p>{/if}

  <section class="card">
    <h2>Customer</h2>
    <div class="grid">
      <label>Name<input bind:value={customer.name} required /></label>
      <label>Department<input bind:value={customer.department} /></label>
      <label>
        Subscriber type
        <select bind:value={customer.subscriber_type}>
          <option value="GOV">Government</option>
          <option value="SEMI_GOV">Semi-Government</option>
        </select>
      </label>
      <label class="span2">Address<input bind:value={customer.address_line} required /></label>
      <label>
        City
        <select bind:value={customer.city}>
          <option value="">Select city</option>
          {#each cities as c}<option value={c.id}>{c.name}</option>{/each}
        </select>
      </label>
      <label>Postal code<input bind:value={customer.postal_code} /></label>
      <label>Contact person<input bind:value={customer.contact_person} /></label>
      <label>Primary phone<input bind:value={customer.phone_primary} required /></label>
      <label>Secondary phone<input bind:value={customer.phone_secondary} /></label>
      <label>Email<input type="email" bind:value={customer.email} /></label>
      <label>User ID<input bind:value={customer.user_id} /></label>
      <label>Tax code<input bind:value={customer.tax_code} /></label>
      <label>Dept code<input bind:value={customer.dept_code} /></label>
      <label class="checkbox-label">
        <input type="checkbox" bind:checked={customer.is_active} /> Active
      </label>
    </div>
    <div class="actions">
      <button class="primary" on:click={saveCustomer} disabled={saving}>
        {saving ? "Saving..." : isNew ? "Create customer" : "Save customer"}
      </button>
      {#if !isNew}
        <button class="danger" on:click={deleteCustomer} disabled={saving}>Delete</button>
      {/if}
    </div>
  </section>

  {#if customerId}
    <section class="card">
      <h2>DSL Service</h2>
      <div class="grid">
        <label>DSL package<input bind:value={dslForm.dsl_package} /></label>
        <label>
          Technology
          <select bind:value={dslForm.technology}>
            {#each TECH_OPTIONS as t}<option value={t}>{t}</option>{/each}
          </select>
        </label>
        <label>Operator<input bind:value={dslForm.operator} /></label>
        <label>
          MSAG
          <select bind:value={dslForm.msag}>
            <option value="">Select MSAG</option>
            {#each msags as m}<option value={m.id}>{m.code}</option>{/each}
          </select>
        </label>
        <label>MSAG card<input bind:value={dslForm.msag_card} /></label>
        <label>
          MSAG port (0-63)
          <input type="number" min="0" max="63" bind:value={dslForm.msag_port} placeholder="e.g. 12" />
        </label>
        <label>IP address<input bind:value={dslForm.ip_address} placeholder="e.g. 10.20.30.40" /></label>
        <label>Modem serial<input bind:value={dslForm.modem_serial} /></label>
        <label>
          Status
          <select bind:value={dslForm.status}>
            {#each STATUS_OPTIONS as s}<option value={s}>{s}</option>{/each}
          </select>
        </label>
        <label class="span2">Status reason<input bind:value={dslForm.status_reason} /></label>
      </div>
      <div class="actions">
        <button class="primary" on:click={saveDslService} disabled={saving}>
          {saving ? "Saving..." : dslService ? "Save DSL service" : "Add DSL service"}
        </button>
      </div>
    </section>
  {/if}

  {#if dslService}
    <section class="card">
      <h2>Copper Pair</h2>
      <div class="grid">
        <label>Cabinet code<input bind:value={pairForm.cabinet_code} /></label>
        <label>Pair number<input bind:value={pairForm.pair_number} /></label>
        <label>Binder group<input bind:value={pairForm.binder_group} /></label>
        <label>Distribution point<input bind:value={pairForm.distribution_point} /></label>
        <label>Cable length (m)<input type="number" bind:value={pairForm.cable_length_meters} /></label>
        <label>
          Condition
          <select bind:value={pairForm.condition}>
            {#each CONDITION_OPTIONS as c}<option value={c}>{c}</option>{/each}
          </select>
        </label>
        <label class="span2">Notes<input bind:value={pairForm.notes} /></label>
      </div>
      <div class="actions">
        <button class="primary" on:click={saveCopperPair} disabled={saving}>
          {saving ? "Saving..." : copperPair ? "Save copper pair" : "Add copper pair"}
        </button>
      </div>
    </section>
  {/if}

  {#if customerId}
    <section class="card">
      <h2>Fault / Complaint History</h2>

      <div class="new-complaint">
        <input
          type="text"
          placeholder="Describe the fault (e.g. 'No dial tone', 'DSL not syncing')"
          bind:value={newComplaint.fault_description}
        />
        <input
          type="text"
          placeholder="Assign to (optional)"
          bind:value={newComplaint.assigned_to}
        />
        <button class="primary" on:click={addComplaint} disabled={addingComplaint || !newComplaint.fault_description.trim()}>
          {addingComplaint ? "Reporting..." : "Report Fault"}
        </button>
      </div>

      {#if complaintsLoading}
        <p class="muted">Loading fault history...</p>
      {:else if complaints.length === 0}
        <p class="muted">No faults reported for this customer.</p>
      {:else}
        <ul class="complaint-list">
          {#each complaints as c (c.id)}
            <li class="complaint-row">
              <div class="complaint-top">
                <span class="status-pill status-{c.status}">
                  {c.status_display}
                </span>
                <span class="complaint-desc">{c.fault_description}</span>
              </div>
              <div class="complaint-meta muted small">
                Reported {new Date(c.reported_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}
                {#if c.resolved_at}
                  · Resolved {new Date(c.resolved_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}
                {/if}
              </div>
              <div class="complaint-edit">
                <select bind:value={c.status}>
                  {#each COMPLAINT_STATUS_OPTIONS as s}<option value={s}>{s.replace("_", " ")}</option>{/each}
                </select>
                <input type="text" placeholder="Assigned to" bind:value={c.assigned_to} />
                <input type="text" placeholder="Resolution notes" bind:value={c.resolution_notes} />
                <button on:click={() => saveComplaint(c)} disabled={complaintSaving[c.id]}>
                  {complaintSaving[c.id] ? "Saving..." : "Update"}
                </button>
              </div>
            </li>
          {/each}
        </ul>
      {/if}
    </section>
  {/if}

  {#if customerId}
    <section class="card">
      <h2>History</h2>
      {#if historyLoading}
        <p class="muted">Loading history...</p>
      {:else}
        <ActivityTimeline entries={history} emptyText="No changes recorded yet." />
      {/if}
    </section>
  {/if}
{/if}

<style>
  .back-btn {
    display: inline-block;
    margin-bottom: 14px;
  }
  section.card {
    margin-bottom: 18px;
  }
  h2 {
    font-size: 1.05rem;
    margin: 0 0 14px;
    color: #123f52;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px 16px;
  }
  .span2 {
    grid-column: span 2;
  }
  label {
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 0.82rem;
    font-weight: 600;
    color: #33414f;
  }
  .checkbox-label {
    flex-direction: row;
    align-items: center;
    gap: 8px;
  }
  .actions {
    margin-top: 16px;
    display: flex;
    gap: 10px;
  }
  button.danger {
    background: white;
    border: 1px solid #c94b43;
    color: #c94b43;
    padding: 8px 16px;
    border-radius: 6px;
    cursor: pointer;
  }
  .notice-text {
    color: #17703a;
    font-size: 0.88rem;
  }
  .muted {
    color: #6b7683;
  }
  .small {
    font-size: 0.78rem;
  }

  /* --- Fault / Complaint History --- */
  .new-complaint {
    display: flex;
    gap: 10px;
    margin-bottom: 16px;
    flex-wrap: wrap;
  }
  .new-complaint input[type="text"]:first-child {
    flex: 2;
    min-width: 220px;
  }
  .new-complaint input[type="text"]:nth-child(2) {
    flex: 1;
    min-width: 140px;
  }

  .complaint-list {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  .complaint-row {
    padding: 12px 0;
    border-bottom: 1px solid #eef1f4;
  }
  .complaint-row:last-child {
    border-bottom: none;
  }
  .complaint-top {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 4px;
  }
  .complaint-desc {
    font-weight: 600;
    font-size: 0.9rem;
  }
  .complaint-meta {
    margin-bottom: 8px;
  }
  .complaint-edit {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    align-items: center;
  }
  .complaint-edit select {
    flex-shrink: 0;
  }
  .complaint-edit input {
    flex: 1;
    min-width: 130px;
  }
  .complaint-edit button {
    border: 1px solid #cbd5de;
    background: white;
    border-radius: 6px;
    padding: 8px 14px;
    cursor: pointer;
    font-size: 0.85rem;
    flex-shrink: 0;
  }
  .complaint-edit button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  @media (max-width: 640px) {
    .grid {
      grid-template-columns: 1fr;
    }
    .span2 {
      grid-column: span 1;
    }
    .actions {
      flex-direction: column;
    }
    .actions button {
      width: 100%;
    }
    section.card {
      padding: 16px 16px;
    }
    .new-complaint {
      flex-direction: column;
    }
    .new-complaint button {
      width: 100%;
    }
    .complaint-edit {
      flex-direction: column;
      align-items: stretch;
    }
    .complaint-edit button {
      width: 100%;
    }
  }
</style>
