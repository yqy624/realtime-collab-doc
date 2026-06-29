<template>
  <router-view />
</template>

<style>
:root {
  color-scheme: light;
  --bg: #f5f7fb;
  --panel: #ffffff;
  --line: #dce3ef;
  --ink: #1f2937;
  --muted: #667085;
  --accent: #1368ce;
  --accent-soft: #eaf3ff;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-width: 320px;
  font-family: "Segoe UI", "PingFang SC", sans-serif;
  background:
    radial-gradient(circle at top left, #fef4d8 0, transparent 28%),
    radial-gradient(circle at top right, #dcefff 0, transparent 30%),
    var(--bg);
  color: var(--ink);
}

button,
input,
textarea {
  font: inherit;
}

a {
  color: inherit;
  text-decoration: none;
}
</style>
