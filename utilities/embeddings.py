import numpy as np

_encoder = None

def get_encoder():
    global _encoder
    if _encoder is None:
        try:
            from sentence_transformers import SentenceTransformer
            _encoder = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            print(f"Embeddings unavailable: {e}")
            _encoder = False
    return _encoder if _encoder is not False else None


def embed_texts(texts):
    encoder = get_encoder()
    if not encoder:
        return None
    try:
        vectors = encoder.encode(texts, show_progress_bar=False)
        return vectors.tolist()
    except Exception as e:
        print(f"Embed error: {e}")
        return None


def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    if a.ndim == 1:
        a = a.reshape(1, -1)
    if b.ndim == 1:
        b = b.reshape(1, -1)
    norm_a = np.linalg.norm(a, axis=1, keepdims=True)
    norm_b = np.linalg.norm(b, axis=1, keepdims=True)
    norm_a = np.where(norm_a == 0, 1, norm_a)
    norm_b = np.where(norm_b == 0, 1, norm_b)
    return (a @ b.T) / (norm_a * norm_b.T)
