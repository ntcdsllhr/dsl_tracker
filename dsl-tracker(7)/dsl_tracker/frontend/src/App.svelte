<script>
  import { onMount } from "svelte";
  import { getToken, clearToken } from "./lib/api.js";
  import Login from "./components/Login.svelte";
  import Dashboard from "./components/Dashboard.svelte";
  import CustomerList from "./components/CustomerList.svelte";
  import CustomerDetail from "./components/CustomerDetail.svelte";
  import Activity from "./components/Activity.svelte";

  let loggedIn = false;
  let checkedAuth = false;

  // page: 'dashboard' | 'customers'
  let page = "dashboard";
  // view: { name: 'list' } | { name: 'detail', id } | { name: 'new' }
  let view = { name: "list" };

  onMount(() => {
    loggedIn = !!getToken();
    checkedAuth = true;
  });

  function handleLoggedIn() {
    loggedIn = true;
  }

  function handleLogout() {
    clearToken();
    loggedIn = false;
    page = "dashboard";
    view = { name: "list" };
  }

  function goTo(p) {
    page = p;
    view = { name: "list" };
  }

  function openCustomer(id) {
    page = "customers";
    view = { name: "detail", id };
  }

  function openNew() {
    view = { name: "new" };
  }

  function backToList() {
    view = { name: "list" };
  }

  const NAV_ITEMS = [
    { key: "dashboard", label: "Dashboard", icon: "grid" },
    { key: "customers", label: "Customers", icon: "users" },
    { key: "activity", label: "Activity", icon: "activity" },
  ];
</script>

