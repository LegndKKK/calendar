"use strict";

const $ = (selector) => document.querySelector(selector);

const els = {
  monthLabel: $("#monthLabel"),
  prevMonth: $("#prevMonth"),
  nextMonth: $("#nextMonth"),
  todayBtn: $("#todayBtn"),
  settingsBtn: $("#settingsBtn"),
  modeBadge: $("#modeBadge"),
  calendarViewBtn: $("#calendarViewBtn"),
  interviewViewBtn: $("#interviewViewBtn"),
  calendarView: $("#calendarView"),
  interviewView: $("#interviewView"),
  monthNav: $("#monthNav"),
  parseForm: $("#parseForm"),
  nlInput: $("#nlInput"),
  parseBtn: $("#parseBtn"),
  preview: $("#preview"),
  calendarGrid: $("#calendarGrid"),
  selectedDateLabel: $("#selectedDateLabel"),
  addBtn: $("#addBtn"),
  emptyAddBtn: $("#emptyAddBtn"),
  eventList: $("#eventList"),
  emptyState: $("#emptyState"),
  upcomingWrap: $("#upcomingWrap"),
  upcomingList: $("#upcomingList"),
  eventDialog: $("#eventDialog"),
  eventForm: $("#eventForm"),
  eventDialogTitle: $("#eventDialogTitle"),
  closeEventDialog: $("#closeEventDialog"),
  cancelEvent: $("#cancelEvent"),
  deleteEventBtn: $("#deleteEventBtn"),
  saveEventBtn: $("#saveEventBtn"),
  fTitle: $("#fTitle"),
  fStart: $("#fStart"),
  fEnd: $("#fEnd"),
  fAllDay: $("#fAllDay"),
  fLocation: $("#fLocation"),
  fNotes: $("#fNotes"),
  settingsDialog: $("#settingsDialog"),
  settingsForm: $("#settingsForm"),
  closeSettings: $("#closeSettings"),
  cancelSettings: $("#cancelSettings"),
  saveSettingsBtn: $("#saveSettingsBtn"),
  exportBackupBtn: $("#exportBackupBtn"),
  shutdownBtn: $("#shutdownBtn"),
  sBaseUrl: $("#sBaseUrl"),
  sApiKey: $("#sApiKey"),
  sModel: $("#sModel"),
  sClearKey: $("#sClearKey"),
  testBtn: $("#testBtn"),
  testResult: $("#testResult"),
  addCompanyBtn: $("#addCompanyBtn"),
  addStageBtn: $("#addStageBtn"),
  emptyAddCompanyBtn: $("#emptyAddCompanyBtn"),
  interviewTable: $("#interviewTable"),
  interviewTableWrap: $("#interviewTableWrap"),
  interviewEmpty: $("#interviewEmpty"),
  interviewDialog: $("#interviewDialog"),
  interviewForm: $("#interviewForm"),
  interviewEyebrow: $("#interviewEyebrow"),
  interviewDialogTitle: $("#interviewDialogTitle"),
  closeInterviewDialog: $("#closeInterviewDialog"),
  cancelInterviewDialog: $("#cancelInterviewDialog"),
  saveInterviewBtn: $("#saveInterviewBtn"),
  deleteInterviewCellBtn: $("#deleteInterviewCellBtn"),
  deleteCompanyBtn: $("#deleteCompanyBtn"),
  iCompanyName: $("#iCompanyName"),
  iCompanyInfo: $("#iCompanyInfo"),
  iLink: $("#iLink"),
  iContent: $("#iContent"),
  iStatus: $("#iStatus"),
  interviewCellFields: $("#interviewCellFields"),
  toast: $("#toast"),
};

const WEEKDAYS = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];

const state = {
  view: startOfMonth(new Date()),
  selected: dateKey(new Date()),
  events: [],
  config: null,
  preview: [],
  previewMeta: null,
  viewMode: "calendar",
  interviews: { companies: [], stages: [], cells: [] },
};

const INTERVIEW_STATUS = {
  待安排: "pending",
  已安排: "scheduled",
  已通过: "passed",
  未通过: "failed",
  已取消: "cancelled",
};

let dialogMode = "create";
let editingId = null;
let previewIndex = -1;
let loadSeq = 0;
let toastTimer = null;
let interviewMode = "cell";
let interviewCompanyId = null;
let interviewStage = null;

/* ---------------- 基础工具 ---------------- */

function pad(value) {
  return String(value).padStart(2, "0");
}

