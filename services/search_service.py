import os
import chromadb
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer

class SearchService:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.persist_dir = os.getenv('CHROMA_PERSIST_DIR', './vector_db')
        self.collection_name = os.getenv('COLLECTION_NAME', 'patent_documents')
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = None
        
        try:
            self.collection = self.client.get_collection(name=self.collection_name)
        except:
            # Collection doesn't exist yet
            pass
    
    def is_indexed(self) -> bool:
        """Check if documents are already indexed."""
        try:
            if self.collection is None:
                return False
            count = self.collection.count()
            return count > 0
        except:
            return False
    
    def index_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Index documents in the vector database."""
        try:
            # Create or get collection
            if self.collection is None:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
            
            # Prepare data for indexing
            ids = []
            embeddings = []
            metadatas = []
            documents_text = []
            
            for doc in documents:
                ids.append(doc['patent_number'])
                embeddings.append(doc['embedding'])
                metadatas.append({
                    'patent_number': doc['patent_number'],
                    'title': doc['title'],
                    'abstract': doc['abstract'],
                    'claims': doc['claims'],
                    'description': doc['description']
                })
                documents_text.append(doc['searchable_text'])
            
            # Add documents to collection
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents_text
            )
            
            print(f"Successfully indexed {len(documents)} documents.")
            
        except Exception as e:
            print(f"Error indexing documents: {e}")
            raise
    
    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Perform semantic search on the indexed documents."""
        try:
            if self.collection is None:
                raise Exception("No collection found. Please index documents first.")
            
            # Generate embedding for the query
            query_embedding = self.model.encode(query).tolist()
            
            # Perform vector search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=['metadatas', 'documents', 'distances']
            )
            
            # Format results
            search_results = []
            if results['metadatas'] and len(results['metadatas'][0]) > 0:
                for i in range(len(results['metadatas'][0])):
                    metadata = results['metadatas'][0][i]
                    distance = results['distances'][0][i]
                    
                    # Convert distance to similarity score (lower distance = higher similarity)
                    similarity_score = 1 - distance
                    
                    result = {
                        'patent_number': metadata['patent_number'],
                        'title': metadata['title'],
                        'abstract': metadata['abstract'],
                        'claims': metadata['claims'],
                        'description': metadata['description'],
                        'score': round(similarity_score, 4)
                    }
                    search_results.append(result)
            
            return search_results
            
        except Exception as e:
            print(f"Error performing search: {e}")
            raise
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the indexed collection."""
        try:
            if self.collection is None:
                return {"error": "No collection found"}
            
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": self.collection_name,
                "status": "ready"
            }
            
        except Exception as e:
            return {"error": str(e)}