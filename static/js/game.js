const session = getSession();
if (!session.room || !session.name) {
  window.location.href = "/";
}

document.getElementById("room-code-label").textContent = session.room;

let localSecondsLeft = null;
let countdownTimer = null;
let finalFetched = false;
let seerLocalResult = null; // { target, role_hint } — giữ lại trên máy để refresh() không xoá mất

function hideAll() {
  ["role-panel", "status-panel", "election-panel", "transition-panel", "night-panel", "day-panel", "end-panel", "roster-panel", "log-panel"]
    .forEach(id => document.getElementById(id).style.display = "none");
}

async function refresh() {
  const { ok, data } = await apiGet(`/api/my-role?room_code=${session.room}&name=${encodeURIComponent(session.name)}`);
  if (!ok || !data.success) {
    showToast(data.message || "Mất kết nối với phòng", true);
    return;
  }
  render(data);
}

function render(info) {
  const room = info.room;

  if (!room.is_started) {
    window.location.href = "/room";
    return;
  }

  document.getElementById("phase-tag").innerHTML = phaseTag(room.phase);

  document.getElementById("role-panel").style.display = "block";
  const ri = roleInfo(info.role);
  document.getElementById("role-side").textContent = (ri.side || "").toUpperCase();
  document.getElementById("role-name").textContent = info.role;
  document.getElementById("role-desc").textContent = ri.desc;

  document.getElementById("status-panel").style.display = "block";
  document.getElementById("alive-status").innerHTML = info.is_alive
    ? `<span class="avatar-status"></span> Bạn vẫn còn sống${info.is_chief ? ' · <strong style="color:var(--cyan)">Trưởng Làng</strong>' : ''}`
    : `<span class="avatar-status dead"></span> Bạn đã bị loại — tiếp tục theo dõi ván đấu trong im lặng`;

  document.getElementById("night-panel").style.display = "none";
  document.getElementById("day-panel").style.display = "none";
  document.getElementById("end-panel").style.display = "none";
  document.getElementById("election-panel").style.display = "none";
  document.getElementById("transition-panel").style.display = "none";

  if (room.phase === "ended") {
    document.getElementById("end-panel").style.display = "block";
    renderEnd(info, room);
  } else if (room.phase === "election") {
    document.getElementById("election-panel").style.display = "block";
    renderElection(info, room);
  } else if (room.phase === "transition") {
    document.getElementById("transition-panel").style.display = "block";
    renderTransition(info, room);
  } else if (room.phase === "night") {
    document.getElementById("night-panel").style.display = "block";
    renderNight(info, room);
  } else if (room.phase === "day") {
    document.getElementById("day-panel").style.display = "block";
    renderDay(info, room);
  }

  document.getElementById("roster-panel").style.display = "block";
  document.getElementById("roster-list").innerHTML = room.players.map(p => `
    <div class="player-row-v2 ${p.is_alive ? '' : 'dead'}">
      <span class="avatar-status ${p.is_alive ? '' : 'dead'}">
        <span class="avatar" style="background:${avatarColor(p.name)}">${initials(p.name)}</span>
      </span>
      <span class="name ${p.is_alive ? '' : 'dead-text'}">${p.name}</span>
      ${p.name === room.chief_name ? '<span class="host-badge">TRƯỞNG LÀNG</span>' : ''}
    </div>
  `).join("");

  if (room.log && room.log.length) {
    document.getElementById("log-panel").style.display = "block";
    document.getElementById("log-feed").innerHTML = room.log.slice().reverse().map(l => {
      const t = new Date(l.time * 1000);
      const hh = String(t.getHours()).padStart(2, "0");
      const mm = String(t.getMinutes()).padStart(2, "0");
      return `<div class="chat-line"><span class="chat-time">${hh}:${mm}</span>${l.message}</div>`;
    }).join("");
  }
}

function avatarCardHtml(name, ringClass, skull) {
  return `
    <div class="reveal-victim">
      <div class="avatar-card-ring ${ringClass}">
        <span class="avatar" style="background:${avatarColor(name)}">${initials(name)}</span>
        ${skull ? `<span class="skull-badge">${skull}</span>` : ""}
      </div>
      <div class="name">${name}</div>
    </div>
  `;
}

