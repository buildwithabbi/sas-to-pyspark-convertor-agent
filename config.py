import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()


class Config(BaseModel):
    # LLM Settings
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model_name: str = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")

    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model_name: str = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")

    llm_provider: str = os.getenv("LLM_PROVIDER", "auto")
    enable_llm_fallback: bool = os.getenv("ENABLE_LLM_FALLBACK", "true").lower() == "true"

    # Application Paths
    base_dir: str = os.path.dirname(os.path.abspath(__file__))
    output_dir: str = os.getenv("OUTPUT_DIR", "./output")
    knowledge_dir: str = os.path.join(base_dir, "knowledge")
    prompts_dir: str = os.path.join(base_dir, "prompts")

    # Spark Config Defaults
    spark_app_name: str = "SAS_to_PySpark_Agent"
    strict_mode: bool = False

    def active_provider(self) -> str:
        if self.llm_provider.lower() != "auto":
            return self.llm_provider.lower()
        if self.groq_api_key:
            return "groq"
        elif self.gemini_api_key:
            return "gemini"
        return "none"


config = Config()
