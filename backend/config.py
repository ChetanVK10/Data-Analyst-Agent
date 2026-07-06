import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# Load environment variables
load_dotenv()

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")

# Sandbox limits
SANDBOX_TIMEOUT_SECONDS = int(os.getenv("SANDBOX_TIMEOUT_SECONDS", "10"))
SANDBOX_MEMORY_LIMIT_MB = int(os.getenv("SANDBOX_MEMORY_LIMIT_MB", "256"))

def get_llm(temperature: float = 0.0) -> ChatGroq:
    """
    Initializes and returns the ChatGroq model (using Llama 3.3 70B).
    """
    if not GROQ_API_KEY:
        # Fallback for debugging, but in real setting GROQ_API_KEY is required
        raise ValueError("GROQ_API_KEY environment variable is not set.")
    
    return ChatGroq(
        api_key=GROQ_API_KEY,
        model_name="llama-3.3-70b-versatile",
        temperature=temperature
    )