function renderTransition(info, room) {
  const ctx = room.transition_context || {};
  const box = document.getElementById("transition-panel");
  let icon = "🌙";
  let title = "Chuẩn bị...";
  let body = "";

  if (ctx.type === "night_pause") {
    icon = "🌙";
    title = "Chuẩn bị...";
    body = `<p class="muted mb-0">Tiếp theo: <strong style="color:var(--cyan)">${ctx.role || ""}</strong></p>`;
  } else if (ctx.type === "night_result") {
    icon = "☀️";
    title = "Trời sáng";
    if (ctx.victims && ctx.victims.length) {
      body = ctx.victims.map(v => avatarCardHtml(v, "", "💀")).join("");
      body += `<p class="reveal-sub">Đã bị Sói tấn công trong đêm</p>`;
    } else {
      body = `<p class="reveal-sub" style="margin-top:14px;">Đêm qua không có ai chết — cả làng bình an.</p>`;
    }
  } else if (ctx.type === "election_result") {
    icon = "👑";
    title = "Kết quả bầu Trưởng Làng";
    if (ctx.chief) {
      body = avatarCardHtml(ctx.chief, "chief", "👑");
      body += `<p class="reveal-sub">Trưởng Làng — phiếu tính gấp đôi khi biểu quyết</p>`;
    } else {
      body = `<p class="reveal-sub" style="margin-top:14px;">Không có ai còn sống để làm Trưởng Làng.</p>`;
    }
  } else if (ctx.type === "day_result") {
    icon = "⚖️";
    title = "Kết quả biểu quyết";
    if (ctx.hanged) {
      body = avatarCardHtml(ctx.hanged, "", "💀");
      body += `<p class="reveal-sub">Đã bị cả làng treo cổ</p>`;
    } else {
      body = `<p class="reveal-sub" style="margin-top:14px;">Làng không thống nhất được — không ai bị treo cổ hôm nay.</p>`;
    }
  }

  box.innerHTML = `
    <div class="reveal-card">
      <div class="reveal-icon">${icon}</div>
      <h3 class="mt-0" style="text-transform:none; letter-spacing:0; color:var(--text-100); font-size:1.3rem;">${title}</h3>
      ${body}
      <div class="countdown-wrap">
        <div class="countdown-track"><div class="countdown-fill" id="transition-countdown-fill" style="width:100%;"></div></div>
        <div class="countdown-text" id="transition-countdown-text"></div>
      </div>
    </div>
  `;
  if (room.seconds_left !== null && room.seconds_left !== undefined) {
    startCountdown(room.seconds_left, "transition-countdown-fill", "transition-countdown-text",
      ctx.type === "night_pause" ? "Bắt đầu sau" : "Chuyển cảnh sau");
  }
  seerLocalResult = null;
}

function renderElection(info, room) {
  if (room.seconds_left !== null && room.seconds_left !== undefined) {
    startCountdown(room.seconds_left, "election-countdown-fill", "election-countdown-text", "Thời gian bầu cử");
  }
  document.getElementById("election-progress").textContent = `${room.election_votes_count ?? 0}/${room.alive_count} người đã bỏ phiếu`;

  const area = document.getElementById("election-area");
  if (!info.is_alive) {
    area.innerHTML = `<p class="muted">Bạn đã bị loại, chỉ có thể theo dõi.</p>`;
    return;
  }
  if (info.has_voted_election) {
    area.innerHTML = `<p class="muted">Bạn đã bỏ phiếu. Đang chờ những người còn lại...</p>`;
    return;
  }

  renderSelectionGrid(area, {
    key: "election",
    names: info.all_alive_players || [],
    selfName: session.name,
    allowAbstain: true,
    abstainLabel: "Không bầu ai",
    confirmLabel: "Khoá phiếu bầu",
    onConfirm: async (choice) => {
      const { ok, data } = await apiPost("/api/election-vote", { room_code: session.room, voter_name: session.name, choice_name: choice });
      if (!ok || !data.success) return showToast(data.message || "Lỗi", true);
      showToast(data.message);
      refresh();
    },
  });
}

