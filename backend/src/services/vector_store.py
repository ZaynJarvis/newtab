"""In-memory vector store with dot product similarity search."""

import numpy as np
from typing import List, Tuple, Dict, Optional
from src.core.models import PageResponse
from sklearn.cluster import KMeans
from collections import defaultdict


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
    
    def search(self, query_vector: List[float], limit: int = 10, min_similarity: float = 0.0, 
               enable_clustering: bool = True, similarity_drop_threshold: float = 0.15) -> List[Tuple[PageResponse, float]]:
        """
        Search for similar vectors using dot product similarity with advanced filtering.
        
        Args:
            query_vector: Query vector to search with
            limit: Maximum number of results to return
            min_similarity: Minimum similarity threshold (0.0 to 1.0)
            enable_clustering: Whether to use clustering-based filtering
            similarity_drop_threshold: Threshold for detecting significant similarity drops
        
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
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Apply advanced filtering if enabled
        if enable_clustering and len(similarities) > 3:
            similarities = self._apply_score_cutoff_filtering(similarities, similarity_drop_threshold)
        
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
    
    def _apply_score_cutoff_filtering(self, similarities: List[Tuple[PageResponse, float]], 
                                     drop_threshold: float = 0.15) -> List[Tuple[PageResponse, float]]:
        """
        Apply advanced score cutoff filtering with clustering and similarity drop detection.
        
        Args:
            similarities: List of (PageResponse, similarity_score) tuples, sorted by score desc
            drop_threshold: Threshold for detecting significant similarity drops
            
        Returns:
            Filtered list of results
        """
        if len(similarities) <= 2:
            return similarities
            
        scores = [sim[1] for sim in similarities]
        
        # Method 1: Detect significant similarity drops
        cutoff_idx = self._detect_similarity_drop(scores, drop_threshold)
        
        # Method 2: Score-based clustering analysis
        cluster_cutoff = self._analyze_score_clusters(scores)
        
        # Use the more conservative (smaller) cutoff
        final_cutoff = min(cutoff_idx, cluster_cutoff) if cluster_cutoff > 0 else cutoff_idx
        
        # Ensure we keep at least 1 result if scores are reasonable
        if final_cutoff == 0 and len(similarities) > 0 and scores[0] > 0.3:
            final_cutoff = 1
            
        return similarities[:final_cutoff] if final_cutoff > 0 else similarities[:1]
    
    def _detect_similarity_drop(self, scores: List[float], threshold: float = 0.15) -> int:
        """
        Detect where there's a significant drop in similarity scores.
        
        Args:
            scores: List of similarity scores, sorted descending
            threshold: Minimum drop to consider significant
            
        Returns:
            Index where to cut off results (0 means no cutoff)
        """
        if len(scores) <= 2:
            return len(scores)
            
        for i in range(1, len(scores)):
            drop = scores[i-1] - scores[i]
            
            # Detect significant drops
            if drop >= threshold:
                return i
                
            # Also check for relative drops (percentage-based)
            if scores[i-1] > 0.1:  # Avoid division by very small numbers
                relative_drop = drop / scores[i-1]
                if relative_drop >= 0.3:  # 30% relative drop
                    return i
        
        return len(scores)  # No significant drop found
    
    def _analyze_score_clusters(self, scores: List[float], min_cluster_size: int = 2) -> int:
        """
        Analyze score distribution to find natural clustering boundaries.
        
        Args:
            scores: List of similarity scores, sorted descending  
            min_cluster_size: Minimum size for a valid cluster
            
        Returns:
            Index where to cut off results based on clustering
        """
        if len(scores) < 4:  # Need minimum data for clustering
            return 0
            
        try:
            # Reshape for sklearn
            score_array = np.array(scores).reshape(-1, 1)
            
            # Try k=2 clustering to separate high vs low relevance
            kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(score_array)
            cluster_centers = kmeans.cluster_centers_.flatten()
            
            # Identify the high-relevance cluster (higher center)
            high_cluster_id = np.argmax(cluster_centers)
            
            # Find the last index of the high-relevance cluster
            cutoff_idx = 0
            for i, label in enumerate(cluster_labels):
                if label == high_cluster_id:
                    cutoff_idx = i + 1
                else:
                    break  # Found first low-relevance result
                    
            # Only apply if the high cluster has reasonable size
            if cutoff_idx >= min_cluster_size:
                return cutoff_idx
                
        except Exception as e:
            print(f"Clustering analysis failed: {e}")
            
        return 0  # No clustering cutoff
    
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