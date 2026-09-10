<script>
  import { onMount } from "svelte";
  import { api } from "../lib/api.js";
  import ActivityTimeline from "./ActivityTimeline.svelte";
  import ChartView from "./Chart.svelte";

  let entries = [];
  let count = 0;
  let nextUrl = null;
  let prevUrl = null;
  let loading = true;
  let error = "";

  let entityType = "";
  let actionType = "";
  let search = "";

  let stats = null;
  let trendChartData = null;

  const ENTITY_OPTIONS = [
    { value: "CUSTOMER", label: "Customer" },
    { value: "DSL_SERVICE", label: "DSL Service" },
    { value: "COPPER_PAIR", label: "Copper Pair" },
  ];
  const ACTION_OPTIONS = [
    { value: "CREATED", label: "Created" },
    { value: "UPDATED", label: "Updated" },
    { value: "DELETED", label: "Deleted" },
  ];

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
        const res = await fetch(url, {
          headers: { Authorization: `Token ${localStorage.getItem("dsl_tracker_token")}` },
        });
        data = await res.json();
      } else {
        data = await api.listActivity({ entity_type: entityType, action: actionType, search });
      }
      entries = data.results;
      count = data.count;
      nextUrl = data.next;
      prevUrl = data.previous;
    } catch (e) {
      error = e.message || "Failed to load activity.";
    } finally {
      loading = false;
    }
  }

  async function loadStats() {
    try {
      stats = await api.getActivityStats();
      trendChartData = {
        labels: stats.daily_counts.map((d) =>
          new Date(d.date).toLocaleDateString(undefined, { month: "short", day: "numeric" })
        ),
        datasets: [
          {
            label: "Changes",
            data: stats.daily_counts.map((d) => d.count),
            borderColor: "#1b6f8a",
            backgroundColor: "rgba(27, 111, 138, 0.12)",
            fill: true,
            tension: 0.3,
            pointRadius: 2,
          },
        ],
      };
    } catch {
      // stats widgets are non-critical — feed still works without them
    }
  }

  onMount(() => {
    load();
    loadStats();
  });
</script>

<div class="activity-page">
  {#if stats}
    <div class="stats-row">
      <div class="stat-chip">
        <div class="stat-value">{stats.total_events}</div>
        <div class="stat-label">Total events</div>
      </div>
      {#each stats.action_breakdown as a}
        <div class="stat-chip">
          <div class="stat-value">{a.count}</div>
          <div class="stat-label">{a.action.charAt(0) + a.action.slice(1).toLowerCase()}</div>
        </div>
      {/each}
    </div>

    {#if trendChartData}
      <div class="card trend-card">
        <h3>Activity — last 14 days</h3>
        <ChartView
          type="line"
          data={trendChartData}
          height={180}
          options={{
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
          }}
        />
      </div>
    {/if}
  {/if}

  <div class="toolbar">
    <input
      type="search"
      inputmode="search"
      placeholder="Search activity..."
      bind:value={search}
      on:input={onSearchInput}
    />
    <select bind:value={entityType} on:change={() => load()}>
      <option value="">All record types</option>
      {#each ENTITY_OPTIONS as o}<option value={o.value}>{o.label}</option>{/each}
    </select>
    <select bind:value={actionType} on:change={() => load()}>
      <option value="">All actions</option>
      {#each ACTION_OPTIONS as o}<option value={o.value}>{o.label}</option>{/each}
    </select>
  </div>

  {#if error}<p class="error-text">{error}</p>{/if}

  <div class="card feed-card">
    {#if loading}
      <p class="muted">Loading...</p>
    {:else}
      <ActivityTimeline entries={entries} showCustomer emptyText="No activity matches these filters." />
    {/if}
  </div>

  {#if !loading && entries.length > 0}
    <div class="card pager-card">
      <div class="pager">
        <span class="muted small">{count} total event{count === 1 ? "" : "s"}</span>
        <div class="pager-btns">
          <button disabled={!prevUrl} on:click={() => load(prevUrl)}>← Prev</button>
          <button disabled={!nextUrl} on:click={() => load(nextUrl)}>Next →</button>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .activity-page {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .stats-row {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
  }
  .stat-chip {
    background: white;
    border-radius: 12px;
    box-shadow: 0 1px 4px rgba(18, 63, 82, 0.08);
    padding: 10px 16px;
    min-width: 100px;
  }
  .stat-value {
    font-size: 1.3rem;
    font-weight: 700;
    color: #123f52;
  }
  .stat-label {
    font-size: 0.72rem;
    color: #6b7683;
  }

  .trend-card h3 {
    margin: 0 0 10px;
    font-size: 0.9rem;
    color: #123f52;
  }

  .toolbar {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }
  .toolbar input[type="search"] {
    flex: 1;
    min-width: 200px;
  }

  .feed-card {
    padding: 8px 20px;
  }

  .pager-card {
    padding: 12px 16px;
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

  .muted {
    color: #6b7683;
  }
  .small {
    font-size: 0.78rem;
  }

  @media (max-width: 640px) {
    .toolbar {
      flex-direction: column;
      align-items: stretch;
    }
    .feed-card {
      padding: 4px 14px;
    }
  }
</style>
