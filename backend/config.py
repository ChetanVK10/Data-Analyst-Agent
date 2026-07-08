import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# Load environment variables
load_dotenv(override=True)

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is missing or empty. "
        "Please ensure it is defined in your `.env` file in the project root directory, "
        "e.g. DATABASE_URL=postgresql://user:password@localhost:5432/autonomous_data_analyst"
    )

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
