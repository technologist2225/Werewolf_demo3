// Tiện ích dùng chung cho các trang

async function apiPost(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  const data = await res.json().catch(() => ({}));
  return { ok: res.ok, data };
}

async function apiGet(url) {
  const res = await fetch(url);
  const data = await res.json().catch(() => ({}));
  return { ok: res.ok, data };
}

function showToast(message, isError) {
  let toast = document.getElementById("toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "toast";
    toast.className = "toast";
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.classList.toggle("error", !!isError);
  toast.classList.add("show");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => toast.classList.remove("show"), 3200);
}

function phaseTag(phase) {
  const map = {
    lobby: { text: "Phòng chờ", cls: "tag-lobby" },
    election: { text: "Bầu Trưởng Làng", cls: "tag-day" },
    transition: { text: "Đang chuyển cảnh", cls: "tag-night" },
    night: { text: "Ban đêm", cls: "tag-night" },
    day: { text: "Ban ngày", cls: "tag-day" },
    ended: { text: "Kết thúc", cls: "tag-ended" },
  };
  const info = map[phase] || map.lobby;
  return `<span class="tag ${info.cls}">${info.text}</span>`;
}

function getSession() {
  return {
    room: localStorage.getItem("mawoi_room") || "",
    name: localStorage.getItem("mawoi_name") || "",
  };
}

function setSession(room, name) {
  localStorage.setItem("mawoi_room", room);
  localStorage.setItem("mawoi_name", name);
}

const ROLE_INFO = {
  "Ma Sói": { side: "Phe Sói", desc: "Mỗi đêm, cùng bầy chọn một người để tiêu diệt. Ban ngày phải giả làm dân, tránh bị treo cổ." },
  "Tiên Tri": { side: "Phe Dân", desc: "Mỗi đêm được soi một người để biết họ có phải Ma Sói hay không." },
  "Bảo Vệ": { side: "Phe Dân", desc: "Mỗi đêm che chở một người, giúp họ miễn nhiễm với vết cắn của Sói đêm đó." },
  "Phù Thủy": { side: "Phe Dân", desc: "Có một bình cứu và một bình độc, mỗi bình chỉ dùng được một lần trong cả ván." },
  "Thợ Săn": { side: "Phe Dân", desc: "Nếu bị loại, có thể bắn theo một người khác. (Web sẽ hướng dẫn khi bạn bị loại)" },
  "Thần Tình Yêu": { side: "Phe Dân", desc: "Đêm đầu tiên chọn hai người thành đôi uyên ương gắn kết số phận." },
  "Trưởng Làng": { side: "Phe Dân", desc: "Vai đặc biệt cho bàn lớn. Lưu ý: chức Trưởng Làng thật trong ván này do cả làng tự bầu ở đầu ván, không nhất thiết là vai bài này." },
  "Thổi Sáo": { side: "Phe thứ ba", desc: "Mỗi đêm thôi miên hai người. Thắng khi tất cả người còn sống đều bị thôi miên." },
  "Ăn Trộm": { side: "Phe thứ ba", desc: "Đêm đầu tiên được đổi sang một trong hai vai dự phòng." },
  "Phản Bội": { side: "Phe thứ ba", desc: "Ban đầu là dân nhưng nếu bị Sói cắn mà không chết, sẽ ngả theo phe Sói." },
  "Dân Làng": { side: "Phe Dân", desc: "Không có khả năng đặc biệt. Dùng lý lẽ và quan sát để tìm ra Sói vào ban ngày." },
};

function roleInfo(role) {
  return ROLE_INFO[role] || { side: "", desc: "Hãy chờ hướng dẫn tiếp theo." };
}

const NIGHT_STEPS = [
  { key: "guard", label: "Bảo Vệ" },
  { key: "wolf", label: "Ma Sói" },
  { key: "seer", label: "Tiên Tri" },
  { key: "witch", label: "Phù Thủy" },
];

