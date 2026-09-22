# Web Quản Trò Ma Sói

Web **tự đứng ra làm quản trò** — không cần một người trong bàn cầm bảng điều
khiển chung. Web tự động: chia phòng, chia vai ngẫu nhiên, lần lượt gọi từng
vai đặc biệt dậy vào ban đêm theo đúng thứ tự cổ điển (Bảo Vệ → Sói → Tiên Tri
→ Phù Thủy), tự tổng kết đêm, tự thu thập phiếu bầu ban ngày và tự xác định
phe chiến thắng.

Mỗi người chơi chỉ nhìn vào điện thoại của chính mình — không ai thấy được
thao tác của người khác, kể cả người tạo phòng (người tạo phòng chỉ là người
chơi đầu tiên vào bàn, không có đặc quyền hay màn hình riêng nào).

## Cài đặt & chạy thử

```bash
pip install -r requirements.txt
python app.py
```

Mặc định server chạy tại `http://127.0.0.1:5000`.

- Máy tính/điện thoại của mọi người cần **cùng một mạng Wi-Fi** (hoặc deploy
  lên hosting để chơi từ xa — xem mục bên dưới).
- Bất kỳ ai cũng có thể mở `http://<IP-máy-chủ>:5000/` để **tạo phòng** hoặc
  **vào phòng** bằng mã 4 số.
- Khi đủ tối thiểu 5 người, **bất kỳ ai trong phòng** cũng có thể bấm "Bắt đầu
  trò chơi".

## Cách một ván diễn ra (không cần người điều hành)

0. Vào phòng chờ (`/room`), thấy mã phòng và danh sách người chơi. Đủ tối
   thiểu 5 người, bất kỳ ai cũng bấm "Bắt đầu" được. Ngay khi game bắt đầu,
   **mọi người tự động được chuyển sang trang chơi riêng (`/game`)** — trang
   chờ và trang chơi tách biệt hẳn nhau để đỡ rối mắt.
1. Web chia vai bí mật rồi vào ngay **Đêm 1**: lần lượt gọi Bảo Vệ → Sói →
   Tiên Tri → Phù Thủy dậy (vai nào không tồn tại trong ván — ví dụ bàn 5-6
   người không có Bảo Vệ — tự động bị bỏ qua). Trước mỗi vai, web dừng 3 giây
   báo "Tiếp theo: <vai>" cho mọi người rồi mới mở nút hành động cho đúng
   người giữ vai đó; người khác chỉ thấy "đang chờ...".
   - Riêng Tiên Tri: sau khi chọn người để soi, kết quả hiện ngay trên máy
     Tiên Tri và **lượt chỉ kết thúc khi Tiên Tri tự bấm "Tiếp tục"** (không
     bị tự động chuyển lượt ngay, tránh trường hợp chưa kịp đọc kết quả).
   - Nếu một vai không thao tác gì trong 30 giây, web tự động chuyển tiếp để
     tránh treo ván.
2. Hết vai cuối cùng, web tổng kết đêm và **giữ màn hình công bố nạn nhân
   trong 5 giây**.
3. Ngay sau Đêm 1 (chỉ một lần duy nhất trong ván), web mở phiên **bầu
   Trưởng Làng**: cả làng có 45 giây bỏ phiếu cho bất kỳ ai còn sống (kể cả
   tự bầu mình). Nếu không ai bỏ phiếu hoặc phiếu bị hòa, **web tự bốc thăm
   ngẫu nhiên** một người trong nhóm phiếu cao nhất — luôn có một Trưởng Làng
   sau bước này. Trưởng Làng có **lá phiếu tính gấp đôi** trong mọi lần biểu
   quyết treo cổ ban ngày sau đó (nếu Trưởng Làng chết, phiếu của họ không
   còn tính vì người chết không được bỏ phiếu). Kết quả bầu cử hiện 5 giây
   trước khi mở phiên bỏ phiếu treo cổ Ngày 1.
4. Ban ngày, mọi người còn sống tự bỏ phiếu (hoặc bỏ phiếu trắng) trong 90
   giây. Đủ phiếu hoặc hết giờ, web tự tổng hợp, **giữ màn hình công bố người
   bị treo cổ trong 5 giây**, rồi mới chuyển sang đêm tiếp theo ("đi ngủ").
5. Web tự kiểm tra thắng/thua sau mỗi đêm và mỗi lần treo cổ; khi có phe
   thắng, tất cả được xem bảng kết quả VICTORY/LOSE và vai trò thật của mọi
   người (kèm chú thích ai từng là Trưởng Làng).

Có thể chỉnh các mốc thời gian này ở đầu `app.py` (`ELECTION_SECONDS`,
`NIGHT_SUBPHASE_SECONDS`, `SEER_RESULT_READ_SECONDS`, `DAY_VOTE_SECONDS`,
`NIGHT_PAUSE_SECONDS`, `REVEAL_SECONDS`).

