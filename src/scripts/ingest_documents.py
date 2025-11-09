import sys
from pathlib import Path
import argparse
import tiktoken
from typing import List, Dict
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.memory import VectorDB
from src.utils import get_logger , config

logger = get_logger(__name__)
encoding = tiktoken.get_encoding('cl100k_base')
def num_tokens(text: str) ->int:
    return len(encoding.encode(text))
def chunk_text(text: str, chunk_size: int = None, overlap: int = None , num_tokens:callable = num_tokens) -> List[str]:
    """
    Split text into overlapping chunks.
    
    Args:
        text: Full text to chunk
        chunk_size: Target chunk size in tokens (approximate)
        overlap: Overlap between chunks in tokens (approximate)
    
    Returns:
        List of text chunks
 
    """
    chunk_size = chunk_size or config.EMBEDDING_CHUNK_SIZE
    overlap = overlap or config.EMBEDDING_CHUNK_OVERLAP
    
    # Split by number of tokens 
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size = chunk_size,
        chunk_overlap = overlap,
        length_function = num_tokens,
        separators=["\n\n","\n","."," ",""]
    )
    chunks = text_splitter.split_text(text)
    
    return chunks


def extract_text_from_pdf(pdf_path: Path , num_tokens: callable = num_tokens) -> List[str,any]:
    """
    Extract text from PDF file.
    
    Args:
        pdf_path: Path to PDF file
    
    Returns:
        Extracted text    
    """
    try:
        from langchain_community.document_loaders import PyPDFLoader
        logger.info(f"Extracting text from PDF: {pdf_path}")

        loader = PyPDFLoader(pdf_path)
        docs = loader.load()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size = config.EMBEDDING_CHUNK_SIZE,
            chunk_overlap = config.EMBEDDING_CHUNK_OVERLAP,
            length_function = num_tokens,
            separators=["\n\n","\n","."," ",""]
        )
        
        chunks = splitter.split_documents(docs)

        return chunks
    
    except Exception as e:
        logger.error(f"Failed to extract text from PDF: {e}")
        raise


def extract_text_from_txt(txt_path: Path) -> str:
    """
    Extract text from plain text file.
    
    Args:
        txt_path: Path to text file
    
    Returns:
        File contents
    """
    try:
        with open(txt_path, 'r', encoding='utf-8') as file:
            text = file.read()
        
        logger.info(f"Read {len(text)} characters from {txt_path}")
        return text
    
    except UnicodeDecodeError:
        # Try with different encoding
        logger.warning(f"UTF-8 failed, trying latin-1 encoding")
        with open(txt_path, 'r', encoding='latin-1') as file:
            text = file.read()
        
        return text
    
    except Exception as e:
        logger.error(f"Failed to read text file: {e}")
        raise


def ingest_file(
    file_path: Path,
    vector_db: VectorDB,
) -> int:
    """
    Ingest a single file (PDF or TXT) into vector database.
    
    Args:
        file_path: Path to file
        vector_db: VectorDB instance
        chunk_size: Chunk size in tokens
        overlap: Chunk overlap in tokens
    
    Returns:
        Number of chunks ingested
    
    Process:
    1. Extract text from file (PDF or TXT)
    2. Split into chunks
    3. Embed chunks using OpenAI
    4. Store in ChromaDB
    """
    try:
        print(f"\n📄 Processing: {file_path.name}")
        
        # Extract text based on file type
        if file_path.suffix.lower() == '.pdf':
            chunks = extract_text_from_pdf(file_path)
            is_pdf = True
            if not chunks[0].page_content.strip():
                print("File is empty")
                return 0

        elif file_path.suffix.lower() in ['.txt', '.md']:
            is_pdf = False
            text = extract_text_from_txt(file_path)
            if not text.strip():
                print("File is empty")
                return 0
            chunks = chunk_text(text)

        else:
            print(f"❌ Unsupported file type: {file_path.suffix}")
            return 0   
                 
        # Prepare metadata for each chunk
        metadatas = []
        chunks_pdf = []
        for i, chunk in enumerate(chunks):
            metadata = {
                "source": file_path.name,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "file_type": file_path.suffix.lower()
            }
            if hasattr(chunk,'page_content') and hasattr(chunk,"metadata"):
                text = chunk.page_content
                chunks_pdf.append(text)
                chunk_meta = chunk.metadata.copy()
                if "page" in chunk_meta:
                    metadata['page'] = chunk_meta['page']

            metadatas.append(metadata)
        
        # Add to vector database (batch)
        print(f"   Embedding and storing chunks...")
        if is_pdf:
            vector_db.add_documents_batch(chunks_pdf, metadatas=metadatas)
        else:
            vector_db.add_documents_batch(chunks,metadatas=metadatas)
        
        print(f"✅ Ingested {len(chunks)} chunks from {file_path.name}")
        
        return len(chunks)
    
    except Exception as e:
        print(f"❌ Failed to ingest {file_path.name}: {e}")
        logger.error(f"Ingestion error for {file_path}: {e}")
        return 0


def ingest_directory(
    directory: Path,
    vector_db: VectorDB,
    recursive: bool = False,
) -> int:
    """
    Ingest all supported files from a directory.
    
    Args:
        directory: Path to directory
        vector_db: VectorDB instance
        recursive: Whether to search subdirectories
        chunk_size: Chunk size in tokens
        overlap: Chunk overlap in tokens
    
    Returns:
        Total number of chunks ingested
    """
    supported_extensions = ['.pdf', '.txt', '.md']
    
    # Find all files
    if recursive:
        files = []
        for ext in supported_extensions:
            files.extend(directory.rglob(f'*{ext}'))
    else:
        files = []
        for ext in supported_extensions:
            files.extend(directory.glob(f'*{ext}'))
    
    if not files:
        print(f"⚠️  No supported files found in {directory}")
        return 0
    
    print(f"\n📁 Found {len(files)} files in {directory}")
    
    total_chunks = 0
    
    for file_path in files:
        chunks = ingest_file(file_path, vector_db)
        total_chunks += chunks
    
    return total_chunks