function initials(name) {
  const parts = name.trim().split(/\s+/);
  const last = parts[parts.length - 1] || name;
  return last.slice(0, 2).toUpperCase();
}

function avatarColor(name) {
  const colors = ["#22e0ff", "#38e29b", "#ffb84d", "#ff4d5e", "#9d8cff", "#5fd0d0"];
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) >>> 0;
  return colors[hash % colors.length];
}

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[ch]));
}

/**
 * Dựng một lưới thẻ avatar để chọn mục tiêu (giống kiểu "chọn rồi khoá lựa
 * chọn" trong ảnh tham khảo), dùng chung cho Sói / Bảo Vệ / Tiên Tri /
 * Phù Thủy / bỏ phiếu ngày / bầu Trưởng Làng.
 *
 * options:
 *   key         - QUAN TRỌNG: chuỗi định danh trạng thái hiện tại (vd
 *                 "day:3:false"). Nếu key không đổi so với lần dựng trước,
 *                 hàm sẽ KHÔNG dựng lại DOM — tránh việc cứ vài giây poll
 *                 lại xoá mất lựa chọn người dùng đang chọn dở (bug không
 *                 bấm chọn được vì bị reset liên tục). Đổi key khi thật sự
 *                 cần dựng lại (đổi lượt, đổi ngày, đã bỏ phiếu xong...).
 *   container   - phần tử DOM sẽ chứa lưới + nút khoá
 *   names       - danh sách tên hiển thị làm thẻ chọn
 *   selfName    - tên của người đang xem (gắn nhãn "(bạn)")
 *   allowAbstain- có thêm thẻ "bỏ qua/không bầu/bỏ phiếu trắng" hay không
 *   abstainLabel- nhãn cho thẻ bỏ qua đó
 *   confirmLabel- chữ trên nút khoá lựa chọn
 *   danger      - tô viền đỏ khi chọn (dùng cho hành động của Sói/đầu độc)
 *   onConfirm   - callback(selectedNameOrEmptyString) khi bấm nút khoá
 */
function renderSelectionGrid(container, {
  key, names, selfName = null, allowAbstain = false, abstainLabel = "Bỏ qua",
  confirmLabel = "Khoá lựa chọn", danger = false, onConfirm,
}) {
  if (key && container.dataset.gridKey === key) {
    return; // trạng thái không đổi — giữ nguyên DOM để không mất lựa chọn đang chọn dở
  }
  if (key) container.dataset.gridKey = key;

  let selected = null;

  const cardHtml = (name, isAbstain) => `
    <div class="avatar-card ${isAbstain ? "abstain-card" : ""}" data-name="${escapeHtml(name)}">
      <div class="avatar-card-ring">
        ${isAbstain
          ? `<span class="avatar avatar-abstain">–</span>`
          : `<span class="avatar" style="background:${avatarColor(name)}">${initials(name)}</span>`}
      </div>
      <div class="avatar-card-name">${escapeHtml(name)}${name === selfName ? " (bạn)" : ""}</div>
    </div>
  `;

  const cards = names.map(n => cardHtml(n, false)).join("") + (allowAbstain ? cardHtml(abstainLabel, true) : "");

  container.innerHTML = `
    <div class="avatar-grid ${danger ? "danger" : ""}">${cards}</div>
    <button class="btn-lockin ${danger ? "danger" : ""}" id="grid-lockin-btn" disabled>${confirmLabel}</button>
  `;

  const abstainName = allowAbstain ? abstainLabel : null;

  container.querySelectorAll(".avatar-card").forEach(card => {
    card.addEventListener("click", () => {
      container.querySelectorAll(".avatar-card").forEach(c => c.classList.remove("selected"));
      card.classList.add("selected");
      const rawName = card.dataset.name;
      selected = (allowAbstain && rawName === abstainName) ? "" : rawName;
      document.getElementById("grid-lockin-btn").disabled = false;
    });
  });

  document.getElementById("grid-lockin-btn").addEventListener("click", () => {
    if (selected === null) return;
    onConfirm(selected);
  });
}
