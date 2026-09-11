import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Enable CORS for the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

url: str = os.environ.get("VITE_SUPABASE_URL")
key: str = os.environ.get("VITE_SUPABASE_ANON_KEY")

if not url or not key:
    raise ValueError("Supabase URL and Key must be set in .env")

supabase: Client = create_client(url, key)

@app.get("/")
def read_root():
    return {"message": "Expense Claims API is running"}

@app.get("/api/test-db")
def test_db_connection():
    try:
        # Fetch up to 5 claims from the database to test connection
        response = supabase.table("claims").select("*").limit(5).execute()
        return {
            "status": "success",
            "message": "Successfully connected to Supabase Database via FastAPI!",
            "data": response.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
