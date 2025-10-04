from utils.vertexai_auth import setup_vertex_ai_auth    
from vertexai.preview.language_models import TextEmbeddingModel

setup_vertex_ai_auth()

def get_embedding_model():
    """Initialize and return the Vertex AI embedding model."""
    model = TextEmbeddingModel.from_pretrained("text-multilingual-embedding-002")
    return model

