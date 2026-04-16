import subprocess
import sys

# Install dependencies
subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"])

# Start the server
import uvicorn
from main import app
from database import engine, Base

# Auto-create all tables on startup
Base.metadata.create_all(bind=engine)
print("✓ Database tables created")
print("✓ AuBit API starting...")

uvicorn.run(app, host="0.0.0.0", port=8000)