## Cấu trúc dự án

```
app.py                  # Toàn bộ backend Flask + logic trò chơi (tự động hoàn toàn)
templates/
  index.html            # Trang chủ: tạo phòng / vào phòng
  room.html             # Trang PHÒNG CHỜ — chỉ hiện khi game chưa bắt đầu
  game.html             # Trang CHƠI — tự động chuyển tới khi game bắt đầu
static/
  css/style.css         # Giao diện
  js/common.js          # Tiện ích dùng chung, mô tả vai trò, avatar
  js/lobby.js           # Logic trang phòng chờ — tự chuyển sang /game khi bắt đầu
  js/game.js            # Toàn bộ logic trang chơi: bầu cử, lượt đêm, bỏ phiếu, kết quả
```

## Danh sách API

| Giai đoạn | API | Method | Endpoint |
|---|---|---|---|
| Khởi tạo | Tạo phòng | POST | `/api/create-room` |
| Khởi tạo | Tham gia phòng | POST | `/api/join-room` |
| Khởi tạo | Bắt đầu game (ai cũng bấm được) | POST | `/api/start-game` |
| Ban đêm | Bảo Vệ che chở (đúng lượt) | POST | `/api/guard-action` |
| Ban đêm | Ma Sói cắn (đúng lượt) | POST | `/api/wolf-action` |
| Ban đêm | Tiên Tri soi (đúng lượt) | POST | `/api/seer-action` |
| Ban đêm | Tiên Tri bỏ qua lượt | POST | `/api/seer-pass` |
| Ban đêm | Tiên Tri xác nhận đã đọc xong, nhường lượt | POST | `/api/seer-done` |
| Ban đêm | Phù Thủy dùng thuốc (đúng lượt) | POST | `/api/witch-action` |
| Ban đêm | Phù Thủy báo xong lượt | POST | `/api/witch-done` |
| Sau đêm 1 | Bỏ phiếu bầu Trưởng Làng | POST | `/api/election-vote` |
| Ban ngày | Bỏ phiếu treo cổ (từng người tự bỏ) | POST | `/api/day-vote` |
| Kết thúc | Kiểm tra thắng thua + bảng kết quả | POST | `/api/check-win` |
| Hỗ trợ | Trạng thái phòng (public) | GET | `/api/room-state` |
| Hỗ trợ | Vai trò + lượt của riêng tôi | GET | `/api/my-role` |

Việc tổng kết đêm, tổng kết bầu cử và tổng kết ngày đều diễn ra **tự động
bên trong** các hàm `_finish_night_actual()` / `resolve_election()` /
`_finish_day_actual()` khi hết lượt hoặc hết giờ — không có API "tổng kết"
nào cần người bấm thủ công.

## Cách chia vai theo số người

Áp dụng đúng bảng thiết lập đã thiết kế: 5-6 người (Sói, Tiên Tri, Phù Thủy,
Dân Làng), 8-9, 10-11, 12-13, 14, 15, 16, 17, 18 người với các vai bổ sung
(Bảo Vệ, Thợ Săn, Thần Tình Yêu, Trưởng Làng, Thổi Sáo, Ăn Trộm, Phản Bội...).
Trên 18 người, hệ thống tự mở rộng thêm Sói và Dân Làng theo tỉ lệ hợp lý.
7 người (không có trong bảng gốc) được nội suy: Sói, Tiên Tri, Bảo Vệ, Phù Thủy
+ Dân Làng.

Lưu ý: vai bài "Trưởng Làng" trong bảng chia vai (chỉ xuất hiện ở bàn 16+
người) là một vai đặc biệt riêng, khác với chức "Trưởng Làng" mà cả làng tự
bầu sau đêm 1 — hai khái niệm trùng tên nhưng độc lập với nhau.

## Những gì đã sửa/thêm theo báo cáo test mới nhất

- **Tách trang phòng chờ và trang chơi**: trước đây mọi thứ dồn chung một
  trang khiến giao diện rối. Giờ vào phòng chỉ thấy màn hình chờ đơn giản
  (`/room`); ngay khi có người bấm "Bắt đầu", **tất cả tự động được chuyển
  sang trang chơi riêng** (`/game`) — mỗi trang chỉ tập trung vào đúng một
  việc.
- **Dời bầu Trưởng Làng sang sau Đêm 1**: trước đây bầu ngay khi vừa chia
  vai (trước khi ai biết gì); giờ diễn ra sau khi qua đêm đầu tiên, đúng
  nhịp chơi cổ điển.
- **Bầu Trưởng Làng luôn ra kết quả**: nếu không ai bỏ phiếu hoặc phiếu bị
  hòa, hệ thống **tự bốc thăm ngẫu nhiên** trong nhóm phiếu cao nhất — không
  còn tình trạng "không bầu được ai".
