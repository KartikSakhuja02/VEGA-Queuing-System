from fastapi import FastAPI, UploadFile, File, Header, HTTPException
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from PIL import Image
import torch
import io

app = FastAPI()

# 🔐 simple auth token (change this)
API_TOKEN = "my_secure_token"

print("Loading model... (this will take time once)")
model = Qwen2VLForConditionalGeneration.from_pretrained(
    "Qwen/Qwen2-VL-2B-Instruct",
    torch_dtype=torch.float16,
    device_map="auto"
)
processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-2B-Instruct")
print("Model loaded.")

@app.post("/ocr")
async def ocr(file: UploadFile = File(...), authorization: str = Header(None)):
    # Debug auth header to diagnose 401 issues
    print(f"[ocr] Authorization header raw: {authorization!r}")

    # 🔐 Basic auth check (robust bearer parsing)
    auth_value = (authorization or "").strip()
    if not auth_value.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    token = auth_value.split(" ", 1)[1].strip()
    if token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    image_bytes = await file.read()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    messages = [{
        "role": "user",
        "content": [
            {"type": "image", "image": image},
            {"type": "text", "text": "Extract all text from this image."}
        ]
    }]

    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    inputs = processor(
        text=[text],
        images=[image],
        return_tensors="pt"
    ).to(model.device)

    with torch.no_grad():
        output = model.generate(**inputs, max_new_tokens=512)

    result = processor.batch_decode(output, skip_special_tokens=True)[0]

    return {"text": result}