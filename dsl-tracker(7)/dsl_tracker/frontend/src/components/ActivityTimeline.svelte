<script>
  export let entries = [];
  export let emptyText = "No activity yet.";
  export let showCustomer = false;

  const ACTION_META = {
    CREATED: { color: "#2f9e5a", bg: "#e4f5e9", label: "Created" },
    UPDATED: { color: "#e0a531", bg: "#fdf3dd", label: "Updated" },
    DELETED: { color: "#d5564d", bg: "#fbe5e4", label: "Deleted" },
  };

  function formatTime(iso) {
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now - d;
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return "just now";
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `${diffHr}h ago`;
    const diffDay = Math.floor(diffHr / 24);
    if (diffDay < 7) return `${diffDay}d ago`;
    return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  }

  let expanded = {};
  function toggle(id) {
    expanded = { ...expanded, [id]: !expanded[id] };
  }
</script>

{#if entries.length === 0}
  <p class="muted empty">{emptyText}</p>
{:else}
  <ul class="timeline">
    {#each entries as entry (entry.id)}
      {@const meta = ACTION_META[entry.action] || ACTION_META.UPDATED}
      {@const hasChanges = entry.changes && Object.keys(entry.changes).length > 0}
      <li class="entry">
        <span class="dot" style="background:{meta.color}"></span>
        <div class="entry-body">
          <div class="entry-top">
            <span class="action-pill" style="color:{meta.color}; background:{meta.bg}">{meta.label}</span>
            <span class="entity-label">{entry.entity_type_display}</span>
            {#if showCustomer}
              <span class="muted">· {entry.customer_name}</span>
            {/if}
            <span class="muted time">{formatTime(entry.created_at)}</span>
          </div>
          <p class="summary">{entry.summary}</p>
          {#if hasChanges}
            <button class="diff-toggle" on:click={() => toggle(entry.id)}>
              {expanded[entry.id] ? "Hide details" : `View ${Object.keys(entry.changes).length} field change${Object.keys(entry.changes).length === 1 ? "" : "s"}`}
            </button>
            {#if expanded[entry.id]}
              <table class="diff-table">
                <tbody>
                  {#each Object.entries(entry.changes) as [field, delta]}
                    <tr>
                      <td class="diff-field">{field.replace(/_/g, " ")}</td>
                      <td class="diff-old">{delta.old ?? "—"}</td>
                      <td class="diff-arrow">→</td>
                      <td class="diff-new">{delta.new ?? "—"}</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            {/if}
          {/if}
          {#if entry.actor_username_snapshot}
            <div class="muted actor">by {entry.actor_username_snapshot}</div>
          {/if}
        </div>
      </li>
    {/each}
  </ul>
{/if}

<style>
  .empty {
    padding: 10px 2px;
  }

  .timeline {
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .entry {
    display: flex;
    gap: 12px;
    padding: 12px 0;
    border-bottom: 1px solid #eef1f4;
  }
  .entry:last-child {
    border-bottom: none;
  }

  .dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    margin-top: 6px;
    flex-shrink: 0;
  }

  .entry-body {
    flex: 1;
    min-width: 0;
  }

  .entry-top {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 4px;
  }

  .action-pill {
    font-size: 0.68rem;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 999px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  .entity-label {
    font-size: 0.78rem;
    font-weight: 600;
    color: #33414f;
  }

  .time {
    margin-left: auto;
    font-size: 0.75rem;
  }

  .summary {
    margin: 0;
    font-size: 0.88rem;
    color: #1b2430;
    line-height: 1.4;
  }

  .diff-toggle {
    background: none;
    border: none;
    color: #1b6f8a;
    font-size: 0.78rem;
    cursor: pointer;
    padding: 4px 0;
    text-decoration: underline;
  }

  .diff-table {
    margin-top: 6px;
    border-collapse: collapse;
    font-size: 0.8rem;
    width: 100%;
  }
  .diff-table td {
    padding: 3px 6px 3px 0;
    vertical-align: top;
  }
  .diff-field {
    text-transform: capitalize;
    color: #6b7683;
    white-space: nowrap;
  }
  .diff-old {
    color: #a02622;
    text-decoration: line-through;
    opacity: 0.75;
  }
  .diff-arrow {
    color: #8593a3;
    padding: 0 4px;
  }
  .diff-new {
    color: #17703a;
    font-weight: 600;
  }

  .actor {
    margin-top: 4px;
    font-size: 0.74rem;
  }

  .muted {
    color: #6b7683;
  }
</style>
