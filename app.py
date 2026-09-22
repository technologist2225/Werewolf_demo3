# -*- coding: utf-8 -*-
"""
Web Quản Trò Ma Sói — bản KHÔNG CẦN quản trò con người.
--------------------------------------------------------
Web tự đóng vai quản trò: bầu Trưởng Làng trước đêm đầu tiên, lần lượt gọi
từng vai đặc biệt dậy vào ban đêm theo đúng thứ tự cổ điển
(Bảo Vệ → Sói → Tiên Tri → Phù Thủy), có khoảng lặng giữa các bước như MC
thật, tự công bố kết quả (nạn nhân / người bị treo cổ) rồi mới chuyển cảnh
tiếp theo, và tự kiểm tra thắng thua.

Dữ liệu lưu trong RAM (dict `rooms`), một tiến trình duy nhất (xem README).
"""

import random
import string
import time

from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Hằng số thời gian (giây)
# ---------------------------------------------------------------------------
MIN_PLAYERS = 5
ELECTION_SECONDS = 45          # thời gian bầu Trưởng Làng
NIGHT_SUBPHASE_SECONDS = 30    # mỗi vai có tối đa 30s để hành động
DAY_VOTE_SECONDS = 120         # cả làng có 2 phút để bỏ phiếu ban ngày (tự kết thúc sớm nếu ai cũng đã bỏ phiếu)
NIGHT_PAUSE_SECONDS = 3        # khoảng lặng trước khi gọi vai tiếp theo dậy
REVEAL_SECONDS = 5             # thời gian hiện kết quả (nạn nhân / người bị treo cổ) trước khi sang cảnh kế
SEER_RESULT_READ_SECONDS = 20  # thời gian riêng để Tiên Tri đọc kết quả soi trước khi tự bấm "Tiếp tục"

WOLF_ROLES = {"Ma Sói"}

NIGHT_ORDER = ["guard", "wolf", "seer", "witch"]
SUBPHASE_ROLE = {
    "guard": "Bảo Vệ",
    "wolf": "Ma Sói",
    "seer": "Tiên Tri",
    "witch": "Phù Thủy",
}
SUBPHASE_LABEL = {
    "guard": "Bảo Vệ đang che chở",
    "wolf": "Ma Sói đang chọn con mồi",
    "seer": "Tiên Tri đang soi",
    "witch": "Phù Thủy đang cân nhắc dùng thuốc",
}

rooms = {}  # room_code -> GameRoom


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
class Player:
    def __init__(self, name):
        self.name = name
        self.role = None
        self.is_alive = True
        self.witch_used_save = False
        self.witch_used_kill = False

    def to_public_dict(self):
        return {"name": self.name, "is_alive": self.is_alive}