function renderNightTracker(room) {
  const sequence = room.night_sequence || [];
  const currentIdx = sequence.indexOf(room.subphase);
  const steps = NIGHT_STEPS.filter(s => sequence.includes(s.key));
  const html = steps.map(s => {
    const idx = sequence.indexOf(s.key);
    let cls = "";
    if (s.key === room.subphase) cls = "active";
    else if (currentIdx >= 0 && idx < currentIdx) cls = "done";
    return `<div class="night-step ${cls}">${s.label}</div>`;
  });
  document.getElementById("night-tracker").innerHTML = html.join(`<div class="night-connector"></div>`);
}

function startCountdown(seconds, fillId, textId, label) {
  clearInterval(countdownTimer);
  localSecondsLeft = seconds;
  const total = Math.max(seconds, 1);
  const update = () => {
    const fill = document.getElementById(fillId);
    const text = document.getElementById(textId);
    if (!fill || !text) return;
    const pct = Math.max(0, Math.min(100, (localSecondsLeft / total) * 100));
    fill.style.width = pct + "%";
    text.textContent = localSecondsLeft > 0 ? `${label}: còn ${localSecondsLeft}s` : `${label}: đang xử lý...`;
  };
  update();
  countdownTimer = setInterval(() => {
    localSecondsLeft = Math.max(0, localSecondsLeft - 1);
    update();
    if (localSecondsLeft <= 0) clearInterval(countdownTimer);
  }, 1000);
}

function renderNight(info, room) {
  document.getElementById("night-day-num").textContent = room.day_count;
  renderNightTracker(room);

  if (room.seconds_left !== null && room.seconds_left !== undefined) {
    startCountdown(room.seconds_left, "countdown-fill", "countdown-text", room.subphase_label || "Đang xử lý");
  }

  const banner = document.getElementById("turn-banner");
  const actionPanel = document.getElementById("action-panel");

  if (!info.is_alive) {
    banner.innerHTML = `<div class="turn-banner waiting">Bạn đã bị loại — hãy nhắm mắt và giữ im lặng.</div>`;
    actionPanel.style.display = "none";
    return;
  }

  if (info.my_turn) {
    banner.innerHTML = `<div class="turn-banner">Đến lượt bạn — hãy thao tác trong im lặng.</div>`;
    actionPanel.style.display = "block";
    renderAction(info, room);
  } else {
    banner.innerHTML = `<div class="turn-banner waiting">${room.subphase_label || "Đang chờ"}... Hãy nhắm mắt và giữ im lặng.</div>`;
    actionPanel.style.display = "none";
    seerLocalResult = null;
  }
}

