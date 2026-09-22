const session = getSession();
if (!session.room || !session.name) {
  window.location.href = "/";
}

document.getElementById("room-code-big").textContent = session.room;

async function refresh() {
  const { ok, data } = await apiGet(`/api/my-role?room_code=${session.room}&name=${encodeURIComponent(session.name)}`);
  if (!ok || !data.success) {
    // Có thể phòng chưa từng có vai trò của mình (game chưa bắt đầu) -> dùng room-state thay thế
    const alt = await apiGet(`/api/room-state?room_code=${session.room}`);
    if (!alt.ok || !alt.data.success) {
      showToast(data.message || "Mất kết nối với phòng", true);
      return;
    }
    render(alt.data.room);
    return;
  }
  render(data.room);
}

function render(room) {
  if (room.is_started) {
    // Trò chơi đã bắt đầu — chuyển hẳn sang trang chơi riêng
    window.location.href = "/game";
    return;
  }

  document.getElementById("player-count").textContent = room.players.length;
  document.getElementById("player-list").innerHTML = room.players.map(p => `
    <div class="player-row-v2">
      <span class="avatar-status">
        <span class="avatar" style="background:${avatarColor(p.name)}">${initials(p.name)}</span>
      </span>
      <span class="name">${p.name}</span>
    </div>
  `).join("");

  const startBtn = document.getElementById("start-btn");
  if (room.players.length >= 5) {
    startBtn.disabled = false;
    startBtn.textContent = `BẮT ĐẦU TRÒ CHƠI (${room.players.length} NGƯỜI)`;
  } else {
    startBtn.disabled = true;
    startBtn.textContent = `CẦN THÊM NGƯỜI CHƠI (${room.players.length}/5)`;
  }
}

document.getElementById("start-btn").addEventListener("click", async () => {
  const { ok, data } = await apiPost("/api/start-game", { room_code: session.room });
  if (!ok || !data.success) return showToast(data.message || "Không thể bắt đầu", true);
  window.location.href = "/game";
});

refresh();
setInterval(refresh, 2000);
