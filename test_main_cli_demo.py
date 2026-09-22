import random

class Player:
    def __init__(self, name):
        self.name = name
        self.role = None
        self.is_alive = True
        self.protected = False

class WerewolfGame:
    def __init__(self, player_names):
        if len(player_names) < 5:
            raise ValueError("Cần ít nhất 5 người chơi để bắt đầu!")
        self.players = [Player(name) for name in player_names]
        self.day_count = 0
        self.assign_roles()

    def assign_roles(self):
        num_players = len(self.players)
        random.shuffle(self.players)
        
        # Thiết lập phân vai linh hoạt (bao gồm cả nhóm nhỏ 5-6 người theo đề xuất)
        if num_players <= 6:
            roles = ["Ma Sói", "Tiên Tri", "Phù Thủy"] + ["Dân Làng"] * (num_players - 3)
        elif 8 <= num_players <= 9:
            roles = ["Ma Sói", "Ma Sói", "Tiên Tri", "Bảo Vệ"] + ["Dân Làng"] * (num_players - 4)
        else:
            # Mặc định cơ bản cho các nhóm lớn hơn
            roles = ["Ma Sói", "Ma Sói", "Tiên Tri", "Bảo Vệ", "Thợ Săn"] + ["Dân Làng"] * (num_players - 5)
        
        # Gán role cho từng người
        for i, player in enumerate(self.players):
            player.role = roles[i]

    def show_status(self):
        print("\n" + "="*30)
        print(f" DANH SÁCH NGƯỜI CHƠI (Ngày {self.day_count}) ")
        print("="*30)
        for p in self.players:
            trang_thai = "Sống 🟢" if p.is_alive else "Đã chết 💀"
            print(f"- {p.name}: {trang_thai} (Vai trò ẩn)")

    def check_win_condition(self):
        wolves = [p for p in self.players if p.role == "Ma Sói" and p.is_alive]
        villagers = [p for p in self.players if p.role != "Ma Sói" and p.is_alive]
        
        if len(wolves) == 0:
            print("\n🎉 PHE DÂN LÀNG CHIẾN THẮNG (VICTORY)! 🎉")
            return True
        elif len(wolves) >= len(villagers):
            print("\n🐺 PHE MA SÓI CHIẾN THẮNG (VICTORY)! 🐺")
            return True
        return False

    def start_game(self):
        print("Trò chơi Ma Sói bắt đầu! Đã phân vai xong ẩn danh.")
        for p in self.players:
            print(f"[Hệ thống nội bộ] {p.name} nhận vai: {p.role}") # Dùng để test
        
        while True:
            self.day_count += 1
            print(f"\n--- ĐÊM THỨ {self.day_count} ---")
            
            # --- PHA BAN ĐÊM ---
            # 1. Sói chọn nạn nhân
            wolves = [p for p in self.players if p.role == "Ma Sói" and p.is_alive]
            if wolves:
                target = random.choice([p for p in self.players if p.is_alive and p.role != "Ma Sói"])
                print(f"Sói đã chọn mục tiêu ban đêm.")
            
            # 2. Tiên tri soi
            seers = [p for p in self.players if p.role == "Tiên Tri" and p.is_alive]
            if seers:
                print(f"Tiên tri [{seers[0].name}] đang soi danh tính...")

            # --- PHA BAN NGÀY ---
            print(f"\n--- TRỜI SÁNG (NGÀY {self.day_count}) ---")
            # Giả lập loại ngẫu nhiên hoặc treo cổ để test vòng lặp
            alive_players = [p for p in self.players if p.is_alive]
            if not alive_players:
                break
                
            victim = random.choice(alive_players)
            victim.is_alive = False
            print(f"Thông báo: {victim.name} đã bị loại trong đêm/treo cổ.")

            self.show_status()

            if self.check_win_condition():
                break
            
            input("\nNhấn Enter để chuyển sang ngày tiếp theo...")

# --- KHỞI CHẠY THỬ NGHIỆM ---
if __name__ == "__main__":
    danh_sach_ban = ["An", "Bình", "Chi", "Dũng", "Hà", "Nam"]
    game = WerewolfGame(danh_sach_ban)
    game.start_game()