function renderAction(info, room) {
  const targetList = document.getElementById("target-list");
  const witchBox = document.getElementById("witch-actions");
  const seerBox = document.getElementById("seer-result");
  witchBox.innerHTML = "";
  seerBox.innerHTML = "";
  // Lưu ý: KHÔNG xoá targetList.innerHTML ở đây — để renderSelectionGrid tự
  // quyết định có cần dựng lại hay không (dựa vào key), tránh xoá mất lựa
  // chọn người dùng đang chọn dở mỗi khi trang tự làm mới sau vài giây.
  const targets = info.alive_players || [];

  if (info.role === "Ma Sói") {
    if (info.wolf_total_count > 1) {
      document.getElementById("action-desc").textContent =
        `Bầy có ${info.wolf_total_count} Sói — chỉ chuyển lượt khi TẤT CẢ đã khoá mục tiêu (${info.wolf_ready_count}/${info.wolf_total_count}).`;
    } else {
      document.getElementById("action-desc").textContent = "Im lặng, chọn người bạn muốn tiêu diệt rồi khoá lựa chọn.";
    }

    if (info.i_am_ready) {
      targetList.innerHTML = `<p class="muted">Bạn đã khoá mục tiêu: <strong style="color:var(--red)">${info.wolf_current_target || ""}</strong>. Đang chờ ${info.wolf_total_count - info.wolf_ready_count} Sói còn lại...</p>`;
      targetList.dataset.gridKey = "";
      return;
    }

    renderSelectionGrid(targetList, {
      key: `night:wolf:${room.day_count}`,
      names: targets, danger: true, confirmLabel: "Khoá mục tiêu",
      onConfirm: async (name) => {
        if (!name) return;
        const { ok, data } = await apiPost("/api/wolf-action", { room_code: session.room, wolf_name: session.name, target_name: name });
        if (!ok || !data.success) return showToast(data.message || "Lỗi", true);
        showToast(data.message);
        refresh();
      },
    });
  }

  if (info.role === "Bảo Vệ") {
    document.getElementById("action-desc").textContent = "Chọn người bạn muốn che chở đêm nay rồi khoá lựa chọn.";
    renderSelectionGrid(targetList, {
      key: `night:guard:${room.day_count}`,
      names: targets, confirmLabel: "Khoá lựa chọn che chở",
      onConfirm: async (name) => {
        if (!name) return;
        const { ok, data } = await apiPost("/api/guard-action", { room_code: session.room, guard_name: session.name, target_name: name });
        if (!ok || !data.success) return showToast(data.message || "Lỗi", true);
        showToast(data.message);
        refresh();
      },
    });
  }

  if (info.role === "Tiên Tri") {
    document.getElementById("action-desc").textContent = "Chọn một người để soi danh tính.";

    if (seerLocalResult) {
      targetList.innerHTML = "";
      targetList.dataset.gridKey = "";
      seerBox.innerHTML = `
        <div class="reveal-victim">
          <div class="avatar-card-ring ${seerLocalResult.role_hint === 'Ma Sói' ? '' : 'safe'}">
            <span class="avatar" style="background:${avatarColor(seerLocalResult.target)}">${initials(seerLocalResult.target)}</span>
          </div>
          <div class="name">${seerLocalResult.target}</div>
        </div>
        <p style="margin-top:6px;">Là: <strong style="color:${seerLocalResult.role_hint === 'Ma Sói' ? 'var(--red)' : 'var(--green)'}">${seerLocalResult.role_hint}</strong></p>
        <button class="btn-primary btn-small" id="seer-continue-btn" style="margin-top:8px;">Tiếp tục (nhường lượt)</button>
      `;
      document.getElementById("seer-continue-btn").addEventListener("click", async () => {
        const { ok, data } = await apiPost("/api/seer-done", { room_code: session.room, seer_name: session.name });
        if (!ok || !data.success) return showToast(data.message || "Lỗi", true);
        seerLocalResult = null;
        refresh();
      });
      return;
    }

    renderSelectionGrid(targetList, {
      key: `night:seer:${room.day_count}`,
      names: targets, allowAbstain: true, abstainLabel: "Bỏ qua lượt", confirmLabel: "Soi danh tính",
      onConfirm: async (name) => {
        if (!name) {
          const { ok, data } = await apiPost("/api/seer-pass", { room_code: session.room, seer_name: session.name });
          if (!ok || !data.success) return showToast(data.message || "Lỗi", true);
          refresh();
          return;
        }
        const { ok, data } = await apiPost("/api/seer-action", { room_code: session.room, seer_name: session.name, target_name: name });
        if (!ok || !data.success) return showToast(data.message || "Lỗi", true);
        seerLocalResult = { target: data.target, role_hint: data.role_hint };
        refresh();
      },
    });
  }

  if (info.role === "Phù Thủy") {
    document.getElementById("action-desc").textContent = "Bạn có một bình cứu và một bình độc, mỗi bình chỉ dùng được một lần trong cả ván.";
    let html = "";
    if (info.wolf_victim_hint) {
      html += `<p>Đêm nay <strong>${info.wolf_victim_hint}</strong> bị Sói cắn.</p>`;
      if (!info.witch_used_save) {
        html += `<button class="btn-leaf btn-small" id="witch-save">Dùng bình cứu cho ${info.wolf_victim_hint}</button>`;
      } else {
        html += `<p class="muted">Bạn đã dùng hết bình cứu.</p>`;
      }
    } else {
      html += `<p class="muted">Đêm nay chưa ai bị Sói cắn.</p>`;
    }
    witchBox.innerHTML = html;

    const saveBtn = document.getElementById("witch-save");
    if (saveBtn) saveBtn.addEventListener("click", async () => {
      const { ok, data } = await apiPost("/api/witch-action", { room_code: session.room, witch_name: session.name, action_type: "save" });
      if (!ok || !data.success) return showToast(data.message || "Lỗi", true);
      showToast(data.message);
      refresh();
    });

    if (!info.witch_used_kill) {
      const killLabel = document.createElement("p");
      killLabel.className = "muted";
      killLabel.style.marginTop = "14px";
      killLabel.textContent = "Hoặc dùng bình độc lên:";
      witchBox.appendChild(killLabel);

      renderSelectionGrid(targetList, {
        key: `night:witch-kill:${room.day_count}`,
        names: targets, danger: true, allowAbstain: true, abstainLabel: "Không dùng độc", confirmLabel: "Dùng bình độc",
        onConfirm: async (name) => {
          if (!name) { showToast("Đã chọn không dùng độc đêm nay."); return; }
          const { ok, data } = await apiPost("/api/witch-action", { room_code: session.room, witch_name: session.name, action_type: "kill", target_name: name });
          if (!ok || !data.success) return showToast(data.message || "Lỗi", true);
          showToast(data.message);
          refresh();
        },
      });
    } else {
      targetList.innerHTML = "";
      targetList.dataset.gridKey = "";
    }

    const doneBtn = document.createElement("button");
    doneBtn.className = "btn-ghost btn-small";
    doneBtn.style.marginTop = "14px";
    doneBtn.textContent = "Xong lượt của tôi";
    doneBtn.addEventListener("click", async () => {
      const { ok, data } = await apiPost("/api/witch-done", { room_code: session.room, witch_name: session.name });
      if (!ok || !data.success) return showToast(data.message || "Lỗi", true);
      refresh();
    });
    witchBox.appendChild(doneBtn);
  }
}

