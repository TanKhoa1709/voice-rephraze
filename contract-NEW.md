
## API Endpoints cho Style Management

### 1. GET /styles

**Mô tả:** Lấy danh sách tất cả các phong cách viết mô tả sản phẩm

**Request:** Không có body

**Response:**

```json
[
  {
    "name": "văn minh",
    "description": "Phong cách lịch sự, trang trọng, sử dụng từ ngữ chuẩn mực"
  },
  {
    "name": "văn hoá người tày",
    "description": "Kết hợp yếu tố văn hóa dân tộc Tày, sử dụng hình ảnh và từ ngữ đặc trưng"
  },
  {
    "name": "tan",
    "description": "Phong cách cá nhân hóa của người dùng"
  },
  {
    "name": "chuyên nghiệp",
    "description": "Ngôn ngữ nghiệp vụ, rõ ràng, tập trung vào thông số kỹ thuật"
  },
  {
    "name": "thân thiện",
    "description": "Giọng điệu gần gũi, ấm áp, dễ tiếp cận với khách hàng"
  }
]
```

----------

### 2. POST /add-style

**Mô tả:** Thêm phong cách tùy chỉnh của người dùng vào danh sách

**Request Body:**

```json
{
  "style": "phong cách cổ điển",
  "description": "Sử dụng từ ngữ tao nhã, trịnh trọng, mang đậm văn hóa truyền thống"
}
```

----------

### 3. POST /gen

**Mô tả:** Tạo mô tả sản phẩm mới theo phong cách đã chọn (style là cái variant filler th, còn phải đi kèm với prompt template)

**Request Body:**

```json
{
  "style": "văn hoá người tày",
  "product_description": "Áo dài truyền thống màu đỏ, chất liệu lụa cao cấp"
}

```

**Prompt Template (tham khảo only)**

```
Bạn hãy đọc product description: ${product_description} 
và tạo lại description theo phong cách: ${style}

```

**Response:**

```json
{
  "original_description": "Áo dài truyền thống màu đỏ, chất liệu lụa cao cấp",
  "style": "văn hoá người tày",
  "generated_description": "Sắc pỉu slính (đỏ) rực rỡ như ngày tết, áo dài may từ lụa mềm mại như dòng suối Nậm Rô...",
  "generated_at": "2026-01-24T10:35:00Z"
}

```

### 4. POST /stt

**Mô tả:** Chuyển đổi giọng nói tiếng Việt thành văn bản, sử dụng model [PhoWhisper](https://github.com/VinAIResearch/PhoWhisper)

**Request:**

Content-Type: `multipart/form-data`

`file` | `File` | File audio cần chuyển đổi (hỗ trợ `.wav`, `.mp3`, `.flac`, `.ogg`)

**Response (200 OK):**

```json
{
  "data": "áo dài truyền thống màu đỏ chất liệu lụa cao cấp"
}
```