{#if !checkedAuth}
  <!-- avoid a login-screen flash while we check localStorage -->
{:else if !loggedIn}
  <div class="auth-shell">
    <Login on:loggedIn={handleLoggedIn} />
  </div>
{:else}
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark">DT</div>
        <div class="brand-text">
          <div class="brand-title">DSL Tracker</div>
          <div class="brand-sub">Field Technical Records</div>
        </div>
      </div>

      <nav>
        {#each NAV_ITEMS as item}
          <button
            class="nav-item"
            class:active={page === item.key}
            on:click={() => goTo(item.key)}
          >
            <span class="nav-icon">
              {#if item.icon === "grid"}
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="3" width="7" height="7" rx="1.5" />
                  <rect x="14" y="3" width="7" height="7" rx="1.5" />
                  <rect x="3" y="14" width="7" height="7" rx="1.5" />
                  <rect x="14" y="14" width="7" height="7" rx="1.5" />
                </svg>
              {:else if item.icon === "users"}
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="9" cy="8" r="3.2" />
                  <path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6" />
                  <circle cx="17" cy="8.5" r="2.6" />
                  <path d="M17 12c2.5 0 4.5 2.2 4.5 5" />
                </svg>
              {:else if item.icon === "activity"}
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M3 12h4l2.5-7 4 14L16 12h5" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
              {/if}
            </span>
            {item.label}
          </button>
        {/each}
      </nav>

      <button class="logout-btn" on:click={handleLogout}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
          <path d="M16 17l5-5-5-5" />
          <path d="M21 12H9" />
        </svg>
        Log out
      </button>
    </aside>

    <div class="content-area">
      <header class="topbar">
        <div class="topbar-brand-mobile">
          <div class="brand-mark small">DT</div>
          <span>DSL Tracker</span>
        </div>
        <h1>
          {#if page === "dashboard"}
            Dashboard
          {:else if page === "activity"}
            Activity &amp; Reporting
          {:else if view.name === "detail"}
            Customer Details
          {:else if view.name === "new"}
            New Customer
          {:else}
            Customers
          {/if}
        </h1>
        <button class="logout-btn logout-mobile" on:click={handleLogout} aria-label="Log out">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <path d="M16 17l5-5-5-5" />
            <path d="M21 12H9" />
          </svg>
        </button>
      </header>

      <main>
        {#if page === "dashboard"}
          <Dashboard />
        {:else if page === "activity"}
          <Activity />
        {:else if view.name === "list"}
          <CustomerList on:open={(e) => openCustomer(e.detail)} on:new={openNew} />
        {:else if view.name === "detail"}
          <CustomerDetail customerId={view.id} on:back={backToList} />
        {:else if view.name === "new"}
          <CustomerDetail customerId={null} on:back={backToList} />
        {/if}
      </main>
    </div>

    <nav class="bottom-nav">
      {#each NAV_ITEMS as item}
        <button
          class="bottom-nav-item"
          class:active={page === item.key}
          on:click={() => goTo(item.key)}
        >
          <span class="nav-icon">
            {#if item.icon === "grid"}
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="7" height="7" rx="1.5" />
                <rect x="14" y="3" width="7" height="7" rx="1.5" />
                <rect x="3" y="14" width="7" height="7" rx="1.5" />
                <rect x="14" y="14" width="7" height="7" rx="1.5" />
              </svg>
            {:else if item.icon === "users"}
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="9" cy="8" r="3.2" />
                <path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6" />
                <circle cx="17" cy="8.5" r="2.6" />
                <path d="M17 12c2.5 0 4.5 2.2 4.5 5" />
              </svg>
            {:else if item.icon === "activity"}
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 12h4l2.5-7 4 14L16 12h5" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            {/if}
          </span>
          <span class="bottom-nav-label">{item.label}</span>
        </button>
      {/each}
    </nav>
  </div>
{/if}

<style>
  :global(:root) {
    --ink: #123f52;
    --teal: #1b6f8a;
    --teal-dark: #0f2f3d;
    --teal-light: #5ba7bf;
    --bg: #f2f5f7;
    --card-shadow: 0 2px 10px rgba(18, 63, 82, 0.08);
  }

  :global(body) {
    margin: 0;
    font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg);
    color: #1b2430;
  }

  .auth-shell {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: radial-gradient(circle at top left, #1b6f8a 0%, #0f2f3d 65%);
  }

  .shell {
    display: flex;
    min-height: 100vh;
  }

  /* --- Sidebar --- */
  .sidebar {
    width: 232px;
    flex-shrink: 0;
    background: linear-gradient(180deg, #123f52 0%, #0c2a38 100%);
    color: #dceaf0;
    display: flex;
    flex-direction: column;
    padding: 22px 16px;
    position: sticky;
    top: 0;
    height: 100vh;
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0 4px 22px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    margin-bottom: 18px;
  }
  .brand-mark {
    width: 36px;
    height: 36px;
    border-radius: 9px;
    background: linear-gradient(135deg, #5ba7bf, #1b6f8a);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.85rem;
    color: white;
    flex-shrink: 0;
  }
  .brand-title {
    font-weight: 700;
    font-size: 0.95rem;
    color: white;
  }
  .brand-sub {
    font-size: 0.68rem;
    color: #9fc3d0;
  }

  nav {
    display: flex;
    flex-direction: column;
    gap: 4px;
    flex: 1;
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 10px;
    background: none;
    border: none;
    color: #bcd6df;
    text-align: left;
    padding: 10px 12px;
    border-radius: 8px;
    font-size: 0.88rem;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
  }
  .nav-item:hover {
    background: rgba(255, 255, 255, 0.06);
    color: white;
  }
  .nav-item.active {
    background: rgba(91, 167, 191, 0.22);
    color: white;
    font-weight: 600;
  }
  .nav-icon {
    width: 18px;
    height: 18px;
    display: inline-flex;
  }
  .nav-icon svg {
    width: 100%;
    height: 100%;
  }

  .logout-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    background: none;
    border: 1px solid rgba(255, 255, 255, 0.15);
    color: #bcd6df;
    padding: 9px 12px;
    border-radius: 8px;
    font-size: 0.82rem;
    cursor: pointer;
    transition: background 0.15s;
  }
  .logout-btn:hover {
    background: rgba(255, 255, 255, 0.08);
    color: white;
  }

  /* --- Content area --- */
  .content-area {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
  }

  .topbar {
    padding: 22px 32px 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }
  .topbar h1 {
    margin: 0;
    font-size: 1.3rem;
    color: var(--ink);
  }
  .topbar-brand-mobile {
    display: none;
    align-items: center;
    gap: 8px;
    font-weight: 700;
    color: var(--ink);
    font-size: 0.95rem;
  }
  .brand-mark.small {
    width: 26px;
    height: 26px;
    font-size: 0.68rem;
    border-radius: 7px;
  }
  .logout-mobile {
    display: none;
  }

  main {
    padding: 0 32px 40px;
  }

  /* --- Bottom tab bar (mobile only) --- */
  .bottom-nav {
    display: none;
  }

  /* --- Shared element styles used across child components --- */
  :global(button.primary) {
    background: linear-gradient(135deg, var(--teal-light), var(--teal));
    color: white;
    border: none;
    padding: 9px 18px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 0.88rem;
    font-weight: 600;
    box-shadow: 0 2px 8px rgba(27, 111, 138, 0.3);
    transition: transform 0.1s, box-shadow 0.15s;
  }
  :global(button.primary:hover) {
    box-shadow: 0 4px 14px rgba(27, 111, 138, 0.4);
    transform: translateY(-1px);
  }
  :global(button.primary:disabled) {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
  }
  :global(.link-btn) {
    background: none;
    border: none;
    color: var(--teal);
    cursor: pointer;
    font-size: 0.9rem;
    text-decoration: underline;
    padding: 0;
  }

  :global(input, select) {
    padding: 9px 11px;
    border: 1px solid #d5dee5;
    border-radius: 8px;
    font-size: 0.88rem;
    font-family: inherit;
    background: white;
    transition: border-color 0.15s, box-shadow 0.15s;
  }
  :global(input:focus, select:focus) {
    outline: none;
    border-color: var(--teal-light);
    box-shadow: 0 0 0 3px rgba(91, 167, 191, 0.18);
  }

  :global(.card) {
    background: white;
    border-radius: 14px;
    box-shadow: var(--card-shadow);
    padding: 20px 22px;
  }

  :global(.error-text) {
    color: #b3261e;
    font-size: 0.88rem;
  }

  :global(.status-pill) {
    display: inline-block;
    padding: 3px 11px;
    border-radius: 999px;
    font-size: 0.74rem;
    font-weight: 700;
    letter-spacing: 0.02em;
  }
  :global(.status-ACTIVE) { background: #dff3e4; color: #17703a; }
  :global(.status-FAULTY) { background: #fbe2e1; color: #a02622; }
  :global(.status-SUSPENDED) { background: #fdf1d6; color: #8a5a09; }
  :global(.status-DECOMMISSIONED) { background: #e6e8eb; color: #4b5563; }
  :global(.status-OPEN) { background: #fbe2e1; color: #a02622; }
  :global(.status-IN_PROGRESS) { background: #fdf1d6; color: #8a5a09; }
  :global(.status-RESOLVED) { background: #dff3e4; color: #17703a; }
  :global(.status-IRRELEVANT) { background: #e6e8eb; color: #4b5563; }

  /* ===================== Mobile (phones) ===================== */
  @media (max-width: 768px) {
    :global(html, body) {
      overflow-x: hidden;
    }

    .auth-shell {
      padding: 20px;
      box-sizing: border-box;
    }

    .shell {
      flex-direction: column;
    }

    /* Hide the desktop sidebar entirely on phones — replaced by bottom nav */
    .sidebar {
      display: none;
    }

    .content-area {
      width: 100%;
    }

    .topbar {
      padding: 16px 16px 10px;
      position: sticky;
      top: 0;
      background: var(--bg);
      z-index: 5;
    }
    .topbar h1 {
      font-size: 1.05rem;
      flex: 1;
      text-align: center;
    }
    .topbar-brand-mobile {
      display: none; /* title takes priority in the limited top-bar space */
    }
    .logout-mobile {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 8px;
      border-radius: 8px;
    }

    main {
      padding: 0 14px 84px; /* extra bottom padding clears the fixed bottom nav */
    }

    /* Bottom tab bar */
    .bottom-nav {
      display: flex;
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      background: linear-gradient(180deg, #123f52, #0c2a38);
      padding: 6px 10px calc(6px + env(safe-area-inset-bottom));
      z-index: 20;
      box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.18);
    }
    .bottom-nav-item {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 3px;
      background: none;
      border: none;
      color: #9fc3d0;
      padding: 8px 4px;
      border-radius: 10px;
      font-size: 0.68rem;
      cursor: pointer;
      min-height: 48px;
    }
    .bottom-nav-item .nav-icon {
      width: 22px;
      height: 22px;
    }
    .bottom-nav-item.active {
      color: white;
      background: rgba(91, 167, 191, 0.22);
    }
    .bottom-nav-label {
      font-weight: 600;
    }
  }

  @media (max-width: 380px) {
    .topbar h1 {
      font-size: 0.95rem;
    }
    main {
      padding: 0 10px 84px;
    }
  }

  @media (max-width: 768px) {
    /* iOS Safari auto-zooms on input focus if font-size < 16px */
    :global(input, select) {
      font-size: 16px;
    }
    :global(.card) {
      padding: 16px 16px;
      border-radius: 12px;
    }
  }
</style>