function renderDay(info, room) {
  document.getElementById("day-day-num").textContent = room.day_count;
  document.getElementById("day-result-msg").textContent = room.last_night_msg || "Cả làng cùng thảo luận để tìm ra Sói.";

  if (room.seconds_left !== null && room.seconds_left !== undefined) {
    startCountdown(room.seconds_left, "day-countdown-fill", "day-countdown-text", "Thời gian bỏ phiếu");
  }

  document.getElementById("vote-progress").textContent = `${room.votes_count ?? 0}/${room.alive_count} người đã bỏ phiếu`;

  const area = document.getElementById("vote-area");
  if (!info.is_alive) {
    area.innerHTML = `<p class="muted">Bạn đã bị loại, chỉ có thể theo dõi cuộc bỏ phiếu.</p>`;
    return;
  }
  if (info.has_voted) {
    area.innerHTML = `<p class="muted">Bạn đã bỏ phiếu. Đang chờ những người còn lại...</p>`;
    return;
  }

  renderSelectionGrid(area, {
    key: `day:${room.day_count}`,
    names: info.alive_players || [],
    danger: true,
    allowAbstain: true,
    abstainLabel: "Bỏ phiếu trắng",
    confirmLabel: "Khoá phiếu bầu",
    onConfirm: async (suspect) => {
      const { ok, data } = await apiPost("/api/day-vote", { room_code: session.room, voter_name: session.name, suspect_name: suspect });
      if (!ok || !data.success) return showToast(data.message || "Lỗi", true);
      showToast(data.message);
      refresh();
    },
  });
}

function renderEnd(info, room) {
  if (finalFetched) return;
  finalFetched = true;
  apiPost("/api/check-win", { room_code: session.room }).then(({ ok, data }) => {
    if (!ok || !data.success) return;
    const iWon = (data.winner === "soi" && info.role === "Ma Sói") || (data.winner === "dan" && info.role !== "Ma Sói");
    document.getElementById("end-title").textContent = data.message;
    const tag = document.getElementById("end-tag");
    tag.textContent = iWon ? "VICTORY" : "LOSE";
    tag.style.color = iWon ? "var(--green)" : "var(--red)";
    document.getElementById("end-role-reveal").textContent = `Vai trò của bạn là: ${info.role}`;
    document.getElementById("result-body").innerHTML = (data.results || []).map(r => `
      <tr>
        <td>${r.name}${r.was_chief ? ' <span class="host-badge">TL</span>' : ''}</td>
        <td>${r.role}</td>
        <td class="${r.result === 'VICTORY' ? 'result-victory' : 'result-lose'}">${r.result}</td>
      </tr>
    `).join("");
  });
}

document.getElementById("back-to-home-btn").addEventListener("click", () => {
  window.location.href = "/";
});

refresh();
setInterval(refresh, 2500);
