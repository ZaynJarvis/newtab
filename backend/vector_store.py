"""In-memory vector store with dot product similarity search."""

import numpy as np
from typing import List, Tuple, Dict, Optional
from models import PageResponse


class VectorStore:
    """In-memory vector store for semantic similarity search."""
    
    def __init__(self, dimension: int = 1536):
        """Initialize vector store with specified dimension."""
        self.dimension = dimension
        self.vectors: Dict[int, np.ndarray] = {}  # page_id -> vector
        self.metadata: Dict[int, PageResponse] = {}  # page_id -> page data
    
    def add_vector(self, page_id: int, vector: List[float], page_data: PageResponse):
        """Add a vector and its associated page data to the store."""
        if len(vector) != self.dimension:
            raise ValueError(f"Vector dimension {len(vector)} doesn't match expected {self.dimension}")
        
        # Normalize the vector for better similarity computation
        vector_array = np.array(vector, dtype=np.float32)
        norm = np.linalg.norm(vector_array)
        if norm > 0:
            vector_array = vector_array / norm
        
        self.vectors[page_id] = vector_array
        self.metadata[page_id] = page_data
    
    def remove_vector(self, page_id: int):
        """Remove a vector from the store."""
        self.vectors.pop(page_id, None)
        self.metadata.pop(page_id, None)
    
    def search(self, query_vector: List[float], limit: int = 10, min_similarity: float = 0.0) -> List[Tuple[PageResponse, float]]:
        """
        Search for similar vectors using dot product similarity.
        
        Args:
            query_vector: Query vector to search with
            limit: Maximum number of results to return
            min_similarity: Minimum similarity threshold (0.0 to 1.0)
        
        Returns:
            List of (PageResponse, similarity_score) tuples, sorted by similarity desc
        """
        if len(query_vector) != self.dimension:
            raise ValueError(f"Query vector dimension {len(query_vector)} doesn't match expected {self.dimension}")
        
        if not self.vectors:
            return []
        
        # Normalize query vector
        query_array = np.array(query_vector, dtype=np.float32)
        query_norm = np.linalg.norm(query_array)
        if query_norm > 0:
            query_array = query_array / query_norm
        
        # Compute similarities for all vectors
        similarities = []
        for page_id, vector in self.vectors.items():
            # Since both vectors are normalized, dot product gives cosine similarity
            similarity = np.dot(query_array, vector)
            
            # Convert to float for JSON serialization
            similarity = float(similarity)
            
            if similarity >= min_similarity:
                page_data = self.metadata[page_id]
                similarities.append((page_data, similarity))
        
        # Sort by similarity (descending) and limit results
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:limit]
    
    def update_vector(self, page_id: int, vector: List[float], page_data: PageResponse):
        """Update an existing vector or add if it doesn't exist."""
        self.add_vector(page_id, vector, page_data)
    
    def get_vector(self, page_id: int) -> Optional[np.ndarray]:
        """Get a vector by page ID."""
        return self.vectors.get(page_id)
    
    def get_page_data(self, page_id: int) -> Optional[PageResponse]:
        """Get page data by page ID."""
        return self.metadata.get(page_id)
    
    def size(self) -> int:
        """Get the number of vectors in the store."""
        return len(self.vectors)
    
    def clear(self):
        """Clear all vectors from the store."""
        self.vectors.clear()
        self.metadata.clear()
    
    def get_all_page_ids(self) -> List[int]:
        """Get all page IDs in the vector store."""
        return list(self.vectors.keys())
    
    def bulk_add_vectors(self, vectors_data: List[Tuple[int, List[float], PageResponse]]):
        """Bulk add multiple vectors for efficiency."""
        for page_id, vector, page_data in vectors_data:
            try:
                self.add_vector(page_id, vector, page_data)
            except ValueError as e:
                print(f"Warning: Skipping vector for page {page_id}: {e}")
    
    def get_stats(self) -> Dict[str, any]:
        """Get statistics about the vector store."""
        if not self.vectors:
            return {
                "total_vectors": 0,
                "dimension": self.dimension,
                "avg_norm": 0.0,
                "memory_usage_mb": 0.0
            }
        
        # Calculate average vector norm
        norms = [np.linalg.norm(vector) for vector in self.vectors.values()]
        avg_norm = np.mean(norms)
        
        # Estimate memory usage (rough)
        memory_usage_bytes = len(self.vectors) * self.dimension * 4  # 4 bytes per float32
        memory_usage_mb = memory_usage_bytes / (1024 * 1024)
        
        return {
            "total_vectors": len(self.vectors),
            "dimension": self.dimension,
            "avg_norm": float(avg_norm),
            "memory_usage_mb": round(memory_usage_mb, 2)
        }