function dateKey(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function timeKey(date) {
  return `${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function toISO(date) {
  return `${dateKey(date)}T${timeKey(date)}`;
}

function fromKey(key) {
  const [year, month, day] = key.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function fromISO(value) {
  const [datePart, timePart = "00:00"] = String(value).split("T");
  const [year, month, day] = datePart.split("-").map(Number);
  const [hour, minute] = timePart.split(":").map(Number);
  return new Date(year, month - 1, day, hour || 0, minute || 0);
}

function addDays(date, days) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function startOfDay(date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

function startOfMonth(date) {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function formatTime(value) {
  return timeKey(fromISO(value));
}

function formatDayShort(date) {
  return `${date.getMonth() + 1}月${date.getDate()}日`;
}

function formatUpcomingDay(date) {
  const today = dateKey(new Date());
  if (dateKey(date) === today) return "今天";
  if (dateKey(date) === dateKey(addDays(new Date(), 1))) return "明天";
  return `${date.getMonth() + 1}/${date.getDate()} ${WEEKDAYS[date.getDay()]}`;
}

function formatRange(event) {
  const start = fromISO(event.start);
  const end = fromISO(event.end);
  if (event.all_day) {
    const days = Math.max(1, Math.round((startOfDay(end) - startOfDay(start)) / 86400000));
    return days > 1 ? `全天 · ${days} 天` : "全天";
  }
  if (dateKey(start) === dateKey(end)) {
    return `${formatTime(event.start)} – ${formatTime(event.end)}`;
  }
  return `${formatTime(event.start)} – ${end.getMonth() + 1}/${end.getDate()} ${formatTime(event.end)}`;
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

async function api(path, options = {}) {
  const request = { ...options, headers: { "Content-Type": "application/json" } };
  if (request.body && typeof request.body !== "string") {
    request.body = JSON.stringify(request.body);
  }
  const response = await fetch(path, request);
  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }
  if (!response.ok) {
    throw new Error((data && data.error) || `请求失败（${response.status}）`);
  }
  return data;
}

function toast(message, type = "ok") {
  clearTimeout(toastTimer);
  els.toast.textContent = message;
  els.toast.className = `toast show${type === "error" ? " error" : ""}`;
  els.toast.hidden = false;
  toastTimer = setTimeout(() => {
    els.toast.classList.remove("show");
    setTimeout(() => {
      els.toast.hidden = true;
    }, 220);
  }, 3200);
}

/* ---------------- 数据加载与渲染 ---------------- */

function gridRange() {
  const first = startOfMonth(state.view);
  const offset = (first.getDay() + 6) % 7;
  const gridStart = addDays(first, -offset);
  const daysInMonth = new Date(first.getFullYear(), first.getMonth() + 1, 0).getDate();
  const cellCount = Math.ceil((offset + daysInMonth) / 7) * 7;
  return { gridStart, cellCount, daysInMonth };
}

async function loadEvents() {
  const seq = ++loadSeq;
  const { gridStart, cellCount } = gridRange();
  const gridEnd = addDays(gridStart, cellCount);
  const today = startOfDay(new Date());
  const fetchStart = gridStart < today ? gridStart : today;
  const upcomingEnd = addDays(today, 15);
  const fetchEnd = gridEnd > upcomingEnd ? gridEnd : upcomingEnd;

  const query = `start=${encodeURIComponent(toISO(fetchStart))}&end=${encodeURIComponent(toISO(fetchEnd))}`;
  const data = await api(`/api/events?${query}`);
  if (seq !== loadSeq) return;
  state.events = data.events || [];
  renderCalendar();
  renderAgenda();
  renderUpcoming();
}

function eventsOnDay(key) {
  return state.events
    .filter((event) => event.start.slice(0, 10) === key)
    .sort((a, b) => a.start.localeCompare(b.start) || a.id - b.id);
}

function renderCalendar() {
  const { gridStart, cellCount } = gridRange();
  const todayKey = dateKey(new Date());
  els.calendarGrid.innerHTML = "";

  for (let index = 0; index < cellCount; index += 1) {
    const day = addDays(gridStart, index);
    const key = dateKey(day);
    const cell = el("div", "day");
    cell.dataset.date = key;
    cell.tabIndex = 0;
    cell.setAttribute("role", "button");
    cell.setAttribute("aria-label", `${formatDayShort(day)} ${WEEKDAYS[day.getDay()]}`);
    if (day.getMonth() !== state.view.getMonth()) cell.classList.add("outside");
    if (key === todayKey) cell.classList.add("today");
    if (key === state.selected) cell.classList.add("selected");

    cell.append(el("span", "day-num", day.getDate()));

    const dayEvents = eventsOnDay(key);
    const holder = el("div", "day-events");
    dayEvents.slice(0, 2).forEach((event) => {
      const chip = el("button", `chip${event.all_day ? " all-day" : ""}`);
      chip.type = "button";
      chip.textContent = event.all_day ? event.title : `${formatTime(event.start)} ${event.title}`;
      chip.title = `${event.title} · ${formatRange(event)}`;
      chip.addEventListener("click", (clickEvent) => {
        clickEvent.stopPropagation();
        openEventDialog({ mode: "edit", id: event.id, event });
      });
      holder.append(chip);
    });
    if (dayEvents.length > 2) {
      holder.append(el("span", "more-count", `+${dayEvents.length - 2}`));
    }
    cell.append(holder);

    cell.addEventListener("click", () => selectDay(key));
    cell.addEventListener("keydown", (keyEvent) => {
      if (keyEvent.key === "Enter" || keyEvent.key === " ") {
        keyEvent.preventDefault();
        selectDay(key);
      }
    });

    els.calendarGrid.append(cell);
  }
}

function selectDay(key) {
  state.selected = key;
  renderCalendar();
  renderAgenda();
}

function renderAgenda() {
  const selected = fromKey(state.selected);
  const todayKey = dateKey(new Date());
  const tomorrowKey = dateKey(addDays(new Date(), 1));
  const prefix = state.selected === todayKey ? "今天" : state.selected === tomorrowKey ? "明天" : "";
  els.selectedDateLabel.textContent = `${prefix ? `${prefix} · ` : ""}${formatDayShort(selected)} ${WEEKDAYS[selected.getDay()]}`;

  const events = eventsOnDay(state.selected);
  els.eventList.innerHTML = "";
  els.emptyState.hidden = events.length > 0;

  events.forEach((event) => {
    const item = el("li", "event-item");

    const time = el("div", "event-time");
    if (event.all_day) {
      time.append(document.createTextNode("全天"));
    } else {
      time.append(document.createTextNode(formatTime(event.start)));
      time.append(el("small", null, formatTime(event.end)));
    }

    const body = el("div", "event-body");
    body.append(el("h3", null, event.title));
    if (event.location) body.append(el("div", "event-meta", `📍 ${event.location}`));
    if (event.notes) body.append(el("div", "event-notes", event.notes));

    const actions = el("div", "event-actions");
    const edit = el("button", "mini-btn", "编辑");
    edit.type = "button";
    edit.addEventListener("click", () => openEventDialog({ mode: "edit", id: event.id, event }));
    const remove = el("button", "mini-btn danger", "删除");
    remove.type = "button";
    remove.addEventListener("click", () => deleteEvent(event));
    actions.append(edit, remove);

    item.append(time, body, actions);
    els.eventList.append(item);
  });
}

function renderUpcoming() {
  const now = new Date();
  const end = addDays(startOfDay(now), 14);
  const upcoming = state.events
    .filter((event) => {
      const start = fromISO(event.start);
      const finish = fromISO(event.end);
      return finish > now && start <= end;
    })
    .sort((a, b) => a.start.localeCompare(b.start))
    .slice(0, 8);

  els.upcomingList.innerHTML = "";
  if (!upcoming.length) {
    els.upcomingList.append(el("li", "upcoming-empty", "未来两周暂无日程"));
    return;
  }

  upcoming.forEach((event) => {
    const item = el("button", "upcoming-item");
    item.type = "button";
    const start = fromISO(event.start);
    item.append(el("span", "upcoming-date", formatUpcomingDay(start)));
    item.append(el("span", "upcoming-title", event.all_day ? event.title : `${formatTime(event.start)} ${event.title}`));
    item.addEventListener("click", () => {
      state.selected = event.start.slice(0, 10);
      state.view = startOfMonth(fromISO(event.start));
      updateMonthLabel();
      renderCalendar();
      renderAgenda();
      openEventDialog({ mode: "edit", id: event.id, event });
    });
    els.upcomingList.append(item);
  });
}

function updateMonthLabel() {
  els.monthLabel.textContent = `${state.view.getFullYear()}年${state.view.getMonth() + 1}月`;
}

function updateModeBadge() {
  if (state.config && state.config.has_key) {
    els.modeBadge.textContent = "模型解析";
    els.modeBadge.classList.add("on");
    els.modeBadge.title = `${state.config.model} · Key ${state.config.key_hint}，点击修改设置`;
  } else {
    els.modeBadge.textContent = "本地解析";
    els.modeBadge.classList.remove("on");
    els.modeBadge.title = "尚未配置 API Key，点击设置";
  }
}

/* ---------------- 自然语言解析 ---------------- */

async function submitParse(event) {
  event.preventDefault();
  const text = els.nlInput.value.trim();
  if (!text) {
    els.nlInput.focus();
    return;
  }

  els.parseBtn.disabled = true;
  els.parseBtn.textContent = "解析中…";
  try {
    const result = await api("/api/parse", { method: "POST", body: { text } });
    if (!result.events || !result.events.length) {
      toast(result.warning || "没有识别到日程，试着补充日期或时间", "error");
      els.preview.hidden = true;
      return;
    }
    state.preview = result.events.slice();
    state.previewMeta = result;
    renderPreview();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    els.parseBtn.disabled = false;
    els.parseBtn.textContent = "解析日程";
  }
}

function renderPreview() {
  if (!state.preview.length) {
    els.preview.hidden = true;
    return;
  }
  els.preview.hidden = false;
  els.preview.innerHTML = "";

  const head = el("div", "preview-head");
  const title = el("div", "preview-title");
  title.append(el("span", null, "解析结果"));
  const source = state.previewMeta && state.previewMeta.source === "model" ? "模型解析" : "本地解析";
  title.append(el("span", "source-badge", source));

  const addAll = el("button", "primary-btn", `全部添加（${state.preview.length}）`);
  addAll.type = "button";
  addAll.addEventListener("click", addAllPreview);
  head.append(title, addAll);
  els.preview.append(head);

  if (state.previewMeta && state.previewMeta.warning) {
    els.preview.append(el("p", "preview-warning", state.previewMeta.warning));
  }

  const list = el("div", "preview-list");
  state.preview.forEach((event, index) => {
    const item = el("div", "preview-item");
    const main = el("div", "preview-main");
    main.append(el("h3", null, event.title));
    const meta = el("div", "preview-meta");
    meta.append(el("span", null, formatRange(event)));
    if (event.location) meta.append(el("span", null, `📍 ${event.location}`));
    main.append(meta);
    if (event.notes) main.append(el("div", "event-notes", event.notes));

    const actions = el("div", "preview-actions");
    const edit = el("button", "ghost-btn", "编辑");
    edit.type = "button";
    edit.addEventListener("click", () => openEventDialog({ mode: "preview", index, event }));
    const add = el("button", "primary-btn", "添加");
    add.type = "button";
    add.addEventListener("click", () => addPreviewAt(index));
    actions.append(edit, add);

    item.append(main, actions);
    list.append(item);
  });
  els.preview.append(list);
}

async function addPreviewAt(index) {
  const event = state.preview[index];
  if (!event) return;
  try {
    await api("/api/events", { method: "POST", body: event });
    state.preview.splice(index, 1);
    if (state.previewMeta) state.previewMeta.warning = "";
    renderPreview();
    toast("已添加日程");
    await loadEvents();
  } catch (error) {
    toast(error.message, "error");
  }
}

async function addAllPreview() {
  if (!state.preview.length) return;
  try {
    const result = await api("/api/events/bulk", { method: "POST", body: { events: state.preview } });
    state.preview = [];
    renderPreview();
    toast(`已添加 ${result.events.length} 条日程`);
    await loadEvents();
  } catch (error) {
    toast(error.message, "error");
  }
}

/* ---------------- 手动增删改 ---------------- */

function openEventDialog({ mode, id = null, index = -1, event }) {
  dialogMode = mode;
  editingId = id;
  previewIndex = index;

  els.eventDialogTitle.textContent =
    mode === "edit" ? "编辑日程" : mode === "preview" ? "修改解析结果" : "添加日程";
  els.fTitle.value = event.title || "";
  els.fStart.value = (event.start || "").slice(0, 16);
  els.fEnd.value = (event.end || "").slice(0, 16);
  els.fAllDay.checked = Boolean(event.all_day);
  els.fLocation.value = event.location || "";
  els.fNotes.value = event.notes || "";
  els.deleteEventBtn.hidden = mode !== "edit" || id === null;

  if (!els.fStart.value) {
    const base = fromKey(state.selected);
    const start = new Date(base);
    start.setHours(9, 0, 0, 0);
    const end = new Date(base);
    end.setHours(10, 0, 0, 0);
    els.fStart.value = toISO(start);
    els.fEnd.value = toISO(end);
  }

  els.eventDialog.showModal();
  setTimeout(() => els.fTitle.focus(), 30);
}

function readEventForm() {
  const title = els.fTitle.value.trim();
  if (!title) throw new Error("请填写标题");
  if (!els.fStart.value) throw new Error("请选择开始时间");

  const allDay = els.fAllDay.checked;
  let start = els.fStart.value.slice(0, 16);
  let end = els.fEnd.value ? els.fEnd.value.slice(0, 16) : "";

  if (allDay) {
    start = `${start.slice(0, 10)}T00:00`;
    if (end) end = `${end.slice(0, 10)}T00:00`;
  }

  if (!end) {
    const startDate = fromISO(start);
    const endDate = allDay ? addDays(startDate, 1) : new Date(startDate.getTime() + 3600000);
    end = toISO(endDate);
    if (allDay) end = `${dateKey(endDate)}T00:00`;
  }

  return {
    title,
    start,
    end,
    all_day: allDay,
    location: els.fLocation.value.trim(),
    notes: els.fNotes.value.trim(),
  };
}

async function saveEvent(event) {
  event.preventDefault();
  let payload;
  try {
    payload = readEventForm();
  } catch (error) {
    toast(error.message, "error");
    return;
  }

  els.saveEventBtn.disabled = true;
  try {
    if (dialogMode === "edit" && editingId !== null) {
      await api(`/api/events/${editingId}`, { method: "PATCH", body: payload });
      toast("日程已保存");
    } else if (dialogMode === "preview") {
      state.preview[previewIndex] = payload;
      renderPreview();
      toast("已更新解析结果");
      els.eventDialog.close();
      return;
    } else {
      await api("/api/events", { method: "POST", body: payload });
      toast("已添加日程");
    }
    els.eventDialog.close();
    await loadEvents();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    els.saveEventBtn.disabled = false;
  }
}

async function removeEvent(id, title) {
  if (!window.confirm(`删除「${title}」？`)) return false;
  try {
    await api(`/api/events/${id}`, { method: "DELETE" });
    toast("日程已删除");
    await loadEvents();
    return true;
  } catch (error) {
    toast(error.message, "error");
    return false;
  }
}

async function deleteEvent(event) {
  await removeEvent(event.id, event.title);
}

async function deleteEditingEvent() {
  if (editingId === null) return;
  const title = els.fTitle.value.trim() || "这条日程";
  if (await removeEvent(editingId, title)) {
    els.eventDialog.close();
  }
}

/* ---------------- 设置 ---------------- */

async function openSettings() {
  try {
    const config = await api("/api/config");
    state.config = config;
    updateModeBadge();
    els.sBaseUrl.value = config.base_url || "";
    els.sModel.value = config.model || "";
    els.sApiKey.value = "";
    els.sApiKey.placeholder = config.has_key ? `已保存 ${config.key_hint}，留空不修改` : "sk-…";
    els.sClearKey.checked = false;
    els.testResult.textContent = "";
    els.testResult.className = "test-result";
    els.settingsDialog.showModal();
    setTimeout(() => els.sBaseUrl.focus(), 30);
  } catch (error) {
    toast(error.message, "error");
  }
}

async function saveSettings(event) {
  event.preventDefault();
  const payload = {
    base_url: els.sBaseUrl.value.trim(),
    model: els.sModel.value.trim(),
  };
  if (els.sApiKey.value.trim()) payload.api_key = els.sApiKey.value.trim();
  if (els.sClearKey.checked) payload.clear_key = true;

  els.saveSettingsBtn.disabled = true;
  try {
    state.config = await api("/api/config", { method: "PUT", body: payload });
    updateModeBadge();
    els.settingsDialog.close();
    toast(state.config.has_key ? "设置已保存，已启用模型解析" : "设置已保存，当前使用本地解析");
  } catch (error) {
    toast(error.message, "error");
  } finally {
    els.saveSettingsBtn.disabled = false;
  }
}

async function exportBackup() {
  els.exportBackupBtn.disabled = true;
  try {
    const response = await fetch("/api/backup");
    if (!response.ok) {
      let message = `导出失败（${response.status}）`;
      try {
        const data = await response.json();
        if (data && data.error) message = data.error;
      } catch {
        // ignore
      }
      throw new Error(message);
    }

    const blob = await response.blob();
    const disposition = response.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename="([^"]+)"/);
    const filename = match ? match[1] : "calendar-backup.zip";
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast("备份已开始下载");
  } catch (error) {
    toast(error.message, "error");
  } finally {
    els.exportBackupBtn.disabled = false;
  }
}

async function shutdownApp() {
  if (!window.confirm("退出本地日历？服务将停止，日程数据会保留。")) return;
  try {
    await api("/api/shutdown", { method: "POST", body: { confirm: true } });
  } catch {
    // 服务可能在返回响应后立即关闭。
  }
  els.settingsDialog.close();
  showShutdownScreen();
}

function showShutdownScreen() {
  const overlay = document.createElement("div");
  overlay.className = "shutdown-screen";

  const card = document.createElement("div");
  card.className = "shutdown-card";
  const mark = document.createElement("div");
  mark.className = "shutdown-mark";
  mark.textContent = "✓";
  const title = document.createElement("h2");
  title.textContent = "本地日历已退出";
  const text = document.createElement("p");
  text.textContent = "服务已停止，可以关闭此页面。下次使用时重新启动应用即可，日程数据仍在本地。";

  card.append(mark, title, text);
  overlay.append(card);
  document.body.append(overlay);
}

async function testConnection() {
  els.testBtn.disabled = true;
  els.testResult.className = "test-result";
  els.testResult.textContent = "测试中…";
  const payload = {
    base_url: els.sBaseUrl.value.trim(),
    model: els.sModel.value.trim(),
  };
  if (els.sApiKey.value.trim()) payload.api_key = els.sApiKey.value.trim();

  try {
    const result = await api("/api/config/test", { method: "POST", body: payload });
    els.testResult.className = "test-result ok";
    els.testResult.textContent = result.count ? `连接成功，发现 ${result.count} 个模型` : "连接成功";
  } catch (error) {
    els.testResult.className = "test-result bad";
    els.testResult.textContent = error.message;
  } finally {
    els.testBtn.disabled = false;
  }
}

/* ---------------- 面试时间线 ---------------- */

function switchView(mode) {
  if (mode !== "calendar" && mode !== "interview") return;
  state.viewMode = mode;
  const isCalendar = mode === "calendar";
  els.calendarView.hidden = !isCalendar;
  els.interviewView.hidden = isCalendar;
  els.monthNav.hidden = !isCalendar;
  els.calendarViewBtn.classList.toggle("active", isCalendar);
  els.interviewViewBtn.classList.toggle("active", !isCalendar);

  if (isCalendar) {
    loadEvents().catch((error) => toast(error.message, "error"));
  } else {
    loadInterviews().catch((error) => toast(error.message, "error"));
  }
}

async function loadInterviews() {
  const data = await api("/api/interviews");
  state.interviews = {
    companies: data.companies || [],
    stages: data.stages || [],
    cells: data.cells || [],
  };
  renderInterviewTable();
}

function interviewCellFor(companyId, stage) {
  return state.interviews.cells.find(
    (cell) => cell.company_id === companyId && cell.stage === stage
  );
}

function renderInterviewTable() {
  const { companies, stages, cells } = state.interviews;
  els.interviewTable.innerHTML = "";
  const hasCompanies = companies.length > 0;
  els.interviewEmpty.hidden = hasCompanies;
  els.interviewTableWrap.hidden = !hasCompanies;
  if (!hasCompanies) return;

  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  const corner = document.createElement("th");
  corner.className = "corner";
  corner.textContent = "阶段 / 公司";
  headRow.append(corner);

  companies.forEach((company) => {
    const th = document.createElement("th");
    th.className = "company-col";
    const button = document.createElement("button");
    button.type = "button";
    button.className = "company-head";
    button.title = "编辑公司信息";
    button.dataset.companyId = String(company.id);
    const name = document.createElement("span");
    name.className = "company-name";
    name.textContent = company.name;
    button.append(name);
    if (company.info) {
      const info = document.createElement("span");
      info.className = "company-snippet";
      info.textContent = company.info;
      button.append(info);
    }
    button.addEventListener("click", () =>
      openInterviewDialog({ mode: "company-edit", companyId: company.id })
    );
    th.append(button);
    headRow.append(th);
  });
  thead.append(headRow);
  els.interviewTable.append(thead);

  const tbody = document.createElement("tbody");
  stages.forEach((stage) => {
    const row = document.createElement("tr");
    const stageHead = document.createElement("th");
    stageHead.className = "stage-head";
    stageHead.textContent = stage.name;
    row.append(stageHead);

    companies.forEach((company) => {
      const cell = cells.find(
        (item) => item.company_id === company.id && item.stage === stage.name
      );
      const td = document.createElement("td");
      const button = document.createElement("button");
      button.type = "button";
      button.className = "interview-cell";
      button.dataset.companyId = String(company.id);
      button.dataset.stage = stage.name;

      if (cell) {
        button.classList.add(`status-${INTERVIEW_STATUS[cell.status] || "pending"}`);
        button.title = `${cell.status}${cell.content ? ` · ${cell.content}` : ""}`;
        const status = document.createElement("span");
        status.className = "cell-status";
        status.textContent = cell.status;
        button.append(status);
        if (cell.link) {
          const link = document.createElement("span");
          link.className = "cell-link";
          link.textContent = "链接";
          button.append(link);
        }
      } else {
        button.classList.add("empty-cell");
        button.title = "点击填写";
      }

      const summary = document.createElement("span");
      summary.className = "cell-summary";
      if (cell && cell.content) {
        summary.textContent =
          cell.content.length > 30 ? `${cell.content.slice(0, 30)}…` : cell.content;
      } else if (cell && cell.link) {
        summary.textContent = "已填写面试链接";
      } else if (cell) {
        summary.textContent = "点击补充内容";
      } else {
        summary.textContent = "＋";
        summary.classList.add("cell-plus");
      }
      button.append(summary);

      button.addEventListener("click", () =>
        openInterviewDialog({ mode: "cell", companyId: company.id, stage: stage.name })
      );
      td.append(button);
      row.append(td);
    });
    tbody.append(row);
  });
  els.interviewTable.append(tbody);
}

function openInterviewDialog({ mode, companyId = null, stage = null }) {
  const company = state.interviews.companies.find((item) => item.id === companyId) || null;
  if (mode !== "company-create" && !company) {
    toast("公司不存在，请刷新后重试", "error");
    return;
  }

  interviewMode = mode;
  interviewCompanyId = companyId;
  interviewStage = stage;

  const isCell = mode === "cell";
  const cell = isCell ? interviewCellFor(companyId, stage) : null;
  els.interviewCellFields.hidden = !isCell;
  els.deleteInterviewCellBtn.hidden = !isCell || !cell;
  els.deleteCompanyBtn.hidden = mode !== "company-edit";
  els.iCompanyName.readOnly = isCell;

  if (isCell) {
    els.interviewEyebrow.textContent = "面试记录";
    els.interviewDialogTitle.textContent = `${company.name} · ${stage}`;
    els.iCompanyName.value = company.name;
    els.iCompanyInfo.value = company.info || "";
    els.iLink.value = cell ? cell.link : "";
    els.iContent.value = cell ? cell.content : "";
    els.iStatus.value = cell ? cell.status : "待安排";
  } else if (mode === "company-create") {
    els.interviewEyebrow.textContent = "公司信息";
    els.interviewDialogTitle.textContent = "添加公司";
    els.iCompanyName.value = "";
    els.iCompanyInfo.value = "";
  } else {
    els.interviewEyebrow.textContent = "公司信息";
    els.interviewDialogTitle.textContent = company.name;
    els.iCompanyName.value = company.name;
    els.iCompanyInfo.value = company.info || "";
  }

  els.interviewDialog.showModal();
  setTimeout(() => (isCell ? els.iLink : els.iCompanyName).focus(), 30);
}

async function saveInterview(event) {
  event.preventDefault();
  const name = els.iCompanyName.value.trim();
  const info = els.iCompanyInfo.value.trim();
  if (!name) {
    toast("请填写公司名称", "error");
    return;
  }

  els.saveInterviewBtn.disabled = true;
  try {
    if (interviewMode === "cell") {
      await api(`/api/interviews/companies/${interviewCompanyId}`, {
        method: "PATCH",
        body: { info },
      });
      await api("/api/interviews/cells", {
        method: "PUT",
        body: {
          company_id: interviewCompanyId,
          stage: interviewStage,
          link: els.iLink.value.trim(),
          content: els.iContent.value.trim(),
          status: els.iStatus.value,
        },
      });
      toast("面试记录已保存");
    } else if (interviewMode === "company-create") {
      await api("/api/interviews/companies", {
        method: "POST",
        body: { name, info },
      });
      toast("公司已添加");
    } else {
      await api(`/api/interviews/companies/${interviewCompanyId}`, {
        method: "PATCH",
        body: { name, info },
      });
      toast("公司信息已保存");
    }
    els.interviewDialog.close();
    await loadInterviews();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    els.saveInterviewBtn.disabled = false;
  }
}

async function deleteInterviewCell() {
  if (interviewCompanyId === null || !interviewStage) return;
  if (!window.confirm("删除这条面试记录？")) return;
  try {
    await api(
      `/api/interviews/cells?company_id=${interviewCompanyId}&stage=${encodeURIComponent(interviewStage)}`,
      { method: "DELETE" }
    );
    els.interviewDialog.close();
    toast("面试记录已删除");
    await loadInterviews();
  } catch (error) {
    toast(error.message, "error");
  }
}

async function deleteInterviewCompany() {
  if (interviewCompanyId === null) return;
  const company = state.interviews.companies.find((item) => item.id === interviewCompanyId);
  if (!window.confirm(`删除「${company ? company.name : "该公司"}」及其所有面试记录？`)) return;
  try {
    await api(`/api/interviews/companies/${interviewCompanyId}`, { method: "DELETE" });
    els.interviewDialog.close();
    toast("公司已删除");
    await loadInterviews();
  } catch (error) {
    toast(error.message, "error");
  }
}

async function addInterviewStage() {
  const name = window.prompt("新阶段名称，例如：笔试、HR 面、终面");
  if (name === null) return;
  const trimmed = name.trim();
  if (!trimmed) return;
  try {
    await api("/api/interviews/stages", { method: "POST", body: { name: trimmed } });
    toast("阶段已添加");
    await loadInterviews();
  } catch (error) {
    toast(error.message, "error");
  }
}

/* ---------------- 事件绑定与初始化 ---------------- */

function shiftMonth(delta) {
  state.view = new Date(state.view.getFullYear(), state.view.getMonth() + delta, 1);
  const selected = fromKey(state.selected);
  if (
    selected.getFullYear() !== state.view.getFullYear() ||
    selected.getMonth() !== state.view.getMonth()
  ) {
    state.selected = dateKey(state.view);
  }
  updateMonthLabel();
  loadEvents().catch((error) => toast(error.message, "error"));
}

function bindEvents() {
  els.prevMonth.addEventListener("click", () => shiftMonth(-1));
  els.nextMonth.addEventListener("click", () => shiftMonth(1));
  els.todayBtn.addEventListener("click", () => {
    const today = new Date();
    state.view = startOfMonth(today);
    state.selected = dateKey(today);
    updateMonthLabel();
    loadEvents().catch((error) => toast(error.message, "error"));
  });

  els.parseForm.addEventListener("submit", submitParse);
  els.settingsBtn.addEventListener("click", openSettings);
  els.modeBadge.addEventListener("click", openSettings);

  els.calendarViewBtn.addEventListener("click", () => switchView("calendar"));
  els.interviewViewBtn.addEventListener("click", () => switchView("interview"));
  els.addCompanyBtn.addEventListener("click", () =>
    openInterviewDialog({ mode: "company-create" })
  );
  els.emptyAddCompanyBtn.addEventListener("click", () =>
    openInterviewDialog({ mode: "company-create" })
  );
  els.addStageBtn.addEventListener("click", addInterviewStage);
  els.interviewForm.addEventListener("submit", saveInterview);
  els.closeInterviewDialog.addEventListener("click", () => els.interviewDialog.close());
  els.cancelInterviewDialog.addEventListener("click", () => els.interviewDialog.close());
  els.deleteInterviewCellBtn.addEventListener("click", deleteInterviewCell);
  els.deleteCompanyBtn.addEventListener("click", deleteInterviewCompany);

  els.addBtn.addEventListener("click", () => openEventDialog({ mode: "create", event: {} }));
  els.emptyAddBtn.addEventListener("click", () => openEventDialog({ mode: "create", event: {} }));

  els.eventForm.addEventListener("submit", saveEvent);
  els.closeEventDialog.addEventListener("click", () => els.eventDialog.close());
  els.cancelEvent.addEventListener("click", () => els.eventDialog.close());
  els.deleteEventBtn.addEventListener("click", deleteEditingEvent);

  els.settingsForm.addEventListener("submit", saveSettings);
  els.closeSettings.addEventListener("click", () => els.settingsDialog.close());
  els.cancelSettings.addEventListener("click", () => els.settingsDialog.close());
  els.testBtn.addEventListener("click", testConnection);
  els.exportBackupBtn.addEventListener("click", exportBackup);
  els.shutdownBtn.addEventListener("click", shutdownApp);

  els.fAllDay.addEventListener("change", () => {
    if (!els.fStart.value) return;
    const datePart = els.fStart.value.slice(0, 10);
    if (els.fAllDay.checked) {
      els.fStart.value = `${datePart}T00:00`;
      if (!els.fEnd.value || els.fEnd.value.slice(0, 10) <= datePart) {
        els.fEnd.value = `${dateKey(addDays(fromKey(datePart), 1))}T00:00`;
      }
    } else if (els.fStart.value.endsWith("T00:00")) {
      els.fStart.value = `${datePart}T09:00`;
      els.fEnd.value = `${datePart}T10:00`;
    }
  });

  [els.eventDialog, els.interviewDialog, els.settingsDialog].forEach((dialog) => {
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) dialog.close();
    });
  });
}

async function init() {
  bindEvents();
  updateMonthLabel();
  try {
    state.config = await api("/api/config");
    updateModeBadge();
  } catch (error) {
    toast(`读取设置失败：${error.message}`, "error");
  }
  try {
    await loadEvents();
  } catch (error) {
    toast(`加载日程失败：${error.message}`, "error");
  }
}

init();
