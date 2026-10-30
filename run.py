import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print("=" * 60)
    print("🛫 Airborne Aviation Academy - 24/7 AI Flight Assistant")
    print(f"📍 Running on: http://0.0.0.0:{port}")
    print(f"📄 Main Demo Website: http://localhost:{port}")
    print(f"🌐 Third-Party Embed Demo: http://localhost:{port}/embed-demo")
    print(f"📦 Standalone Widget JS: http://localhost:{port}/widget.js")
    print("=" * 60)
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=False)
