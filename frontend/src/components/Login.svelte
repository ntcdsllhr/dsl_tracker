<script>
  import { createEventDispatcher } from "svelte";
  import { api, setToken } from "../lib/api.js";

  const dispatch = createEventDispatcher();

  let username = "";
  let password = "";
  let error = "";
  let loading = false;

  async function handleSubmit() {
    error = "";
    loading = true;
    try {
      const data = await api.login(username, password);
      setToken(data.token);
      dispatch("loggedIn");
    } catch (e) {
      error = "Invalid username or password.";
    } finally {
      loading = false;
    }
  }
</script>

<div class="login-card">
  <div class="login-logo">DT</div>
  <h2>Technician Login</h2>
  <p class="login-sub">Sign in to access DSL customer technical records</p>
  <form on:submit|preventDefault={handleSubmit}>
    <label>
      Username
      <input type="text" bind:value={username} autocomplete="username" required />
    </label>
    <label>
      Password
      <input type="password" bind:value={password} autocomplete="current-password" required />
    </label>
    {#if error}<p class="error-text">{error}</p>{/if}
    <button class="primary" type="submit" disabled={loading}>
      {loading ? "Signing in..." : "Sign in"}
    </button>
  </form>
</div>

<style>
  .login-card {
    width: min(340px, 100%);
    box-sizing: border-box;
    background: white;
    border-radius: 16px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    padding: 28px 24px;
  }
  .login-logo {
    width: 44px;
    height: 44px;
    border-radius: 11px;
    background: linear-gradient(135deg, #5ba7bf, #1b6f8a);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    margin-bottom: 14px;
  }
  h2 {
    margin: 0 0 4px;
    color: #123f52;
    font-size: 1.15rem;
  }
  .login-sub {
    margin: 0 0 18px;
    font-size: 0.82rem;
    color: #6b7683;
  }
  form {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  label {
    display: flex;
    flex-direction: column;
    gap: 5px;
    font-size: 0.85rem;
    font-weight: 600;
    color: #33414f;
  }
  button.primary {
    width: 100%;
    margin-top: 4px;
  }
</style>
