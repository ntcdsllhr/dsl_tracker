<script>
  import { onMount } from "svelte";
  import { createEventDispatcher } from "svelte";
  import { api } from "../lib/api.js";

  const dispatch = createEventDispatcher();

  let results = [];
  let count = 0;
  let nextUrl = null;
  let prevUrl = null;
  let loading = false;
  let error = "";

  let search = "";
  let status = "";
  let cityId = "";
  let faultsOnly = false;
  let ordering = "name";

  const ORDER_OPTIONS = [
    { value: "name", label: "Name (A-Z)" },
    { value: "dsl_service__msag__code", label: "MSAG" },
    { value: "dsl_service__msag_port", label: "Port (low to high)" },
    { value: "-dsl_service__msag_port", label: "Port (high to low)" },
  ];
  let cities = [];

  const STATUS_OPTIONS = ["ACTIVE", "SUSPENDED", "FAULTY", "DECOMMISSIONED"];

  let searchTimer;
  function onSearchInput() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => load(), 350);
  }

  async function load(url) {
    loading = true;
    error = "";
    try {
      let data;
      if (url) {
        // paginated next/prev links come back as absolute API urls already
        const res = await fetch(url, {
          headers: { Authorization: `Token ${localStorage.getItem("dsl_tracker_token")}` },
        });
        data = await res.json();
      } else {
        data = await api.listCustomers({
          search, status, city: cityId, ordering,
          has_open_complaint: faultsOnly ? "true" : "",
        });
      }
      results = data.results;
      count = data.count;
      nextUrl = data.next;
      prevUrl = data.previous;
    } catch (e) {
      error = e.message || "Failed to load customers.";
    } finally {
      loading = false;
    }
  }

  async function loadCities() {
    try {
      const data = await api.listCities();
      cities = data.results ?? data;
    } catch {
      // non-fatal — filter dropdown just stays empty
    }
  }

  onMount(() => {
    load();
    loadCities();
  });
</script>

