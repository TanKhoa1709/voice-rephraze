import os
import sqlite3
import shutil
from fastapi import FastAPI, HTTPException, File, UploadFile
from pydantic import BaseModel
from typing import List
from datetime import datetime, timezone
from openai import AsyncOpenAI
from dotenv import load_dotenv
from transformers import pipeline

# Load API Key
load_dotenv()

# Cấu hình OpenAI
client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)

AI_MODEL = "gpt-4o-mini"
DB_NAME = "styles.db"  # Tên file database sẽ được tạo ra

# Khởi tạo PhoWhisper cho Speech-to-Text
stt_pipeline = pipeline("automatic-speech-recognition", model="vinai/PhoWhisper-large")

app = FastAPI(title="AI Copywriting Service")


# --- 1. DATA MODELS ---
class Style(BaseModel):
    name: str
    description: str


class GenRequest(BaseModel):
    style: str
    product_description: str


class GenResponse(BaseModel):
    original_description: str
    style: str
    generated_description: str
    generated_at: str


# --- 2. DATABASE SETUP ---
def init_db():
    """Khởi tạo database và bảng nếu chưa có"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Tạo bảng styles
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS styles
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       name
                       TEXT
                       UNIQUE
                       NOT
                       NULL,
                       description
                       TEXT
                       NOT
                       NULL
                   )
                   ''')

    # Kiểm tra xem có dữ liệu chưa, nếu chưa thì nạp dữ liệu mẫu
    cursor.execute('SELECT count(*) FROM styles')
    if cursor.fetchone()[0] == 0:
        default_data = [
            ("văn minh", "Phong cách lịch sự, trang trọng, sử dụng từ ngữ chuẩn mực"),
            ("văn hoá người tày", "Kết hợp yếu tố văn hóa dân tộc Tày, sử dụng hình ảnh và từ ngữ đặc trưng"),
            ("tan", "Phong cách cá nhân hóa của người dùng"),
            ("chuyên nghiệp", "Ngôn ngữ nghiệp vụ, rõ ràng, tập trung vào thông số kỹ thuật"),
            ("thân thiện", "Giọng điệu gần gũi, ấm áp, dễ tiếp cận với khách hàng")
        ]
        cursor.executemany('INSERT INTO styles (name, description) VALUES (?, ?)', default_data)
        conn.commit()
        print(">>> Đã khởi tạo dữ liệu mẫu vào SQLite.")

    conn.close()


# Chạy hàm khởi tạo ngay khi file được load
init_db()


# --- 3. ENDPOINTS ---

@app.get("/styles", response_model=List[Style])
async def get_styles():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT name, description FROM styles")
    rows = cursor.fetchall()

    conn.close()

    # Chuyển đổi từng row (sqlite3.Row) thành dict chuẩn
    return [dict(row) for row in rows]


@app.post("/add-style")
async def add_style(style: Style):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute("INSERT INTO styles (name, description) VALUES (?, ?)", (style.name, style.description))
        conn.commit()
        conn.close()

        return {"message": "Style added successfully", "data": style}
    except sqlite3.IntegrityError:
        # Bắt lỗi nếu trùng tên style (do cột name là UNIQUE)
        raise HTTPException(status_code=400, detail="Style name already exists")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/gen", response_model=GenResponse)
async def generate_description(request: GenRequest):
    # 1. Lấy context từ SQLite
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Query lấy description dựa trên tên style
    cursor.execute("SELECT description FROM styles WHERE name = ?", (request.style,))
    row = cursor.fetchone()
    conn.close()

    style_context = "Viết sáng tạo, tự nhiên"  # Fallback
    if row:
        style_context = row[0]  # Lấy cột description

    # 2. Tạo Prompt
    system_prompt = """Bạn là một chuyên gia Copywriter thương mại điện tử hàng đầu, chuyên tạo ra các mô tả sản phẩm hấp dẫn, thuyết phục và tối ưu chuyển đổi.

Nhiệm vụ của bạn:
- Nhận đầu vào là một đoạn **giọng nói được chuyển thành văn bản** (speech-to-text). Đoạn văn bản này có thể lộn xộn, lặp lại, dùng từ miệng, thiếu dấu câu hoặc diễn đạt chưa rõ ràng.
- Phân tích và trích xuất các thông tin cốt lõi về sản phẩm: tên sản phẩm, chất liệu, màu sắc, tính năng, lợi ích, đối tượng sử dụng, v.v.
- Viết lại thành một mô tả sản phẩm hoàn chỉnh, trôi chảy và chuyên nghiệp theo đúng phong cách yêu cầu.

Quy tắc bắt buộc:
1. KHÔNG được bịa thêm thông tin không có trong đầu vào.
2. Bỏ qua hoàn toàn các từ miệng, tiếng ừm/à, câu lặp lại, và lỗi nói.
3. Chỉ trả về **nội dung mô tả sản phẩm** dưới dạng văn xuôi. Không giải thích, không dẫn nhập, không dấu ngoặc kép.
4. Độ dài lý tưởng: 3–5 câu súc tích nhưng đủ thuyết phục."""

    user_prompt = (
        f"""## Đầu vào từ giọng nói người dùng:
\"\"\"
{request.product_description}
\"\"\"

## Phong cách viết yêu cầu: {request.style}
## Đặc tả phong cách: {style_context}

## Hướng dẫn:
Bước 1 – Đọc kỹ đoạn giọng nói trên và xác định những thông tin quan trọng về sản phẩm (ví dụ: tên, màu sắc, chất liệu, công dụng, điểm nổi bật).
Bước 2 – Dùng các thông tin đó để viết một mô tả sản phẩm hoàn chỉnh theo phong cách \'{request.style}\' ({style_context}).

Kết quả (chỉ trả về mô tả sản phẩm, không kèm tiêu đề hay giải thích):"""
    )

    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": user_prompt
        }
    ]

    try:
        # 3. Gọi OpenAI API
        response = await client.chat.completions.create(
            model=AI_MODEL,
            messages=messages,
            temperature=0.75,
            max_tokens=600
        )

        generated_text = response.choices[0].message.content.strip()

        # 4. Trả về kết quả
        return GenResponse(
            original_description=request.product_description,
            style=request.style,
            generated_description=generated_text,
            generated_at=datetime.now(timezone.utc).isoformat()
        )

    except Exception as e:
        print(f"OpenAI Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stt")
async def speech_to_text(file: UploadFile = File(...)):
    # 1. Kiểm tra định dạng file
    allowed_extensions = ["wav", "mp3", "flac", "ogg", "m4a", "webm", "mp4", "mpeg", "mpga"]
    file_ext = file.filename.split(".")[-1].lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400,
                            detail=f"Định dạng file không được hỗ trợ. Chỉ hỗ trợ: {', '.join(allowed_extensions)}")

    # 2. Lưu file audio tạm thời
    temp_file_path = f"temp_{file.filename}"
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 3. Gọi PhoWhisper để nhận dạng giọng nói
        result = stt_pipeline(temp_file_path)

        # 4. Xóa file tạm
        os.remove(temp_file_path)

        return {"data": result["text"]}

    except Exception as e:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        print(f"STT Error: {e}")
        raise HTTPException(status_code=500, detail="Lỗi khi xử lý âm thanh")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 5001)))
