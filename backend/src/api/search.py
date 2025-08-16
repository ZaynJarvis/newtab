"""Search endpoints for unified keyword and semantic search."""

import asyncio
from fastapi import APIRouter, HTTPException
from src.core.models import UnifiedSearchResponse


router = APIRouter()

# Import dependencies - will be injected at runtime
db = None
ark_client = None
vector_store = None


def inject_dependencies(database, api_client, vector_storage):
    """Inject dependencies at startup."""
    global db, ark_client, vector_store
    db = database
    ark_client = api_client
    vector_store = vector_storage


@router.get("/search", response_model=UnifiedSearchResponse)
async def unified_search(q: str):
    """
    Unified search endpoint with server-controlled ranking logic.
    
    Combines keyword and semantic search with optimal server-side mixing:
    - 70% weight for semantic/vector search (for relevance)
    - 30% weight for keyword/text search (for exact matches)
    - Maximum 10 results returned
    - Server handles all ranking and deduplication
    
    Args:
        q: Search query string
    
    Returns:
        Unified search results with relevance scoring
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # Server-controlled parameters
    MAX_RESULTS = 10
    VECTOR_WEIGHT = 0.7
    KEYWORD_WEIGHT = 0.3
    MIN_SIMILARITY = 0.1
    
    # Advanced filtering parameters
    ENABLE_SMART_CUTOFF = True
    SIMILARITY_DROP_THRESHOLD = 0.15  # Detect 15% similarity drops
    MIN_CLUSTER_SCORE = 0.25  # Minimum score for clustering analysis
    
    try:
        # Define async functions for parallel execution
        async def get_keyword_results():
            """Get keyword search results."""
            try:
                results, total = db.search_keyword(q, MAX_RESULTS * 2)
                return results
            except Exception as e:
                print(f"Keyword search error: {e}")
                return []
        
        async def get_vector_results():
            """
            Get vector search results with 3-step fallback strategy:
            1. Use exact cached embedding for query
            2. If not cached, call API and cache result
            3. If API fails, use keyword search top-1 result's embedding for similarity search
            """
            if not ark_client:
                return []
            
            try:
                # Step 1 & 2: Generate embedding for query (cache-aware)
                query_vector = await ark_client.generate_embedding(q)
                
                # Search in vector store with advanced filtering
                vector_results = vector_store.search(
                    query_vector, 
                    MAX_RESULTS * 2, 
                    MIN_SIMILARITY,
                    enable_clustering=ENABLE_SMART_CUTOFF,
                    similarity_drop_threshold=SIMILARITY_DROP_THRESHOLD
                )
                
                # Format results with similarity scores
                formatted_results = []
                for page_data, similarity in vector_results:
                    result_dict = page_data.dict()
                    result_dict['vector_similarity'] = round(similarity, 4)
                    formatted_results.append(result_dict)
                
                return formatted_results
            except Exception as e:
                print(f"Vector search error: {e}")
                
                # Step 3: Fallback to keyword search top-1 result's embedding for similarity
                try:
                    print(f"Attempting fallback: using keyword search top result's embedding")
                    keyword_fallback_results, _ = db.search_keyword(q, 1)
                    
                    if keyword_fallback_results and len(keyword_fallback_results) > 0:
                        top_result = keyword_fallback_results[0]
                        
                        # Get the stored embedding for the top keyword result
                        stored_embedding = db.get_page_embedding(top_result.id)
                        
                        if stored_embedding:
                            print(f"Using stored embedding from top keyword result: {top_result.title[:50]}...")
                            
                            # Use top result's embedding for vector similarity search
                            fallback_vector_results = vector_store.search(
                                stored_embedding,
                                MAX_RESULTS * 2,
                                MIN_SIMILARITY,
                                enable_clustering=ENABLE_SMART_CUTOFF,
                                similarity_drop_threshold=SIMILARITY_DROP_THRESHOLD
                            )
                            
                            # Format fallback results
                            formatted_fallback = []
                            for page_data, similarity in fallback_vector_results:
                                result_dict = page_data.dict()
                                result_dict['vector_similarity'] = round(similarity, 4)
                                # Mark as fallback result
                                result_dict['fallback_source'] = 'keyword_top_result_embedding'
                                formatted_fallback.append(result_dict)
                            
                            return formatted_fallback
                        else:
                            print(f"No stored embedding found for top keyword result")
                    else:
                        print(f"No keyword results found for fallback")
                
                except Exception as fallback_error:
                    print(f"Fallback strategy also failed: {fallback_error}")
                
                return []
        
        # Execute searches in parallel
        keyword_task = asyncio.create_task(get_keyword_results())
        vector_task = asyncio.create_task(get_vector_results())
        
        # Wait for both searches to complete
        keyword_results, vector_results = await asyncio.gather(keyword_task, vector_task)
        
        # Server-controlled result mixing
        url_to_result = {}
        
        # Process keyword results with position-based scoring
        for i, result in enumerate(keyword_results):
            result_dict = result.dict()
            # Position-based scoring: first result = 1.0, decreasing linearly
            keyword_score = 1.0 - (i / max(len(keyword_results) - 1, 1)) * 0.9 if len(keyword_results) > 1 else 1.0
            result_dict['keyword_score'] = keyword_score
            result_dict['vector_score'] = 0.0
            result_dict['relevance_score'] = keyword_score * KEYWORD_WEIGHT
            url_to_result[result.url] = result_dict
        
        # Process vector results and merge/add
        for result in vector_results:
            url = result['url']
            vector_score = result.get('vector_similarity', 0.0)
            
            if url in url_to_result:
                # Merge with existing keyword result
                existing = url_to_result[url]
                existing['vector_score'] = vector_score
                existing['relevance_score'] = (
                    existing['keyword_score'] * KEYWORD_WEIGHT + 
                    vector_score * VECTOR_WEIGHT
                )
            else:
                # New result from vector search only
                result['keyword_score'] = 0.0
                result['vector_score'] = vector_score
                result['relevance_score'] = vector_score * VECTOR_WEIGHT
                url_to_result[url] = result
        
        # Apply ARC-based re-ranking with visit count
        final_results = list(url_to_result.values())
        
        # First pass: calculate base final scores without frequency boost
        for result in final_results:
            result['final_score'] = result.get('relevance_score', 0.0)
        
        # Find max score for frequency boost range calculation
        if final_results:
            max_score = max(result['final_score'] for result in final_results)
            frequency_threshold = max_score - 0.05  # Apply boost only within 0.05 of max
        else:
            max_score = 0.0
            frequency_threshold = 0.0
        
        # Second pass: apply frequency boost only to top-scoring results
        for result in final_results:
            # Get frequency metrics from result (already included from database)
            visit_count = result.get('visit_count', 0)
            arc_score = result.get('arc_score', 0.0)
            relevance_score = result.get('relevance_score', 0.0)
            
            # Apply frequency boost only to results within 0.05 of max score
            if result['final_score'] >= frequency_threshold and visit_count > 0:
                # Normalize visit count for boosting (max boost of 20%)
                frequency_boost = min(visit_count / 50.0, 0.2)  # Cap at 20% boost
                arc_boost = arc_score * 0.1  # ARC score contributes up to 10% boost
                
                # Apply frequency boost to top results only
                result['final_score'] = relevance_score + frequency_boost + arc_boost
                result['frequency_boost'] = frequency_boost
                result['arc_boost'] = arc_boost
            else:
                # No frequency boost for lower scoring results
                result['frequency_boost'] = 0.0
                result['arc_boost'] = 0.0
        
        # Sort by combined final score and limit to MAX_RESULTS
        final_results.sort(key=lambda x: x['final_score'], reverse=True)
        final_results = final_results[:MAX_RESULTS]
        
        # Clean up results for response and prepare metadata for frontend
        for result in final_results:
            # Keep the final relevance score
            result['relevance_score'] = round(result.get('final_score', 0.0), 4)
            
            # Preserve scoring metadata for hover hints
            result['metadata'] = {
                'vector_score': round(result.get('vector_score', 0.0), 4),
                'keyword_score': round(result.get('keyword_score', 0.0), 4),
                'access_count': result.get('visit_count', 0),
                'final_score': round(result.get('final_score', 0.0), 4)
            }
            
            # Remove internal scoring fields (now preserved in metadata)
            result.pop('keyword_score', None)
            result.pop('vector_score', None)
            result.pop('vector_similarity', None)
            result.pop('final_score', None)
            result.pop('frequency_boost', None)
            result.pop('arc_boost', None)
        
        return UnifiedSearchResponse(
            results=final_results,
            total_found=len(final_results),
            query=q
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")