def main():
    """
    CLI entrypoint for document ingestion.
    
    Usage examples:
        # Ingest single file
        python scripts/ingest_documents.py --file ./notes.pdf
        
        # Ingest multiple files
        python scripts/ingest_documents.py --file notes.pdf research.txt
        
        # Ingest entire directory
        python scripts/ingest_documents.py --directory ./documents/
        
        # Ingest directory recursively (including subdirectories)
        python scripts/ingest_documents.py --directory ./documents/ --recursive
        
        # Custom chunk size
        python scripts/ingest_documents.py --file notes.pdf --chunk-size 1000
    """
    parser = argparse.ArgumentParser(
        description="Ingest documents into vector database for RAG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ingest single file
  python scripts/ingest_documents.py --file notes.pdf
  
  # Ingest multiple files
  python scripts/ingest_documents.py --file notes.pdf research.txt
  
  # Ingest directory
  python scripts/ingest_documents.py --directory ./documents/
  
  # Ingest directory recursively
  python scripts/ingest_documents.py --directory ./documents/ --recursive
  
Supported file types: .pdf, .txt, .md
        """
    )
    
    parser.add_argument(
        '--file', '-f',
        type=str,
        nargs='+',
        help='Path(s) to file(s) to ingest'
    )
    
    parser.add_argument(
        '--directory', '-d',
        type=str,
        help='Path to directory containing files to ingest'
    )
    
    parser.add_argument(
        '--recursive', '-r',
        action='store_true',
        help='Recursively search subdirectories (use with --directory)'
    )
    
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=config.EMBEDDING_CHUNK_SIZE,
        help=f'Chunk size in tokens (default: {config.EMBEDDING_CHUNK_SIZE})'
    )
    
    parser.add_argument(
        '--overlap',
        type=int,
        default=config.EMBEDDING_CHUNK_OVERLAP,
        help=f'Chunk overlap in tokens (default: {config.EMBEDDING_CHUNK_OVERLAP})'
    )
    
    parser.add_argument(
        '--list-sources',
        action='store_true',
        help='List all sources currently in the database'
    )
    
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Clear all documents from database (DANGEROUS!)'
    )
    
    args = parser.parse_args()
    
    # Print header
    print("=" * 70)
    print("DOCUMENT INGESTION TOOL")
    print("=" * 70)
    
    # Check OpenAI API key
    if not config.OPENAI_API_KEY or config.OPENAI_API_KEY.startswith("sk-proj-xxx"):
        print("\nOpenAI API key not configured")
        print("Set OPENAI_API_KEY in .env file")
        sys.exit(1)
    
    # Initialize vector database
    print(f"\n📊 Initializing vector database...")
    vector_db = VectorDB()
    
    print(f"   Database: {config.CHROMA_PERSIST_DIR}")
    print(f"   Documents: {vector_db.get_document_count()}")
    
    # Handle --list-sources
    if args.list_sources:
        print(f"\n📚 Sources in database:")
        sources = vector_db.list_sources()
        
        if sources:
            for source in sources:
                print(f"   • {source}")
        else:
            print("   (No sources yet)")
        
        sys.exit(0)
    
    # Handle --clear
    if args.clear:
        confirm = input("\n⚠️  This will delete ALL documents. Are you sure? (yes/no): ")
        
        if confirm.lower() == 'yes':
            vector_db.clear_collection()
            print("✅ Database cleared")
        else:
            print("❌ Clear cancelled")
        
        sys.exit(0)
    
    # Validate arguments
    if not args.file and not args.directory:
        print("\n❌ Error: Must specify --file or --directory")
        print("   Run with --help for usage examples")
        sys.exit(1)
    
    # Ingest files
    total_chunks = 0
    
    if args.file:
        # Ingest individual files
        for file_path_str in args.file:
            file_path = Path(file_path_str)
            
            if not file_path.exists():
                print(f"\n❌ File not found: {file_path}")
                continue
            
            chunks = ingest_file(
                file_path,
                vector_db,
                chunk_size=args.chunk_size,
                overlap=args.overlap
            )
            total_chunks += chunks
    
    if args.directory:
        # Ingest directory
        dir_path = Path(args.directory)
        
        if not dir_path.exists():
            print(f"\n❌ Directory not found: {dir_path}")
            sys.exit(1)
        
        if not dir_path.is_dir():
            print(f"\n❌ Not a directory: {dir_path}")
            sys.exit(1)
        
        chunks = ingest_directory(
            dir_path,
            vector_db,
            recursive=args.recursive,
            chunk_size=args.chunk_size,
            overlap=args.overlap
        )
        total_chunks += chunks
    
    # Print summary
    print("\n" + "=" * 70)
    print("INGESTION COMPLETE")
    print("=" * 70)
    print(f"✅ Total chunks ingested: {total_chunks}")
    print(f"   Total documents in DB: {vector_db.get_document_count()}")
    print(f"\n💡 You can now query these documents with voice commands:")
    print(f"   'What did I upload about [topic]?'")
    print(f"   'Search my documents for [query]'")


if __name__ == "__main__":
    main()