<div class="toolbar">
  <input
    type="search"
    inputmode="search"
    placeholder="Search name, phone, address, user ID..."
    bind:value={search}
    on:input={onSearchInput}
  />
  <div class="toolbar-row2">
    <select bind:value={ordering} on:change={() => load()}>
      {#each ORDER_OPTIONS as o}
        <option value={o.value}>Sort: {o.label}</option>
      {/each}
    </select>
    <select bind:value={status} on:change={() => load()}>
      <option value="">All statuses</option>
      {#each STATUS_OPTIONS as s}
        <option value={s}>{s}</option>
      {/each}
    </select>
    <select bind:value={cityId} on:change={() => load()}>
      <option value="">All cities</option>
      {#each cities as c}
        <option value={c.id}>{c.name}</option>
      {/each}
    </select>
    <button
      type="button"
      class="fault-toggle"
      class:active={faultsOnly}
      on:click={() => { faultsOnly = !faultsOnly; load(); }}
    >
      ⚠ Faults only
    </button>
  </div>
  <button class="primary new-btn" on:click={() => dispatch("new")}>+ New Customer</button>
</div>

{#if error}<p class="error-text">{error}</p>{/if}

{#if loading}
  <p class="muted loading-text">Loading...</p>
{:else if results.length === 0}
  <div class="card"><p class="muted">No customers found.</p></div>
{:else}
  <!-- Desktop / tablet: real table -->
  <div class="card table-card desktop-only">
    <table>
      <thead>
        <tr>
          <th>Name</th>
          <th>Phone</th>
          <th>MSAG / Port</th>
          <th>DSL Package</th>
          <th>Pair #</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {#each results as c (c.id)}
          <tr on:click={() => dispatch("open", c.id)}>
            <td>
              <div class="cust-name-row">
                <span class="cust-name">{c.name}</span>
                {#if c.open_complaint_count > 0}
                  <span class="fault-badge" title="{c.open_complaint_count} open fault(s)">⚠ {c.open_complaint_count}</span>
                {/if}
              </div>
              <div class="muted small">{c.department}</div>
            </td>
            <td>{c.phone_primary}</td>
            <td>
              {#if c.msag_code}
                <div>{c.msag_code}</div>
                <div class="muted small">Port {c.msag_port}</div>
              {:else}
                <span class="muted">—</span>
              {/if}
            </td>
            <td>{c.dsl_package ?? "—"}</td>
            <td>{c.pair_number ?? "—"}</td>
            <td>
              {#if c.dsl_status}
                <span class="status-pill status-{c.dsl_status}">{c.dsl_status}</span>
              {:else}
                <span class="muted">—</span>
              {/if}
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>

  <!-- Phones: tap-friendly card list -->
  <div class="card-list mobile-only">
    {#each results as c (c.id)}
      <button class="cust-card" on:click={() => dispatch("open", c.id)}>
        <div class="cust-card-top">
          <div>
            <div class="cust-name-row">
              <span class="cust-name">{c.name}</span>
              {#if c.open_complaint_count > 0}
                <span class="fault-badge" title="{c.open_complaint_count} open fault(s)">⚠ {c.open_complaint_count}</span>
              {/if}
            </div>
            <div class="muted small">{c.department}</div>
          </div>
          {#if c.dsl_status}
            <span class="status-pill status-{c.dsl_status}">{c.dsl_status}</span>
          {/if}
        </div>
        <div class="cust-card-rows">
          <div class="cust-card-row">
            <span class="muted small">Phone</span>
            <span>{c.phone_primary}</span>
          </div>
          <div class="cust-card-row">
            <span class="muted small">MSAG</span>
            <span>{c.msag_code ?? "—"}</span>
          </div>
          <div class="cust-card-row">
            <span class="muted small">Port</span>
            <span>{c.msag_port ?? "—"}</span>
          </div>
          <div class="cust-card-row">
            <span class="muted small">DSL Package</span>
            <span>{c.dsl_package ?? "—"}</span>
          </div>
          <div class="cust-card-row">
            <span class="muted small">Pair #</span>
            <span>{c.pair_number ?? "—"}</span>
          </div>
        </div>
      </button>
    {/each}
  </div>

  <div class="card pager-card">
    <div class="pager">
      <span class="muted small">{count} total record{count === 1 ? "" : "s"}</span>
      <div class="pager-btns">
        <button disabled={!prevUrl} on:click={() => load(prevUrl)}>← Prev</button>
        <button disabled={!nextUrl} on:click={() => load(nextUrl)}>Next →</button>
      </div>
    </div>
  </div>
{/if}

<style>
  .toolbar {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 16px;
    align-items: center;
  }
  .toolbar input[type="search"] {
    flex: 1;
    min-width: 220px;
  }
  .toolbar-row2 {
    display: flex;
    gap: 10px;
  }

  .fault-toggle {
    display: flex;
    align-items: center;
    gap: 5px;
    background: white;
    border: 1px solid #d5dee5;
    color: #6b7683;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 0.85rem;
    cursor: pointer;
    white-space: nowrap;
    transition: background 0.15s, border-color 0.15s, color 0.15s;
  }
  .fault-toggle.active {
    background: #fbe5e4;
    border-color: #d5564d;
    color: #a02622;
    font-weight: 600;
  }

  .loading-text {
    padding: 6px 2px;
  }

  .table-card {
    padding: 0;
    overflow: hidden;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  thead th {
    text-align: left;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #8593a3;
    font-weight: 700;
    padding: 14px 16px;
    border-bottom: 1px solid #eef1f4;
    background: #fafcfd;
  }

  tbody tr {
    cursor: pointer;
    border-bottom: 1px solid #eef1f4;
    transition: background 0.12s;
  }
  tbody tr:last-child {
    border-bottom: none;
  }
  tbody tr:hover {
    background: #f0f8fa;
  }
  tbody td {
    padding: 13px 16px;
    font-size: 0.89rem;
  }

  .cust-name-row {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .cust-name {
    font-weight: 600;
  }
  .fault-badge {
    display: inline-flex;
    align-items: center;
    background: #fbe2e1;
    color: #a02622;
    font-size: 0.68rem;
    font-weight: 700;
    padding: 1px 7px;
    border-radius: 999px;
    flex-shrink: 0;
  }
  .muted {
    color: #6b7683;
  }
  .small {
    font-size: 0.78rem;
  }

  .pager-card {
    padding: 12px 16px;
    margin-top: 12px;
  }
  .pager {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .pager-btns {
    display: flex;
    gap: 8px;
  }
  .pager-btns button {
    border: 1px solid #cbd5de;
    background: white;
    border-radius: 6px;
    padding: 6px 12px;
    cursor: pointer;
    font-size: 0.85rem;
  }
  .pager-btns button:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  /* --- Mobile card list (hidden on desktop) --- */
  .mobile-only {
    display: none;
  }

  .card-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .cust-card {
    display: block;
    width: 100%;
    text-align: left;
    background: white;
    border: none;
    border-radius: 12px;
    box-shadow: 0 1px 4px rgba(18, 63, 82, 0.08);
    padding: 14px 16px;
    cursor: pointer;
    font-family: inherit;
    -webkit-tap-highlight-color: rgba(27, 111, 138, 0.15);
  }
  .cust-card:active {
    background: #f0f8fa;
  }

  .cust-card-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 10px;
  }

  .cust-card-rows {
    display: flex;
    flex-direction: column;
    gap: 6px;
    border-top: 1px solid #eef1f4;
    padding-top: 8px;
  }
  .cust-card-row {
    display: flex;
    justify-content: space-between;
    font-size: 0.86rem;
  }

  @media (max-width: 768px) {
    .desktop-only {
      display: none;
    }
    .mobile-only {
      display: flex;
    }

    .toolbar {
      flex-direction: column;
      align-items: stretch;
    }
    .toolbar-row2 {
      width: 100%;
      flex-wrap: wrap;
    }
    .toolbar-row2 select {
      flex: 1;
      min-width: 0;
    }
    .fault-toggle {
      flex: 1 1 100%;
      justify-content: center;
    }
    .new-btn {
      width: 100%;
    }

    .pager-card {
      position: sticky;
      bottom: 78px; /* clears the fixed bottom nav */
      box-shadow: 0 -2px 10px rgba(18, 63, 82, 0.1);
    }
  }
</style>
