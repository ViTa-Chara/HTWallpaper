async function postForm(url, form) {
  const data = new FormData(form);
  const response = await fetch(url, { method: "POST", body: data });
  return response.json();
}

let debugModeEnabled = false;

function render(targetId, payload) {
  const target = document.getElementById(targetId);
  if (!target) {
    return;
  }
  if (!debugModeEnabled) {
    target.textContent = "";
    return;
  }
  target.textContent = JSON.stringify(payload, null, 2);
}

const uploadForm = document.getElementById("uploadForm");
const scheduleForm = document.getElementById("scheduleForm");
const applyForm = document.getElementById("applyForm");
const startupForm = document.getElementById("startupForm");
const settingsForm = document.getElementById("settingsForm");
const refreshVideos = document.getElementById("refreshVideos");
const videoList = document.getElementById("videoList");

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const result = await postForm("/api/upload", uploadForm);
  render("uploadResult", result);
  await loadVideos();
});

scheduleForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const result = await postForm("/api/schedule", scheduleForm);
  render("scheduleStatus", result);
});

document.getElementById("stopSchedule").addEventListener("click", async () => {
  const data = new FormData();
  data.append("enable", "false");
  const response = await fetch("/api/schedule", { method: "POST", body: data });
  const result = await response.json();
  render("scheduleStatus", result);
});

applyForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const result = await postForm("/api/apply", applyForm);
  render("applyStatus", result);
});

refreshVideos.addEventListener("click", async () => {
  await loadVideos();
});

startupForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const result = await postForm("/api/startup", startupForm);
  render("startupStatus", result);
});

settingsForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(settingsForm);
  ["multi_screen_enabled", "debug_mode"].forEach((name) => {
    const checkbox = settingsForm.querySelector(`input[name='${name}']`);
    if (checkbox) {
      data.set(name, checkbox.checked ? "true" : "false");
    }
  });
  const response = await fetch("/api/settings", { method: "POST", body: data });
  const result = await response.json();
  render("settingsStatus", result);
  await loadSettings();
});

document.getElementById("checkCompat").addEventListener("click", async () => {
  const response = await fetch("/api/status");
  const result = await response.json();
  render("compatResult", result.compat);
});

async function loadVideos() {
  const response = await fetch("/api/videos");
  const result = await response.json();
  videoList.innerHTML = "";
  (result.videos || []).forEach((item) => {
    const li = document.createElement("li");
    const span = document.createElement("span");
    span.textContent = item.name || item.path;
    const removeBtn = document.createElement("button");
    removeBtn.textContent = "删除";
    removeBtn.className = "secondary";
    removeBtn.addEventListener("click", async () => {
      const query = new URLSearchParams({ path: item.path });
      await fetch(`/api/videos?${query.toString()}`, { method: "DELETE" });
      await loadVideos();
    });
    li.appendChild(span);
    li.appendChild(removeBtn);
    videoList.appendChild(li);
  });
}

async function loadSettings() {
  const response = await fetch("/api/settings");
  const result = await response.json();
  debugModeEnabled = Boolean(result.debug_mode);
  if (result.video_dir) {
    const videoDirInput = document.querySelector("input[name='video_dir']");
    if (videoDirInput) {
      videoDirInput.value = result.video_dir;
    }
  }
  if (result.max_attempts) {
    const attemptsInput = document.querySelector("input[name='max_attempts']");
    if (attemptsInput) {
      attemptsInput.value = result.max_attempts;
    }
  }
  if (result.frame_limit) {
    document.querySelectorAll("input[name='max_frames']").forEach((input) => {
      input.value = result.frame_limit;
    });
    const settingsInput = document.querySelector("input[name='frame_limit']");
    if (settingsInput) {
      settingsInput.value = result.frame_limit;
    }
  }
  if (result.wallpaper_style) {
    document.querySelectorAll("select[name='style']").forEach((select) => {
      select.value = result.wallpaper_style;
    });
    const settingsSelect = document.querySelector("select[name='wallpaper_style']");
    if (settingsSelect) {
      settingsSelect.value = result.wallpaper_style;
    }
  }
  if (result.schedule_interval_minutes) {
    const scheduleIntervalInput = document.querySelector(
      "#scheduleForm input[name='interval_minutes']"
    );
    if (scheduleIntervalInput) {
      scheduleIntervalInput.value = result.schedule_interval_minutes;
    }
  }
  if (typeof result.multi_screen_enabled !== "undefined") {
    const multiScreenCheckbox = document.querySelector(
      "#settingsForm input[name='multi_screen_enabled']"
    );
    if (multiScreenCheckbox) {
      multiScreenCheckbox.checked = Boolean(result.multi_screen_enabled);
    }
  }
  if (result.multi_screen_mode) {
    const modeSelect = document.querySelector(
      "#settingsForm select[name='multi_screen_mode']"
    );
    if (modeSelect) {
      modeSelect.value = result.multi_screen_mode;
    }
  }
  if (result.span_layout) {
    const layoutSelect = document.querySelector(
      "#settingsForm select[name='span_layout']"
    );
    if (layoutSelect) {
      layoutSelect.value = result.span_layout;
    }
  }
  if (typeof result.debug_mode !== "undefined") {
    debugModeEnabled = Boolean(result.debug_mode);
    const debugCheckbox = document.querySelector(
      "#settingsForm input[name='debug_mode']"
    );
    if (debugCheckbox) {
      debugCheckbox.checked = debugModeEnabled;
    }
  }
}

loadVideos();
loadSettings();
