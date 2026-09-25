<script>
  import { onMount } from "svelte";
  import { api } from "../lib/api.js";
  import ChartView from "./Chart.svelte";
  import ActivityTimeline from "./ActivityTimeline.svelte";

  let stats = null;
  let loading = true;
  let error = "";

  const PALETTE = {
    teal: "#1b6f8a",
    tealLight: "#5ba7bf",
    green: "#2f9e5a",
    amber: "#e0a531",
    red: "#d5564d",
    slate: "#8593a3",
    ink: "#123f52",
  };

  const STATUS_COLORS = {
    ACTIVE: PALETTE.green,
    FAULTY: PALETTE.red,
    SUSPENDED: PALETTE.amber,
    DECOMMISSIONED: PALETTE.slate,
  };

  const CONDITION_COLORS = {
    GOOD: PALETTE.green,
    DEGRADED: PALETTE.amber,
    FAULTY: PALETTE.red,
    UNKNOWN: PALETTE.slate,
  };

  let statusChartData = null;
  let msagChartData = null;
  let conditionChartData = null;

  async function load() {
    loading = true;
    error = "";
    try {
      stats = await api.getDashboardStats();

      statusChartData = {
        labels: stats.status_breakdown.map((r) => r.status),
        datasets: [
          {
            data: stats.status_breakdown.map((r) => r.count),
            backgroundColor: stats.status_breakdown.map((r) => STATUS_COLORS[r.status] || PALETTE.slate),
            borderWidth: 0,
          },
        ],
      };

      msagChartData = {
        labels: stats.customers_by_msag.map((r) => r.msag || "Unassigned"),
        datasets: [
          {
            label: "Customers",
            data: stats.customers_by_msag.map((r) => r.count),
            backgroundColor: PALETTE.teal,
            borderRadius: 6,
            maxBarThickness: 36,
          },
        ],
      };

      conditionChartData = {
        labels: stats.condition_breakdown.map((r) => r.condition),
        datasets: [
          {
            data: stats.condition_breakdown.map((r) => r.count),
            backgroundColor: stats.condition_breakdown.map(
              (r) => CONDITION_COLORS[r.condition] || PALETTE.slate
            ),
            borderWidth: 0,
          },
        ],
      };
    } catch (e) {
      error = e.message || "Failed to load dashboard data.";
    } finally {
      loading = false;
    }
  }

  onMount(load);

  $: faultyRate = stats && stats.total_dsl_services
    ? Math.round((stats.faulty_dsl_services / stats.total_dsl_services) * 100)
    : 0;
</script>

