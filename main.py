from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import os
import traceback

from dotenv import load_dotenv
load_dotenv()

from inbody_extractor import InBodyExtractor

# =========================
# App Setup
# =========================
app = FastAPI(
    title="InBody OCR API",
    description="Extract body composition data from InBody images",
    version="1.0"
)

print("🚀 App starting...")

# =========================
# Init Extractor
# =========================
try:
    extractor = InBodyExtractor()
    print("✅ Extractor initialized")
except Exception as e:
    print("❌ Failed to init extractor:", str(e))
    extractor = None


# =========================
# Health Check
# =========================
@app.get("/")
def root():
    return {"message": "InBody API is running 🚀"}


# =========================
# Main Endpoint
# =========================
@app.post("/analyze-inbody")
async def analyze_inbody(file: UploadFile = File(...)):
    try:
        print("\n📥 New request received")

        # ✅ check extractor
        if extractor is None:
            raise HTTPException(status_code=500, detail="Extractor not initialized")

        # ✅ validate file
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="❌ لازم ترفع صورة")

        print(f"📄 File: {file.filename} | Type: {file.content_type}")

        # ✅ read image
        contents = await file.read()
        print(f"📦 File size: {len(contents)} bytes")

        # ✅ call extractor
        print("🧠 Calling extractor...")
        result = extractor.extract_from_bytes(
            image_bytes=contents,
            mime_type=file.content_type
        )

        print("✅ Extraction done")

        # ✅ check result
        if not result:
            raise HTTPException(status_code=500, detail="فشل في استخراج البيانات")

        # لو فيه error من extractor
        if isinstance(result, dict) and "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        print("📤 Sending response")

        return JSONResponse(content=result)

    except HTTPException:
        raise

    except Exception as e:
        print("❌ Unexpected Error:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# =========================
# Run (Railway compatible)
# =========================
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"🌐 Starting server on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port)