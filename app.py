from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv

import multiprocessing
import uvicorn

# Load environment variables
load_dotenv()

# Import our services
from services.data_preprocessor import DataProcessor
from services.search_service import SearchService
from services.summarization_service import SummarizationService

app = FastAPI(
    title="Patent Semantic Search API",
    description="Semantic search API for patent documents with AI-powered summarization",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Response models
class DocumentInfo(BaseModel):
    patent_number: str
    title: str
    relevance_score: float

class SearchResponse(BaseModel):
    query: str
    top_documents: List[DocumentInfo]
    summary: str
    processing_time: float

# Initialize services
data_processor = DataProcessor()
search_service = SearchService()
summarization_service = SummarizationService()

@app.on_event("startup")
async def startup_event():
    """Initialize the application and load data if needed."""
    print("Starting Patent Search API...")
    
    # Check if vector database exists, if not, process and index documents
    if not search_service.is_indexed():
        print("Vector database not found. Processing and indexing documents...")
        documents = data_processor.load_and_process_documents()
        search_service.index_documents(documents)
        print(f"Indexed {len(documents)} documents.")
    else:
        print("Vector database found. Ready to serve requests.")
    
    # Print the localhost URL for easy access
    host = os.getenv("API_HOST", "0.0.0.0")
    port = os.getenv("API_PORT", 8000)
    print(f"\n🚀 Application startup complete!")
    print(f"📡 API is running at: http://localhost:{port}")
    print(f"📚 Interactive API docs: http://localhost:{port}/docs")
    print(f"❤️  Health check: http://localhost:{port}/health")
    print(f"🔍 Try a search: http://localhost:{port}/search?query=your_search_query")

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Patent Semantic Search API",
        "version": "1.0.0",
        "endpoints": {
            "search": "/search?query=your_search_query",
            "health": "/health",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "patent-search-api"}

@app.get("/search", response_model=SearchResponse)
async def search(
    query: str = Query(..., description="Search query for patent documents", min_length=3)
):
    """
    Search for the top 3 most relevant patent documents and provide a summary.
    
    Args:
        query: Search query string
    
    Returns:
        SearchResponse with top documents and AI-generated summary
    """
    try:
        import time
        start_time = time.time()
        
        if not query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Perform semantic search
        search_results = search_service.search(query, top_k=3)
        
        if not search_results:
            raise HTTPException(status_code=404, detail="No relevant documents found")
        
        # Extract document information
        top_documents = []
        descriptions = []
        
        for result in search_results:
            doc_info = DocumentInfo(
                patent_number=result['patent_number'],
                title=result['title'],
                relevance_score=result['score']
            )
            top_documents.append(doc_info)
            descriptions.append(result['description'])
        
        # Generate summary
        summary = summarization_service.summarize_descriptions(descriptions)
        
        processing_time = time.time() - start_time
        
        return SearchResponse(
            query=query,
            top_documents=top_documents,
            summary=summary,
            processing_time=round(processing_time, 3)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/stats")
async def get_stats():
    """Get statistics about the indexed documents."""
    try:
        stats = search_service.get_collection_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving stats: {str(e)}")

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(
#         "app:app", 
#         host=os.getenv("API_HOST", "0.0.0.0"), 
#         port=int(os.getenv("API_PORT", 8000)), 
#         reload=os.getenv("API_RELOAD", "true").lower() == "true"
#     )
if __name__ == "__main__":

    multiprocessing.set_start_method("spawn", force=True)  # Windows-safe method

    uvicorn.run(
        "app:app", 
        host=os.getenv("API_HOST", "0.0.0.0"), 
        port=int(os.getenv("API_PORT", 8000)), 
        reload=os.getenv("API_RELOAD", "true").lower() == "true"
    )