class GameRoom:
    def __init__(self, room_code):
        self.room_code = room_code
        self.players = []
        self.is_started = False
        self.phase = "lobby"          # lobby -> election -> (transition<->night) -> (transition<->day) -> ... -> ended
        self.day_count = 0
        self.winner = None            # None | "soi" | "dan"
        self.created_at = time.time()

        # Trưởng Làng
        self.chief_name = None
        self.election_done = False    # bầu 1 lần duy nhất, ngay sau khi qua đêm đầu tiên
        self.election_votes = {}      # voter_name -> choice_name ("" = không bầu ai)
        self.election_deadline = None
        self.last_election_result = None

        # Đêm
        self.night_sequence = []      # vd ["wolf", "seer", "witch"]
        self._night_index = 0
        self.subphase = None
        self.subphase_deadline = None
        self.wolf_target = None
        self.guard_target = None
        self.witch_save_target = None
        self.witch_kill_target = None
        self.wolf_ready = set()       # đồng bộ nhiều Sói (bàn 8+ người)
        self.last_night_result = None

        # Ngày
        self.day_deadline = None
        self.votes = {}               # voter_name -> suspect_name ("" = bỏ phiếu trắng)
        self.last_day_result = None

        # Khoảng lặng / công bố kết quả dùng chung
        self.transition_deadline = None
        self.transition_message = None
        self.transition_kind = None   # "pause" | "reveal"
        self.transition_context = {}  # dữ liệu có cấu trúc để vẽ giao diện (avatar nạn nhân...)
        self.pending_action = None

        self.log = []

    # ------------------------------------------------------------------
    def find_player(self, name):
        return next((p for p in self.players if p.name == name), None)

    def alive_players(self):
        return [p for p in self.players if p.is_alive]

    def add_log(self, message):
        self.log.append({"time": time.time(), "message": message})
        self.log = self.log[-100:]

    # ------------------------------------------------------------------
    def assign_roles(self):
        n = len(self.players)
        random.shuffle(self.players)

        if n < MIN_PLAYERS:
            raise ValueError("Cần ít nhất 5 người chơi để bắt đầu!")

        if n <= 6:
            roles = ["Ma Sói", "Tiên Tri", "Phù Thủy"] + ["Dân Làng"] * (n - 3)
        elif n == 7:
            roles = ["Ma Sói", "Tiên Tri", "Bảo Vệ", "Phù Thủy"] + ["Dân Làng"] * (n - 4)
        elif 8 <= n <= 9:
            roles = ["Ma Sói", "Ma Sói", "Tiên Tri", "Bảo Vệ"] + ["Dân Làng"] * (n - 4)
        elif 10 <= n <= 11:
            roles = ["Ma Sói", "Ma Sói", "Ma Sói", "Tiên Tri", "Bảo Vệ", "Thợ Săn"] + ["Dân Làng"] * (n - 6)
        elif 12 <= n <= 13:
            roles = ["Ma Sói", "Ma Sói", "Ma Sói", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Thần Tình Yêu"] + ["Dân Làng"] * (n - 7)
        elif n == 14:
            roles = (
                ["Ma Sói", "Ma Sói", "Ma Sói", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Thần Tình Yêu", "Phù Thủy"]
                + ["Dân Làng"] * 5 + ["Phản Bội"]
            )
        elif n == 15:
            roles = (
                ["Ma Sói", "Ma Sói", "Ma Sói", "Ma Sói", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Thần Tình Yêu", "Phù Thủy"]
                + ["Dân Làng"] * 6
            )
        elif n == 16:
            roles = (
                ["Ma Sói", "Ma Sói", "Ma Sói", "Ma Sói", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Thần Tình Yêu", "Phù Thủy", "Trưởng Làng"]
                + ["Dân Làng"] * 6
            )
        elif n == 17:
            roles = (
                ["Ma Sói", "Ma Sói", "Ma Sói", "Ma Sói", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Thần Tình Yêu", "Phù Thủy", "Trưởng Làng", "Thổi Sáo"]
                + ["Dân Làng"] * 6
            )
        elif n == 18:
            roles = (
                ["Ma Sói", "Ma Sói", "Ma Sói", "Ma Sói", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Thần Tình Yêu", "Phù Thủy", "Trưởng Làng", "Thổi Sáo", "Ăn Trộm"]
                + ["Dân Làng"] * 6
            )
        else:
            special = ["Ma Sói", "Ma Sói", "Ma Sói", "Ma Sói", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Thần Tình Yêu", "Phù Thủy", "Trưởng Làng", "Thổi Sáo", "Ăn Trộm"]
            extra_wolves = max(0, (n // 4) - 4)
            roles = special + ["Ma Sói"] * extra_wolves
            roles += ["Dân Làng"] * (n - len(roles))

        for player, role in zip(self.players, roles):
            player.role = role
            player.witch_used_save = False
            player.witch_used_kill = False

        self.is_started = True
        self.day_count = 1
        self.add_log("Trò chơi bắt đầu — vai trò đã được chia bí mật cho từng người.")
        self.start_night()

    # ------------------------------------------------------------------
    # Khoảng lặng / công bố kết quả (dùng chung cho mọi lần chuyển cảnh)
    # ------------------------------------------------------------------
    def enter_transition(self, seconds, message, pending_action, kind="pause", context=None):
        self.phase = "transition"
        self.transition_deadline = time.time() + seconds
        self.transition_message = message
        self.transition_kind = kind
        self.transition_context = context or {}
        self.pending_action = pending_action

    def _resolve_transition(self):
        action, self.pending_action = self.pending_action, None
        self.transition_message = None
        self.transition_deadline = None
        if action == "start_night_subphase":
            self._activate_current_subphase()
        elif action == "after_election_reveal":
            self._open_day_actual()
        elif action == "after_night_reveal":
            self._after_night_reveal()
        elif action == "after_day_reveal":
            self._open_next_round_or_end()

    # ------------------------------------------------------------------
    # Bầu Trưởng Làng — diễn ra đúng MỘT LẦN, ngay sau khi qua đêm đầu tiên,
    # trước khi mở phiên bỏ phiếu ban ngày đầu tiên.
    # ------------------------------------------------------------------
    def _start_election_actual(self):
        self.phase = "election"
        self.election_votes = {}
        self.election_deadline = time.time() + ELECTION_SECONDS
        self.add_log("Cả làng bắt đầu bầu Trưởng Làng.")

    def cast_election_vote(self, voter_name, choice_name):
        self.election_votes[voter_name] = choice_name or ""
        if len(self.election_votes) >= len(self.alive_players()):
            self.resolve_election()

    def resolve_election(self):
        # Mỗi người còn sống là một ứng viên hợp lệ, khởi điểm 0 phiếu —
        # nhờ vậy nếu không ai bỏ phiếu (hoặc toàn bỏ phiếu trắng) thì mọi
        # người đều đang "bằng phiếu cao nhất" và vẫn bốc ngẫu nhiên được.
        tally = {p.name: 0 for p in self.alive_players()}
        for choice in self.election_votes.values():
            if choice and choice in tally:
                tally[choice] += 1

        chief = None
        if tally:
            top_votes = max(tally.values())
            top = [name for name, c in tally.items() if c == top_votes]
            # Hòa phiếu (hoặc không ai bầu ai) -> random 1 người trong nhóm cao phiếu nhất
            chief = random.choice(top)

        self.chief_name = chief
        if chief:
            msg = f"{chief} được chọn làm Trưởng Làng! Phiếu của Trưởng Làng sẽ tính gấp đôi khi biểu quyết ban ngày."
        else:
            msg = "Không có ai còn sống để làm Trưởng Làng."
        self.add_log(msg)
        self.last_election_result = {"chief": chief, "message": msg}
        self.election_votes = {}
        self.election_deadline = None
        self.enter_transition(
            REVEAL_SECONDS, msg, "after_election_reveal", kind="reveal",
            context={"type": "election_result", "chief": chief},
        )

    # ------------------------------------------------------------------
    # Ban đêm
    # ------------------------------------------------------------------
    def build_night_sequence(self):
        return [s for s in NIGHT_ORDER if any(p.role == SUBPHASE_ROLE[s] and p.is_alive for p in self.players)]

    def start_night(self):
        self.wolf_target = None
        self.guard_target = None
        self.witch_save_target = None
        self.witch_kill_target = None
        self.wolf_ready = set()   # tên các Sói đã xác nhận lựa chọn đêm nay (đồng bộ nhiều Sói)
        self.night_sequence = self.build_night_sequence()
        self._night_index = 0
        if self.night_sequence:
            self._queue_subphase_transition()
        else:
            self._finish_night_actual()

    def _queue_subphase_transition(self):
        role_key = self.night_sequence[self._night_index]
        self.subphase = role_key
        self.add_log(f"{SUBPHASE_LABEL[role_key]}...")
        self.enter_transition(
            NIGHT_PAUSE_SECONDS,
            f"Tiếp theo: {SUBPHASE_ROLE[role_key]}",
            "start_night_subphase",
            kind="pause",
            context={"type": "night_pause", "role": SUBPHASE_ROLE[role_key]},
        )

    def _activate_current_subphase(self):
        self.phase = "night"
        self.subphase_deadline = time.time() + NIGHT_SUBPHASE_SECONDS

    def advance_subphase(self):
        """Gọi sau khi vai hiện tại hành động xong (hoặc bỏ qua)."""
        self._night_index += 1
        if self._night_index < len(self.night_sequence):
            self._queue_subphase_transition()
        else:
            self._finish_night_actual()

    def _finish_night_actual(self):
        victims = []
        wolf_victim = self.wolf_target
        saved = wolf_victim is not None and (
            wolf_victim == self.guard_target or wolf_victim == self.witch_save_target
        )
        if wolf_victim and not saved:
            victims.append(wolf_victim)

        if self.witch_kill_target and self.witch_kill_target not in victims:
            victims.append(self.witch_kill_target)

        for name in victims:
            p = self.find_player(name)
            if p:
                p.is_alive = False

        if victims:
            msg = "Trời sáng! Nạn nhân đêm qua là: " + ", ".join(victims)
        else:
            msg = "Trời sáng! Đêm qua không có ai chết."
        self.add_log(msg)
        self.last_night_result = {"day": self.day_count, "victims": victims, "message": msg}

        self.subphase = None
        self.subphase_deadline = None
        self.enter_transition(
            REVEAL_SECONDS, msg, "after_night_reveal", kind="reveal",
            context={"type": "night_result", "victims": victims},
        )

    def _after_night_reveal(self):
        if self.check_win():
            return
        if not self.election_done:
            self.election_done = True
            self._start_election_actual()
        else:
            self._open_day_actual()

    def _open_day_actual(self):
        self.phase = "day"
        self.votes = {}
        self.last_day_result = None
        self.day_deadline = time.time() + DAY_VOTE_SECONDS
        self.add_log(f"Ngày {self.day_count} bắt đầu, mời cả làng bỏ phiếu.")

    # ------------------------------------------------------------------
    # Ban ngày
    # ------------------------------------------------------------------
    def cast_vote(self, voter_name, suspect_name):
        self.votes[voter_name] = suspect_name or ""
        if len(self.votes) >= len(self.alive_players()):
            self._finish_day_actual()

    def _vote_weight(self, voter_name):
        if voter_name == self.chief_name:
            voter = self.find_player(voter_name)
            if voter and voter.is_alive:
                return 2
        return 1

    def _finish_day_actual(self):
        tally = {}
        for voter, suspect in self.votes.items():
            if not suspect:
                continue
            tally[suspect] = tally.get(suspect, 0) + self._vote_weight(voter)

        hanged = None
        if tally:
            top_votes = max(tally.values())
            top = [name for name, c in tally.items() if c == top_votes]
            if len(top) == 1:
                hanged = top[0]

        if hanged:
            p = self.find_player(hanged)
            if p:
                p.is_alive = False
            msg = f"Cả làng đã bỏ phiếu treo cổ {hanged}!"
        else:
            msg = "Làng không đạt được đa số thống nhất — không ai bị treo cổ hôm nay."

        self.add_log(msg)
        self.last_day_result = {"day": self.day_count, "hanged": hanged, "message": msg}
        self.votes = {}
        self.day_deadline = None
        self.enter_transition(
            REVEAL_SECONDS, msg, "after_day_reveal", kind="reveal",
            context={"type": "day_result", "hanged": hanged},
        )

    def _open_next_round_or_end(self):
        if self.check_win():
            return
        self.day_count += 1
        self.start_night()

    # ------------------------------------------------------------------
    def tick(self):
        """Gọi ở đầu mỗi request để tự động chuyển cảnh khi hết giờ."""
        if not self.is_started or self.winner:
            return
        now = time.time()
        if self.phase == "transition" and self.transition_deadline and now >= self.transition_deadline:
            self._resolve_transition()
        elif self.phase == "election" and self.election_deadline and now >= self.election_deadline:
            self.resolve_election()
        elif self.phase == "night" and self.subphase_deadline and now >= self.subphase_deadline:
            self.add_log(f"Hết giờ chờ {SUBPHASE_ROLE.get(self.subphase, '')} — tự động chuyển tiếp.")
            self.advance_subphase()
        elif self.phase == "day" and self.day_deadline and now >= self.day_deadline:
            self._finish_day_actual()

    def check_win(self):
        alive = self.alive_players()
        wolves_alive = [p for p in alive if p.role in WOLF_ROLES]
        others_alive = [p for p in alive if p.role not in WOLF_ROLES]

        if len(wolves_alive) == 0:
            self.winner = "dan"
        elif len(wolves_alive) >= len(others_alive):
            self.winner = "soi"
        else:
            self.winner = None

        if self.winner:
            self.phase = "ended"
            self.add_log("Phe Dân Làng đã chiến thắng! 🎉" if self.winner == "dan" else "Phe Ma Sói đã chiến thắng! 🐺")
        return self.winner

    # ------------------------------------------------------------------
    def seconds_left(self):
        if self.phase == "transition":
            deadline = self.transition_deadline
        elif self.phase == "election":
            deadline = self.election_deadline
        elif self.phase == "night":
            deadline = self.subphase_deadline
        elif self.phase == "day":
            deadline = self.day_deadline
        else:
            deadline = None
        if not deadline:
            return None
        return max(0, round(deadline - time.time()))

    def to_state_dict(self):
        return {
            "room_code": self.room_code,
            "is_started": self.is_started,
            "phase": self.phase,
            "day_count": self.day_count,
            "winner": self.winner,
            "players": [p.to_public_dict() for p in self.players],
            "log": self.log[-15:],
            "subphase": self.subphase,
            "subphase_label": SUBPHASE_LABEL.get(self.subphase) if self.subphase else None,
            "night_sequence": self.night_sequence,
            "seconds_left": self.seconds_left(),
            "votes_count": len(self.votes) if self.phase == "day" else None,
            "election_votes_count": len(self.election_votes) if self.phase == "election" else None,
            "alive_count": len(self.alive_players()),
            "last_night_msg": self.last_night_result["message"] if self.last_night_result else None,
            "last_day_msg": self.last_day_result["message"] if self.last_day_result else None,
            "chief_name": self.chief_name,
            "transition_message": self.transition_message,
            "transition_kind": self.transition_kind,
            "transition_context": self.transition_context,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def error(message, code=400):
    return jsonify({"success": False, "message": message}), code


def generate_room_code():
    code = "".join(random.choices(string.digits, k=4))
    while code in rooms:
        code = "".join(random.choices(string.digits, k=4))
    return code


def get_room(room_code):
    room = rooms.get(room_code)
    if room:
        room.tick()
    return room


# ---------------------------------------------------------------------------
# Trang web
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/room")
def room_page():
    return render_template("room.html")


@app.route("/game")
def game_page():
    return render_template("game.html")


# ---------------------------------------------------------------------------
# API: Tạo phòng / Vào phòng — không có khái niệm "quản trò"
# ---------------------------------------------------------------------------
@app.route("/api/create-room", methods=["POST"])
def create_room():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return error("Vui lòng nhập tên của bạn!")

    room_code = generate_room_code()
    room = GameRoom(room_code)
    room.players.append(Player(name))
    rooms[room_code] = room

    return jsonify({"success": True, "room_code": room_code, "message": "Tạo phòng thành công!"})


@app.route("/api/join-room", methods=["POST"])
def join_room():
    data = request.get_json(silent=True) or {}
    room_code = (data.get("room_code") or "").strip()
    name = (data.get("name") or "").strip()
    if not room_code or not name:
        return error("Vui lòng nhập đầy đủ mã phòng và tên!")

    room = get_room(room_code)
    if not room:
        return error("Phòng không tồn tại!", 404)
    if room.is_started:
        return error("Trò chơi đã bắt đầu, không thể vào phòng!")
    if room.find_player(name):
        return error("Tên này đã có người dùng trong phòng, hãy chọn tên khác!")

    room.players.append(Player(name))
    room.add_log(f"{name} đã vào phòng.")

    return jsonify({"success": True, "message": f"Đã vào phòng {room_code}", "players": [p.name for p in room.players]})


@app.route("/api/start-game", methods=["POST"])
def start_game():
    data = request.get_json(silent=True) or {}
    room = get_room((data.get("room_code") or "").strip())
    if not room:
        return error("Phòng không tồn tại!", 404)
    if room.is_started:
        return error("Trò chơi đã được bắt đầu rồi!")
    if len(room.players) < MIN_PLAYERS:
        return error(f"Cần ít nhất {MIN_PLAYERS} người chơi để bắt đầu!")

    try:
        room.assign_roles()
    except ValueError as e:
        return error(str(e))

    return jsonify({"success": True, "message": "Trò chơi đã bắt đầu! Mời cả làng bầu Trưởng Làng trước."})


# ---------------------------------------------------------------------------
# Trạng thái phòng / vai trò cá nhân
# ---------------------------------------------------------------------------
@app.route("/api/room-state", methods=["GET"])
def room_state():
    room = get_room((request.args.get("room_code") or "").strip())
    if not room:
        return error("Phòng không tồn tại!", 404)
    return jsonify({"success": True, "room": room.to_state_dict()})


@app.route("/api/my-role", methods=["GET"])
def my_role():
    room = get_room((request.args.get("room_code") or "").strip())
    name = (request.args.get("name") or "").strip()
    if not room:
        return error("Phòng không tồn tại!", 404)

    player = room.find_player(name)
    if not player:
        return error("Không tìm thấy người chơi trong phòng!", 404)

    state = room.to_state_dict()
    my_turn = (
        room.phase == "night"
        and player.is_alive
        and room.subphase is not None
        and player.role == SUBPHASE_ROLE.get(room.subphase)
    )

    payload = {
        "success": True,
        "room": state,
        "name": player.name,
        "role": player.role,
        "is_alive": player.is_alive,
        "witch_used_save": player.witch_used_save,
        "witch_used_kill": player.witch_used_kill,
        "my_turn": my_turn,
        "alive_players": [p.name for p in room.players if p.is_alive and p.name != player.name],
        "all_alive_players": [p.name for p in room.players if p.is_alive],
        "has_voted": room.votes.get(player.name) is not None if room.phase == "day" else False,
        "has_voted_election": room.election_votes.get(player.name) is not None if room.phase == "election" else False,
        "is_chief": player.name == room.chief_name,
    }

    if player.role == "Phù Thủy" and room.phase == "night":
        payload["wolf_victim_hint"] = room.wolf_target

    if player.role == "Ma Sói" and room.phase == "night":
        alive_wolves = [p for p in room.players if p.role == "Ma Sói" and p.is_alive]
        payload["wolf_ready_count"] = len(room.wolf_ready)
        payload["wolf_total_count"] = len(alive_wolves)
        payload["wolf_current_target"] = room.wolf_target
        payload["i_am_ready"] = player.name in room.wolf_ready

    return jsonify(payload)


# ---------------------------------------------------------------------------
# API: Bầu Trưởng Làng
# ---------------------------------------------------------------------------
@app.route("/api/election-vote", methods=["POST"])
def election_vote():
    data = request.get_json(silent=True) or {}
    room = get_room((data.get("room_code") or "").strip())
    if not room:
        return error("Phòng không tồn tại!", 404)
    if room.phase != "election":
        return error("Không phải lúc bầu Trưởng Làng!")

    voter_name = (data.get("voter_name") or "").strip()
    choice_name = (data.get("choice_name") or "").strip()

    voter = room.find_player(voter_name)
    if not voter or not voter.is_alive:
        return error("Bạn không thể bỏ phiếu!", 403)
    if choice_name:
        choice = room.find_player(choice_name)
        if not choice or not choice.is_alive:
            return error("Người được đề cử không hợp lệ!")

    room.cast_election_vote(voter_name, choice_name)
    return jsonify({"success": True, "message": "Đã ghi nhận phiếu bầu Trưởng Làng của bạn."})


# ---------------------------------------------------------------------------
# Hành động ban đêm — chỉ chấp nhận đúng lượt
# ---------------------------------------------------------------------------
def _check_turn(room, subphase_key, player):
    if room.phase == "transition":
        return error("Đang chuyển tiếp, vui lòng đợi giây lát...")
    if room.phase != "night":
        return error("Không phải phiên ban đêm!")
    if room.subphase != subphase_key:
        return error(f"Chưa tới lượt của {SUBPHASE_ROLE[subphase_key]}, vui lòng chờ!")
    if not player or not player.is_alive:
        return error(f"Bạn không phải {SUBPHASE_ROLE[subphase_key]} còn sống!", 403)
    if player.role != SUBPHASE_ROLE[subphase_key]:
        return error(f"Bạn không phải {SUBPHASE_ROLE[subphase_key]}!", 403)
    return None


@app.route("/api/wolf-action", methods=["POST"])
def wolf_action():
    data = request.get_json(silent=True) or {}
    room = get_room((data.get("room_code") or "").strip())
    if not room:
        return error("Phòng không tồn tại!", 404)

    wolf_name = (data.get("wolf_name") or "").strip()
    target_name = (data.get("target_name") or "").strip()
    wolf_player = room.find_player(wolf_name)

    err = _check_turn(room, "wolf", wolf_player)
    if err:
        return err

    target = room.find_player(target_name)
    if not target or not target.is_alive:
        return error("Mục tiêu không hợp lệ!")

    # Bàn có nhiều Sói (8+ người): mục tiêu mới nhất được ghi nhận, nhưng
    # lượt Sói chỉ thật sự kết thúc khi TẤT CẢ Sói còn sống đã xác nhận —
    # tránh việc một Sói bấm trước làm những Sói khác bị "khoá" mất lượt.
    room.wolf_target = target_name
    room.wolf_ready.add(wolf_name)
    alive_wolves = [p for p in room.players if p.role == "Ma Sói" and p.is_alive]
    ready_count = len(room.wolf_ready)
    total_wolves = len(alive_wolves)
    room.add_log(f"Một Sói đã chọn xong mục tiêu ({ready_count}/{total_wolves}).")

    if ready_count >= total_wolves:
        room.advance_subphase()
        note = "Cả bầy đã thống nhất."
    else:
        note = f"Đang chờ {total_wolves - ready_count} Sói còn lại xác nhận..."

    return jsonify({
        "success": True,
        "message": f"Sói đã chọn tiêu diệt: {target_name}. {note}",
        "wolf_ready_count": ready_count,
        "wolf_total_count": total_wolves,
    })


@app.route("/api/guard-action", methods=["POST"])
def guard_action():
    data = request.get_json(silent=True) or {}
    room = get_room((data.get("room_code") or "").strip())
    if not room:
        return error("Phòng không tồn tại!", 404)

    guard_name = (data.get("guard_name") or "").strip()
    target_name = (data.get("target_name") or "").strip()
    guard_player = room.find_player(guard_name)

    err = _check_turn(room, "guard", guard_player)
    if err:
        return err

    target = room.find_player(target_name)
    if not target or not target.is_alive:
        return error("Mục tiêu không hợp lệ!")

    room.guard_target = target_name
    room.add_log("Bảo Vệ đã chọn xong người che chở.")
    room.advance_subphase()
    return jsonify({"success": True, "message": f"Bảo Vệ đã chọn bảo vệ: {target_name}"})


@app.route("/api/seer-action", methods=["POST"])
def seer_action():
    data = request.get_json(silent=True) or {}
    room = get_room((data.get("room_code") or "").strip())
    if not room:
        return error("Phòng không tồn tại!", 404)

    seer_name = (data.get("seer_name") or "").strip()
    target_name = (data.get("target_name") or "").strip()
    seer_player = room.find_player(seer_name)

    err = _check_turn(room, "seer", seer_player)
    if err:
        return err

    target = room.find_player(target_name)
    if not target:
        return error("Không tìm thấy mục tiêu!")

    role_hint = "Ma Sói" if target.role == "Ma Sói" else "Dân Làng/Phe Khác"
    room.add_log("Tiên Tri đã soi xong.")
    # Không tự chuyển lượt ngay — để Tiên Tri có đủ thời gian đọc kết quả rồi
    # tự bấm "Tiếp tục" (xem /api/seer-done). Gia hạn thêm thời gian đọc kết
    # quả, tách biệt với thời gian cân nhắc chọn mục tiêu ban đầu.
    room.subphase_deadline = time.time() + SEER_RESULT_READ_SECONDS
    return jsonify({"success": True, "target": target_name, "role_hint": role_hint, "message": f"Tiên tri đã soi {target_name}"})


@app.route("/api/seer-pass", methods=["POST"])
def seer_pass():
    data = request.get_json(silent=True) or {}
    room = get_room((data.get("room_code") or "").strip())
    if not room:
        return error("Phòng không tồn tại!", 404)
    seer_player = room.find_player((data.get("seer_name") or "").strip())
    err = _check_turn(room, "seer", seer_player)
    if err:
        return err
    room.add_log("Tiên Tri không soi ai đêm nay.")
    room.advance_subphase()
    return jsonify({"success": True, "message": "Đã bỏ qua lượt soi."})


@app.route("/api/seer-done", methods=["POST"])
def seer_done():
    """Tiên Tri bấm 'Tiếp tục' sau khi đã đọc xong kết quả soi."""
    data = request.get_json(silent=True) or {}
    room = get_room((data.get("room_code") or "").strip())
    if not room:
        return error("Phòng không tồn tại!", 404)
    seer_player = room.find_player((data.get("seer_name") or "").strip())
    err = _check_turn(room, "seer", seer_player)
    if err:
        return err
    room.advance_subphase()
    return jsonify({"success": True, "message": "Tiên Tri đã xong lượt."})


@app.route("/api/witch-action", methods=["POST"])
def witch_action():
    data = request.get_json(silent=True) or {}
    room = get_room((data.get("room_code") or "").strip())
    if not room:
        return error("Phòng không tồn tại!", 404)

    witch_name = (data.get("witch_name") or "").strip()
    action_type = (data.get("action_type") or "").strip().lower()
    target_name = (data.get("target_name") or "").strip()
    witch_player = room.find_player(witch_name)

    err = _check_turn(room, "witch", witch_player)
    if err:
        return err

    if action_type == "save":
        if witch_player.witch_used_save:
            return error("Bạn đã dùng bình cứu rồi!")
        if not room.wolf_target:
            return error("Đêm nay chưa có ai bị Sói cắn để cứu!")
        room.witch_save_target = room.wolf_target
        witch_player.witch_used_save = True
        room.add_log("Phù Thủy đã dùng bình cứu.")
        return jsonify({"success": True, "message": f"Đã cứu {room.wolf_target}"})

    elif action_type == "kill":
        if witch_player.witch_used_kill:
            return error("Bạn đã dùng bình độc rồi!")
        target = room.find_player(target_name)
        if not target or not target.is_alive:
            return error("Mục tiêu không hợp lệ!")
        room.witch_kill_target = target_name
        witch_player.witch_used_kill = True
        room.add_log("Phù Thủy đã dùng bình độc.")
        return jsonify({"success": True, "message": f"Đã đầu độc {target_name}"})

    elif action_type == "pass":
        room.add_log("Phù Thủy không dùng thuốc đêm nay.")
        room.advance_subphase()
        return jsonify({"success": True, "message": "Đã bỏ qua lượt."})

    return error("Hành động không hợp lệ! (action_type phải là 'save', 'kill' hoặc 'pass')")


@app.route("/api/witch-done", methods=["POST"])
def witch_done():
    """Phù Thủy bấm 'Xong lượt' sau khi đã dùng 0/1/2 bình thuốc."""
    data = request.get_json(silent=True) or {}
    room = get_room((data.get("room_code") or "").strip())
    if not room:
        return error("Phòng không tồn tại!", 404)
    witch_player = room.find_player((data.get("witch_name") or "").strip())
    err = _check_turn(room, "witch", witch_player)
    if err:
        return err
    room.advance_subphase()
    return jsonify({"success": True, "message": "Phù Thủy đã xong lượt."})


# ---------------------------------------------------------------------------
# API: Bỏ phiếu ban ngày — mọi người còn sống đều tự bỏ phiếu
# ---------------------------------------------------------------------------
@app.route("/api/day-vote", methods=["POST"])
def day_vote():
    data = request.get_json(silent=True) or {}
    room = get_room((data.get("room_code") or "").strip())
    if not room:
        return error("Phòng không tồn tại!", 404)
    if room.phase != "day":
        return error("Không phải phiên ban ngày!")

    voter_name = (data.get("voter_name") or "").strip()
    suspect_name = (data.get("suspect_name") or "").strip()

    voter = room.find_player(voter_name)
    if not voter or not voter.is_alive:
        return error("Bạn không thể bỏ phiếu (đã chết hoặc không hợp lệ)!", 403)

    if suspect_name:
        suspect = room.find_player(suspect_name)
        if not suspect or not suspect.is_alive:
            return error("Nghi phạm không hợp lệ!")

    room.cast_vote(voter_name, suspect_name)
    return jsonify({"success": True, "message": "Đã ghi nhận phiếu bầu của bạn."})


# ---------------------------------------------------------------------------
# API: Kiểm tra thắng thua (trả kết quả chi tiết từng người khi đã kết thúc)
# ---------------------------------------------------------------------------
@app.route("/api/check-win", methods=["POST"])
def check_win():
    data = request.get_json(silent=True) or {}
    room = get_room((data.get("room_code") or "").strip())
    if not room:
        return error("Phòng không tồn tại!", 404)

    winner = room.winner
    result = {"success": True, "winner": winner, "phase": room.phase}

    if winner:
        results = []
        for p in room.players:
            if winner == "soi":
                tag = "VICTORY" if p.role == "Ma Sói" else "LOSE"
            else:
                tag = "VICTORY" if p.role != "Ma Sói" else "LOSE"
            results.append({"name": p.name, "role": p.role, "result": tag, "was_chief": p.name == room.chief_name})
        result["results"] = results
        result["message"] = "Phe Ma Sói đã chiến thắng! 🐺" if winner == "soi" else "Phe Dân Làng đã chiến thắng! 🎉"
    else:
        result["message"] = "Trò chơi vẫn đang tiếp diễn."

    return jsonify(result)


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
