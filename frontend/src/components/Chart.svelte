<script>
  import { onMount, onDestroy } from "svelte";
  import Chart from "chart.js/auto";

  export let type = "bar"; // 'bar' | 'doughnut' | 'line'
  export let data;
  export let options = {};
  export let height = 220;

  let canvas;
  let chartInstance;
  let mounted = false;

  function render() {
    if (!canvas || !data) return;
    if (chartInstance) chartInstance.destroy();
    chartInstance = new Chart(canvas, {
      type,
      data,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: type === "doughnut", labels: { boxWidth: 12, font: { size: 11 } } },
        },
        ...options,
      },
    });
  }

  onMount(() => {
    mounted = true;
    render();
  });

  onDestroy(() => {
    if (chartInstance) chartInstance.destroy();
  });

  // Re-render whenever the data reference changes, after mount.
  $: if (mounted && data) {
    render();
  }
</script>

<div style="height: {height}px; position: relative;">
  <canvas bind:this={canvas}></canvas>
</div>