<div class="dashboard">
  {#if loading}
    <p class="muted">Loading dashboard...</p>
  {:else if error}
    <p class="error-text">{error}</p>
  {:else if stats}
    <div class="tiles">
      <div class="tile tile-teal">
        <div class="tile-value">{stats.total_customers}</div>
        <div class="tile-label">Total Customers</div>
      </div>
      <div class="tile tile-green">
        <div class="tile-value">{stats.active_customers}</div>
        <div class="tile-label">Active Customers</div>
      </div>
      <div class="tile tile-red">
        <div class="tile-value">{stats.faulty_dsl_services}</div>
        <div class="tile-label">Faulty DSL Lines</div>
        <div class="tile-sub">{faultyRate}% of all lines</div>
      </div>
      <div class="tile tile-amber">
        <div class="tile-value">{stats.total_copper_pairs}</div>
        <div class="tile-label">Copper Pairs Tracked</div>
      </div>
      <div class="tile tile-slate">
        <div class="tile-value">{stats.changes_last_7d}</div>
        <div class="tile-label">Changes (7 days)</div>
        <div class="tile-sub">{stats.new_customers_last_7d} new customer{stats.new_customers_last_7d === 1 ? "" : "s"}</div>
      </div>
    </div>

    <div class="chart-grid">
      <div class="card chart-card">
        <h3>DSL Line Status</h3>
        {#if statusChartData}
          <ChartView type="doughnut" data={statusChartData} height={220} />
        {/if}
      </div>

      <div class="card chart-card">
        <h3>Copper Pair Condition</h3>
        {#if conditionChartData}
          <ChartView type="doughnut" data={conditionChartData} height={220} />
        {/if}
      </div>

      <div class="card chart-card wide">
        <h3>Customers by MSAG</h3>
        {#if msagChartData}
          <ChartView
            type="bar"
            data={msagChartData}
            height={240}
            options={{
              plugins: { legend: { display: false } },
              scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
            }}
          />
        {/if}
      </div>
    </div>

    <div class="card capacity-card">
      <h3>Card Capacity (busiest cards)</h3>
      {#if stats.card_utilization.length === 0}
        <p class="muted">No ports assigned yet.</p>
      {:else}
        <ul class="capacity-list">
          {#each stats.card_utilization as c (c.msag + c.card)}
            <li class="capacity-row">
              <div class="capacity-label">
                <span class="capacity-msag">{c.msag}</span>
                <span class="muted">· Card {c.card}</span>
              </div>
              <div class="capacity-bar-track">
                <div
                  class="capacity-bar-fill"
                  class:capacity-warn={c.percent_full >= 75 && c.percent_full < 100}
                  class:capacity-full={c.percent_full >= 100}
                  style="width: {Math.min(c.percent_full, 100)}%"
                ></div>
              </div>
              <div class="capacity-count muted">{c.used_ports} / {c.capacity}</div>
            </li>
          {/each}
        </ul>
      {/if}
    </div>

    <div class="card activity-card">
      <h3>Recent Activity</h3>
      <ActivityTimeline entries={stats.recent_activity} showCustomer emptyText="No activity recorded yet." />
    </div>
  {/if}
</div>

<style>
  .dashboard {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .tiles {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 14px;
  }

  .tile {
    border-radius: 14px;
    padding: 18px 20px;
    color: white;
    box-shadow: 0 4px 14px rgba(20, 40, 60, 0.12);
    position: relative;
    overflow: hidden;
  }
  .tile-teal { background: linear-gradient(135deg, #1b6f8a, #123f52); }
  .tile-green { background: linear-gradient(135deg, #2f9e5a, #1c6e3d); }
  .tile-red { background: linear-gradient(135deg, #d5564d, #a02622); }
  .tile-amber { background: linear-gradient(135deg, #e0a531, #a97613); }
  .tile-slate { background: linear-gradient(135deg, #6b7f91, #384a5c); }

  .tile-value {
    font-size: 2rem;
    font-weight: 700;
    line-height: 1;
  }
  .tile-label {
    margin-top: 6px;
    font-size: 0.82rem;
    opacity: 0.9;
  }
  .tile-sub {
    margin-top: 4px;
    font-size: 0.72rem;
    opacity: 0.75;
  }

  .chart-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }
  .chart-card.wide {
    grid-column: span 2;
  }
  .chart-card h3 {
    margin: 0 0 12px;
    font-size: 0.95rem;
    color: #123f52;
  }

  .activity-card h3 {
    margin: 0 0 6px;
    font-size: 0.95rem;
    color: #123f52;
  }

  /* --- Card capacity widget --- */
  .capacity-card h3 {
    margin: 0 0 12px;
    font-size: 0.95rem;
    color: #123f52;
  }
  .capacity-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .capacity-row {
    display: grid;
    grid-template-columns: 130px 1fr 60px;
    align-items: center;
    gap: 10px;
  }
  .capacity-label {
    font-size: 0.82rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .capacity-msag {
    font-weight: 600;
    color: #123f52;
  }
  .capacity-bar-track {
    background: #eef1f4;
    border-radius: 999px;
    height: 8px;
    overflow: hidden;
  }
  .capacity-bar-fill {
    height: 100%;
    background: #2f9e5a;
    border-radius: 999px;
    transition: width 0.3s;
  }
  .capacity-bar-fill.capacity-warn {
    background: #e0a531;
  }
  .capacity-bar-fill.capacity-full {
    background: #d5564d;
  }
  .capacity-count {
    font-size: 0.78rem;
    text-align: right;
    white-space: nowrap;
  }

  .muted {
    color: #6b7683;
  }

  @media (max-width: 720px) {
    .tiles {
      grid-template-columns: repeat(2, 1fr);
    }
    .chart-grid {
      grid-template-columns: 1fr;
    }
    .chart-card.wide {
      grid-column: span 1;
    }
    .capacity-row {
      grid-template-columns: 100px 1fr 50px;
      gap: 8px;
    }
  }

  @media (max-width: 420px) {
    .dashboard {
      gap: 14px;
    }
    .tiles {
      gap: 10px;
    }
    .tile {
      padding: 14px 14px;
    }
    .tile-value {
      font-size: 1.6rem;
    }
    .tile-label {
      font-size: 0.72rem;
    }
    .chart-grid {
      gap: 10px;
    }
  }
</style>
