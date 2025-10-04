from utils.vertexai_auth import setup_vertex_ai_auth
from vertexai.generative_models import GenerativeModel, GenerationConfig

setup_vertex_ai_auth()

def get_gemini_model(model_name: str = "gemini-2.5-flash") -> GenerativeModel:
    """Get a Gemini model instance from Vertex AI"""
    try:
        model = GenerativeModel(model_name, generation_config=GenerationConfig(
            max_output_tokens=8192,
            temperature=0,
        ))
        print(f"Loaded Gemini model: {model_name}")
        return model
    except Exception as e:
        print(f"Error loading Gemini model '{model_name}': {e}")
        return None