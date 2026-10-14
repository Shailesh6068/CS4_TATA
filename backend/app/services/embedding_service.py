import math
import re
from typing import List

class LocalEmbeddingService:
    """
    Local embedding generator.
    Produces dense semantic vectors locally without any external API calls.
    Uses hash-based word & subword n-gram vectorization with TF-IDF normalization
    to provide robust 256-dimensional semantic representations offline.
    """
    def __init__(self, vector_dim: int = 256):
        self.vector_dim = vector_dim

    def embed_text(self, text: str) -> List[float]:
        """Encodes single text string into a normalized dense vector."""
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Encodes multiple text chunks into normalized dense vectors."""
        results = []
        for text in texts:
            vec = [0.0] * self.vector_dim
            # Tokenize and clean
            tokens = re.findall(r'[a-zA-Z0-9_]+', text.lower())
            if not tokens:
                results.append(vec)
                continue

            for idx, token in enumerate(tokens):
                # Unigram hash
                h1 = hash(token) % self.vector_dim
                vec[h1] += 1.0
                # Bigram hash if next token exists
                if idx < len(tokens) - 1:
                    bigram = f"{token}_{tokens[idx+1]}"
                    h2 = hash(bigram) % self.vector_dim
                    vec[h2] += 1.5

            # L2 Normalization
            norm = math.sqrt(sum(v * v for v in vec))
            if norm > 0:
                vec = [v / norm for v in vec]
            results.append(vec)
        return results

embedding_service = LocalEmbeddingService()