- **Tiên Tri không còn bị cướp lượt quá nhanh**: trước đây vừa chọn xong
  người để soi là hệ thống lập tức chuyển sang vai kế tiếp, khiến kết quả
  hiện chưa tới 5 giây đã biến mất. Giờ Tiên Tri **giữ nguyên lượt và xem
  kết quả bao lâu tuỳ ý**, tự bấm "Tiếp tục" khi đã đọc xong mới nhường lượt
  (có hạn 30s dự phòng nếu quên bấm, để ván không bị treo).

## Giao diện

Giao diện theo phong cách bảng điều khiển tối màu, viền cyan phát sáng —
người chơi chọn mục tiêu bằng cách bấm vào thẻ avatar rồi bấm nút "khoá lựa
chọn" (áp dụng cho Sói, Bảo Vệ, Phù Thủy, bỏ phiếu ngày và bầu Trưởng Làng);
kết quả mỗi lượt (nạn nhân, người bị treo cổ, Trưởng Làng mới) hiện thành
thẻ avatar kèm icon riêng thay vì chỉ một dòng chữ.

## Những gì đã sửa ở các vòng test trước
  Trước đây người tạo phòng vừa là "quản trò" vừa có thể trúng vai Ma Sói,
  khiến việc họ thao tác trên màn hình chung bị lộ vai. Giờ mỗi người chỉ có
  đúng một màn hình cá nhân, không ai có đặc quyền hay thao tác thay người
  khác.
- **Thêm đúng thứ tự gọi dậy ban đêm**: Bảo Vệ → Sói → Tiên Tri → Phù Thủy,
  từng vai chỉ thấy nút hành động khi đến đúng lượt của mình.
- **Tự động hoàn toàn**: tổng kết đêm, thu phiếu và treo cổ ban ngày, kiểm
  tra thắng/thua đều do server tự thực hiện (có cơ chế tự chuyển lượt sau 30s
  và tự chốt phiếu bầu sau 90s nếu chưa đủ người thao tác).
- Vẫn giữ các lỗi đã sửa ở bản trước: Phù Thủy không còn dùng chung biến với
  Bảo Vệ, mỗi bình thuốc chỉ dùng được một lần trong cả ván, mỗi hành động
  đêm đều xác thực đúng vai trò và còn sống.

## Giới hạn hiện tại / hướng mở rộng

Các vai trò đặc biệt khác (Thợ Săn bắn trả, Thần Tình Yêu ghép đôi, Trưởng
Làng 2 phiếu, Thổi Sáo, Ăn Trộm, Phản Bội, Cô Bé...) vẫn được **chia vai**
đúng số lượng cho các bàn lớn, nhưng hành động riêng của họ chưa có API tự
động — người giữ vai này tạm thời chỉ tham gia bỏ phiếu ban ngày như dân
thường, chưa có màn hình thao tác đêm riêng.

Dữ liệu phòng lưu trong RAM, mất khi tắt server — phù hợp cho một buổi chơi.
Muốn lưu nhiều bàn cùng lúc lâu dài hơn thì có thể thay bằng Redis/SQLite.

## Chơi online với bạn ở xa (deploy lên hosting)

Vì dữ liệu phòng (`rooms`) chỉ lưu trong RAM của **một tiến trình**, khi deploy
bạn phải chạy **đúng 1 instance / 1 worker**. Nếu chạy nhiều worker hoặc nhiều
instance, mỗi cái sẽ có bộ nhớ `rooms` riêng và người chơi có thể bị "vào
phòng không tồn tại" dù người khác vừa tạo. `Procfile` đã cấu hình sẵn
`--workers 1` cho đúng yêu cầu này.

### Deploy lên Render.com (miễn phí, có link cố định dạng `https://ten-app.onrender.com`)

1. Đưa code lên GitHub: tạo repo mới, `git init && git add . && git commit -m "init" && git push`.
2. Vào [render.com](https://render.com) → đăng ký/đăng nhập bằng GitHub.
3. **New +** → **Web Service** → chọn repo vừa đẩy lên.
4. Điền cấu hình:
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --workers 1 --threads 8 --timeout 120`
   - **Instance Type**: Free
5. Bấm **Create Web Service**, đợi build xong (1-2 phút) là có link
   `https://ten-app.onrender.com` dùng được cho mọi người ở bất kỳ đâu.

Lưu ý gói Free của Render sẽ "ngủ" sau ~15 phút không có ai truy cập, và khi
có người vào lại sẽ mất khoảng 30-60 giây khởi động lại — **đồng thời dữ liệu
phòng cũ sẽ mất** vì server restart. Với một buổi chơi thì không sao, chỉ cần
tạo phòng mới sau khi server tỉnh dậy. Muốn server không ngủ và bền hơn thì
nâng cấp gói trả phí, hoặc dùng Railway/Fly.io (cấu hình tương tự, cũng cần
`--workers 1`).

