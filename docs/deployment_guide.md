# Hướng dẫn triển khai miễn phí (M9-T04)

Kiến trúc và lý do chọn: `docs/11_free_deployment.md` (phương án A). Tóm tắt:
- **Giao diện** chạy trên **Vercel** (bản build tĩnh).
- **API, database, model embedding** chạy trên **một máy chủ ảo miễn phí**, sau **Caddy** (HTTPS tự động).

> Các bước cần tài khoản, thẻ xác minh và secret chỉ **bạn** làm được. Điều khoản miễn phí thay đổi thường xuyên: kiểm tra trang chính thức của nhà cung cấp trước khi đăng ký.

## Đã kiểm tra gì trong repo (2026-11-06)

Stack `deploy/docker-compose.prod.yml` đã chạy thật trên máy phát triển với `API_DOMAIN=localhost`:
- API trả lời qua HTTPS; HTTP tự chuyển sang HTTPS.
- Có header HSTS, `nosniff` và `X-Frame-Options`; không lộ header `Server`.
- CORS chỉ cho phép đúng origin đã khai báo.
- Đăng nhập sai bị khóa sau số lần cấu hình (trả 429).
- Cổng database 5432 và backend 8000 không mở ra mạng.

**Chưa thử:**
- trên máy chủ thật, với tên miền thật (chứng chỉ Let's Encrypt);
- trên Vercel thật.

## Yêu cầu máy chủ

- Linux 64-bit, có Docker Engine và plugin Compose.
- RAM tối thiểu khoảng 2 GB: model embedding khoảng 0,93 GB, cộng PostgreSQL và hệ điều hành (số đo ở `docs/11_free_deployment.md` mục 4.1).
- Ổ đĩa trống khoảng 6 GB (image backend 2,2 GB, model, database).
- Mở cổng 80 và 443. Cổng 80 cần cho Let's Encrypt xác minh tên miền.

## Bước 1. Tên miền cho API

Cần một tên miền (hoặc tên miền phụ miễn phí từ dịch vụ DNS động) có bản ghi **A** trỏ về IP công khai của máy chủ, ví dụ `api.ten-cua-ban.example`.

## Bước 2. Cài đặt trên máy chủ

```bash
git clone <địa chỉ repo của bạn> ai-evaluation-platform
cd ai-evaluation-platform
cp deploy/production.env.example deploy/production.env
nano deploy/production.env
```

Điền `deploy/production.env`:
- `API_DOMAIN`: tên miền ở bước 1.
- `CORS_ALLOWED_ORIGINS`: địa chỉ Vercel (điền tạm, sửa sau bước 4).
- `POSTGRES_PASSWORD` và `JWT_SECRET`: tạo bằng các lệnh ghi trong file mẫu.

File này nằm ngoài Git (`.gitignore`); không gửi nó cho ai.

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/production.env up -d --build
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/production.env ps
curl https://api.ten-cua-ban.example/health      # mong đợi {"status":"ok","database":"ok"}
```

Lần đầu mất vài phút: dựng image, tải model embedding vào volume `models`, Caddy xin chứng chỉ.

## Bước 3. Giao diện trên Vercel

1. Đưa repo lên GitHub (repo hiện **chưa có remote**; bạn tự tạo).
2. Trên Vercel: **Add New Project** → chọn repo → **Root Directory = `frontend`**. Framework Vite được nhận tự động.
3. Biến môi trường `VITE_API_BASE_URL = https://api.ten-cua-ban.example`.
   - Mọi biến `VITE_*` đều **công khai** trong trình duyệt; không đặt secret ở đây.
4. Deploy. `frontend/vercel.json` đưa mọi đường dẫn về `index.html`, để tải lại trang `/documents` không bị 404.

## Bước 4. Nối hai phần

1. Sửa `CORS_ALLOWED_ORIGINS` trong `deploy/production.env` thành đúng địa chỉ Vercel (ví dụ `https://ten-du-an.vercel.app`, không có dấu `/` ở cuối).
2. Chạy lại `up -d` để áp dụng.
3. Mở trang Vercel, đăng ký tài khoản của bạn, rồi upload một tài liệu thử.
4. **Đóng đăng ký:** đặt `REGISTRATION_ENABLED=false` và chạy lại `up -d`. Bản demo công khai thì không nên để ai cũng đăng ký được.

## Bước 5 (tùy chọn). LLM

Điền `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` (dịch vụ tương thích OpenAI Chat Completions) rồi chạy lại `up -d`. Khi chưa điền, hệ thống chạy chế độ trích đoạn.

Lưu ý:
- Gói miễn phí của LLM thường có hạn mức. Bộ đánh giá và kiểm thử bảo mật gọi LLM nhiều lần mỗi lượt.
- Tài liệu bạn upload sẽ được gửi tới LLM; đọc chính sách dữ liệu của gói miễn phí.

## Vận hành

| Việc | Lệnh |
|---|---|
| Xem log | `docker compose -f deploy/docker-compose.prod.yml --env-file deploy/production.env logs -f backend` |
| Cập nhật code | `git pull` rồi chạy lại `up -d --build` (migration tự chạy khi backend khởi động) |
| Sao lưu database | `docker compose -f deploy/docker-compose.prod.yml --env-file deploy/production.env exec db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > ~/backup-$(date +%F).sql`. File sao lưu chứa toàn bộ dữ liệu người dùng nên được lưu **ngoài** thư mục repo; `.gitignore` cũng loại `*.sql` để phòng hờ |
| Dừng | `... down` (giữ dữ liệu). **Không** thêm `-v` nếu không muốn mất database, file upload và model |

## Giới hạn đã biết

- **Một tiến trình backend:**
  - Tác vụ nền (xử lý tài liệu, đánh giá, kiểm thử, benchmark) chạy trong tiến trình web. Khởi động lại thì tác vụ dở bị đánh dấu lỗi.
  - Bộ đếm giới hạn đăng nhập nằm trong bộ nhớ.
  - Không chạy nhiều worker hay nhiều máy khi chưa có hàng đợi và kho dùng chung.
- **IP người dùng thật:**
  - Trên Linux, Docker giữ nguyên IP nguồn khi chuyển cổng, nên Caddy và backend thấy IP thật.
  - Trên Docker Desktop (Windows, macOS) mọi request có vẻ đến từ cùng một IP gateway, nên giới hạn theo IP gộp chung mọi người. Chỉ dùng Docker Desktop để thử.
- Bản demo không có khôi phục mật khẩu hay xác minh email.
