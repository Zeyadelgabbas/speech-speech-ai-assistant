import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import hashlib
from pathlib import Path
from ..utils import get_logger , config
import logging

logger = get_logger(__name__)

logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)


class VectorDB:
    """
    Vector database for Retrieval-Augmented Generation (RAG).
    
    Stores:
    - Uploaded PDF/text documents (chunked)
    - Any text the user wants to remember and search later
    """
    
    def __init__(
        self,
        collection_name: str = "documents",
        persist_directory: Optional[Path] = None
    ):
        """
        Initialize vector database.
        
        Args:
            collection_name: Name of the ChromaDB collection
                Think of this as a "table" in SQL
            persist_directory: Where to store the database
                If None, uses config.CHROMA_PERSIST_DIR
        
        ChromaDB concepts:
        - Client: Database connection
        - Collection: Container for embeddings (like a table)
        - Documents: Text chunks
        - Embeddings: Vector representations (handled by OpenAI)
        - Metadata: Extra info about each chunk (source, date, etc.)
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory or config.CHROMA_PERSIST_DIR
        
        # Ensure directory exists
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,  # Disable telemetry
                allow_reset = True
            )   
        )
        
        # Get or create collection
        # Note: ChromaDB will use OpenAI embeddings via our embedding function
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "User documents and voice inserts"}
        )
        
        logger.info(
            f"VectorDB initialized: collection={collection_name}, "
            f"path={self.persist_directory}, docs={self.collection.count()}"
        )
    
    def _get_openai_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using OpenAI API.
        
        Args:
            text: Text to embed
        
        Returns:
            Embedding vector (list of floats, length=1536 for text-embedding-3-small)
        
        """
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=config.OPENAI_API_KEY)
            
            # Call embeddings API
            response = client.embeddings.create(
                model=config.OPENAI_EMBEDDING_MODEL,
                input=text
            )
            
            embedding = response.data[0].embedding
            
            logger.debug(f"Generated embedding: {len(text)} chars → {len(embedding)} dims")
            
            return embedding
        
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    def add_document(
        self,
        text: str,
        metadata: Optional[Dict] = None,
        doc_id: Optional[str] = None
    ) -> str:
        """
        Add a single document (or chunk) to the vector database.
        
        Args:
            text: Document text
            metadata: Additional info about document
            doc_id: Unique identifier (auto-generated if None)
                Important: Same doc_id = update existing doc
        
        Returns:
            Document ID
        """
        # Generate doc_id if not provided (hash of content)
        if not doc_id:
            doc_id = self._generate_doc_id(text, metadata)
        
        # Add default metadata
        if metadata is None:
            metadata = {}
        
        metadata.setdefault("added_at", str(Path.cwd()))
        
        # Generate embedding
        embedding = self._get_openai_embedding(text)
        
        # Add to collection
        self.collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata]
        )
        
        logger.info(f"Added document: id={doc_id}, length={len(text)} chars")
        
        return doc_id
    
    def add_documents_batch(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict]] = None,
        doc_ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Add multiple documents in a single batch (more efficient).
        
        Args:
            texts: List of document texts
            metadatas: List of metadata dicts (one per text)
            doc_ids: List of document IDs (auto-generated if None)
        
        Returns:
            List of document IDs
    
        """
        if not texts:
            return []
        
        # Generate doc_ids if not provided
        if not doc_ids:
            doc_ids = [
                self._generate_doc_id(text, metadatas[i] if metadatas else None)
                for i, text in enumerate(texts)
            ]
        
        # Prepare metadatas
        if metadatas is None:
            metadatas = [{}] * len(texts)

        all_sources = self.list_sources()
        new_texts=[]
        new_metadatas = []
        new_docs_ids = []

        for i in range(len(texts)):

            current_metadata = metadatas[i] if i < len(metadatas) else {}
            source = current_metadata.get("source","")

            if source and source in all_sources:
                logger.info(f"skipping duplicate source: {source} ")
                continue

            new_texts.append(texts[i])
            new_metadatas.append(current_metadata)
            new_docs_ids.append(doc_ids[i]) 

        if not new_texts:
            logger.info(f"All documents were duplicates , skipping ")
            return []
        
        # Generate embeddings (batch)
        embeddings = self._get_openai_embeddings_batch(new_texts)
        
        # Add to collection
        self.collection.add(
            ids=new_docs_ids,
            embeddings=embeddings,
            documents=new_texts,
            metadatas=new_metadatas,
        )
        
        logger.info(f"Added {len(texts)} documents in batch")
        
        return new_docs_ids
    
    def _get_openai_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in one API call.
        
        Args:
            texts: List of texts to embed
        
        Returns:
            List of embedding vectors
        
        OpenAI batch limits:
        - Max 2048 texts per request
        - Max 8191 tokens per text
        - If you exceed, split into multiple batches
        """
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=config.OPENAI_API_KEY)
            
            # Call embeddings API (batch)
            response = client.embeddings.create(
                model=config.OPENAI_EMBEDDING_MODEL,
                input=texts
            )
            
            embeddings = [item.embedding for item in response.data]
            
            logger.debug(f"Generated {len(embeddings)} embeddings in batch")
            
            return embeddings
        
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise
    
    def query(
        self,
        query_text: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search for similar documents using semantic similarity.
        
        Args:
            query_text: Search query (natural language)
            top_k: Number of results to return (default: 5)
            filter_metadata: Filter results by metadata
        
        Returns:
            List of results:
            [
                {
                    "id": "doc_123",
                    "text": "Project deadline is Nov 15...",
                    "metadata": {"source": "notes.pdf", "page": 3},
                    "distance": 0.23  # Lower = more similar
                },
                ...
            ]
        """
        if not query_text.strip():
            logger.warning("Empty query provided")
            return []
        
        # Generate embedding for query
        query_embedding = self._get_openai_embedding(query_text)
        
        # Query ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_metadata  # Optional metadata filtering
        )
        
        # Format results
        formatted_results = []
        
        if results['ids'] and results['ids'][0]:
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    "id": results['ids'][0][i],
                    "text": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                })
        
        logger.info(f"Query '{query_text[:50]}...': found {len(formatted_results)} results")
        
        return formatted_results
    
    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document by ID.
        
        Args:
            doc_id: Document ID
        
        Returns:
            True if deleted, False if not found
        
        Usage:
            vector_db.delete_document("meeting_notes_page3_chunk1")
        """
        try:
            self.collection.delete(ids=[doc_id])
            logger.info(f"Deleted document: {doc_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False
    
    
    def get_document_count(self) -> int:
        """
        Get total number of documents in the database.
        
        Returns:
            Document count
        """
        return self.collection.count()
    
    def list_sources(self) -> List[str]:
        """
        Get list of unique sources in the database.
        
        Returns:
            List of source names
        
        Usage:
            sources = vector_db.list_sources()
            print(f"Documents from: {', '.join(sources)}")
        """
        try:
            # Get all documents
            results = self.collection.get()
            
            # Extract unique sources from metadata
            sources = set()
            for metadata in results['metadatas']:
                if 'source' in metadata:
                    sources.add(metadata['source'])
            
            return sorted(list(sources))
        
        except Exception as e:
            logger.error(f"Failed to list sources: {e}")
            return []
    
    def _generate_doc_id(self, text: str, metadata: Optional[Dict] = None) -> str:
        """
        Generate a unique document ID based on content and metadata.
        
        Args:
            text: Document text
            metadata: Document metadata
        
        Returns:
            Document ID (hash string)
        
        """
        # Combine text and metadata into single string
        content = text
        if metadata:
            content += str(sorted(metadata.items()))
        
        # Generate MD5 hash
        hash_obj = hashlib.md5(content.encode('utf-8'))
        doc_id = hash_obj.hexdigest()[:16]  # Use first 16 chars
        
        return doc_id
    
    def clear_collection(self):
        """
        Delete all documents in the collection (DANGEROUS!).
        """
        try:
            # Delete the collection
            self.client.delete_collection(name=self.collection_name)
            
            # Recreate empty collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "User documents and voice inserts"}
            )
            
            logger.warning("Collection cleared (all documents deleted)")
            print("⚠️  All documents deleted from vector database")
        
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            raise

    def delete_by_metadata(self,metadata: dict):

        try:
            self.collection.delete(where = metadata)
            logger.info(f"Deleted by metadata : {metadata}")
            return 1 
        
        except Exception as e : 
            logger.error(f"failed to delete by metadata : {e}")

if __name__ == "__main__":
    import tempfile
    import shutil
    import time
    
    print("=" * 70)
    print("VECTOR DATABASE TEST")
    print("=" * 70)
    
    # Check if OpenAI API key is configured
    if not config.OPENAI_API_KEY or config.OPENAI_API_KEY.startswith("sk-proj-xxx"):
        print("❌ OpenAI API key not configured")
        print("   Set OPENAI_API_KEY in .env to run vector DB tests")
        exit(1)
    
    # Create temporary directory for testing
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Test 1: Initialize vector DB
        print("\n📝 Test 1: Initialize vector database")
        print("-" * 70)
        
        vector_db = VectorDB(
            collection_name="test_collection",
            persist_directory=temp_dir
        )
        
        print(f"✅ VectorDB initialized")
        print(f"   Path: {temp_dir}")
        print(f"   Document count: {vector_db.get_document_count()}")
        
        # Test 2: Add single document
        print("\n📝 Test 2: Add single document")
        print("-" * 70)
        
        doc_text = "The project deadline is November 15th. We need to complete the backend API by then."
        doc_id = vector_db.add_document(
            text=doc_text,
            metadata={"source": "meeting_notes.txt", "date": "2025-11-05"}
        )
        
        print(f"✅ Added document: {doc_id}")
        print(f"   Document count: {vector_db.get_document_count()}")
        
        # Test 3: Add batch of documents
        print("\n📝 Test 3: Add batch of documents")
        print("-" * 70)
        
        batch_texts = [
            "Team meeting scheduled for Mondays at 10 AM.",
            "Use Python 3.10+ for the project.",
            "Database should use PostgreSQL 14.",
            "Deploy to AWS using Docker containers."
        ]
        
        batch_metadata = [
            {"source": "team_guidelines.txt"},
            {"source": "tech_stack.txt"},
            {"source": "tech_stack.txt"},
            {"source": "deployment.txt"}
        ]
        
        batch_ids = vector_db.add_documents_batch(batch_texts, batch_metadata)
        
        print(f"✅ Added {len(batch_ids)} documents")
        print(f"   Total documents: {vector_db.get_document_count()}")
        
        # Test 4: Query (semantic search)
        print("\n📝 Test 4: Query for similar documents")
        print("-" * 70)
        
        query = "When is the project due?"
        results = vector_db.query(query, top_k=3)
        
        print(f"✅ Query: '{query}'")
        print(f"   Found {len(results)} results:\n")
        
        for i, r in enumerate(results, 1):
            print(f"   {i}. [{r['metadata'].get('source', 'unknown')}]")
            print(f"      {r['text'][:80]}...")

        
        # Test 5: Query with metadata filter
        print("\n📝 Test 5: Query with metadata filter")
        print("-" * 70)
        
        filtered_results = vector_db.query(
            query_text="technology stack",
            top_k=5,
            filter_metadata={"source": "tech_stack.txt"}
        )
        
        print(f"✅ Filtered query (source='tech_stack.txt')")
        print(f"   Found {len(filtered_results)} results")
        
        # Test 6: List sources
        print("\n📝 Test 6: List unique sources")
        print("-" * 70)
        
        sources = vector_db.list_sources()
        print(f"✅ Sources in database:")
        for source in sources:
            print(f"   - {source}")
        
        # Test 7: Delete document
        print("\n📝 Test 7: Delete document")
        print("-" * 70)
        
        deleted = vector_db.delete_document(doc_id)
        print(f"✅ Deleted document: {deleted}")
        print(f"   Documents remaining: {vector_db.get_document_count()}")
        
        # Test 8: Delete by metadata
        print("\n📝 Test 8: Delete by metadata filter")
        print("-" * 70)
        
        deleted_count = vector_db.delete_by_metadata({"source": "deployment.txt"})
        print(f"✅ Deleted {deleted_count} documents")
        print(f"   Documents remaining: {vector_db.get_document_count()}")
        
        print("\n" + "=" * 70)
        print("✅ All vector database tests passed!")
        print("\n💡 Tips:")
        print("  - Use batch operations for faster ingestion")
        print("  - Set top_k=3-5 for good context without token bloat")
        print("  - Filter by metadata to narrow search scope")
        print("  - Distance < 0.5 usually indicates good relevance")
    
    finally:
        # Cleanup
        try:
            vector_db.clear_collection()
            print("collection deleted")

            # Close the Chroma DB client if possible
            if hasattr(vector_db, "client") and vector_db.client:
                if hasattr(vector_db.client, "persist"):
                    vector_db.client.persist()
                if hasattr(vector_db.client, "reset"):
                    vector_db.client.reset()  # Requires allow_reset=True
                elif hasattr(vector_db.client, "close"):
                    vector_db.client.close()
        except Exception as e:
            print(f"⚠️ Could not fully close Chroma client: {e}")

        try:
            time.sleep(15)
            shutil.rmtree(temp_dir)
            print(f"\n🧹 Cleaned up test directory: {temp_dir}")

        except Exception as e:
            print(e)
