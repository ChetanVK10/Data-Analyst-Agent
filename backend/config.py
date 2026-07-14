import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-2.5-flash")

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

def get_llm(temperature: float = 0.0):
    """
    Initializes and returns the primary ChatGroq model (Llama 3.3 70B),
    with a transparent provider-level fallback to Gemini if GOOGLE_API_KEY is present.
    """
    from langchain_groq import ChatGroq
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.language_models.chat_models import BaseChatModel

    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY environment variable is not set.")
    
    primary_llm = ChatGroq(
        api_key=GROQ_API_KEY,
        model_name="llama-3.3-70b-versatile",
        temperature=temperature
    )
    
    if GOOGLE_API_KEY:
        fallback_llm = ChatGoogleGenerativeAI(
            api_key=GOOGLE_API_KEY,
            model=GEMINI_FALLBACK_MODEL,
            temperature=temperature
        )
        return primary_llm.with_fallbacks([fallback_llm])
        
    return primary_llm
