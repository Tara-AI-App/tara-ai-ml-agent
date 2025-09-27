import os
from concurrent.futures import ThreadPoolExecutor
from llama_index.core.node_parser import CodeSplitter, SentenceSplitter
from llama_index.core import Document
from langchain.vectorstores.utils import DistanceStrategy
from langchain_community.vectorstores import BigQueryVectorSearch
from langchain_google_vertexai import VertexAIEmbeddings
from typing import List, Any, Optional, Tuple
import logging

class DocumentPreprocessor:
    """Fast parallel document preprocessing with language detection"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
    def detect_language(self, file_path: str) -> Optional[str]:
        """Detect programming language from file extension."""
        supported_languages = {
            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
            '.go': 'go', '.java': 'java', '.cpp': 'cpp', '.c': 'c',
            '.cs': 'csharp', '.rb': 'ruby', '.php': 'php', '.rs': 'rust',
            '.html': 'html', '.css': 'css', '.json': 'json'
        }
        ext = os.path.splitext(file_path)[1].lower()
        return supported_languages.get(ext)
    
    def split_single_document(self, doc: Document) -> List:
        """Split a single document with language detection."""
        file_path = doc.metadata.get('file_path', '')
        language = self.detect_language(file_path)
        
        if language is None:
            # Use semantic splitting for unsupported languages
            splitter = SentenceSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separator="\n\n",
            )
            return splitter.get_nodes_from_documents([doc])
        
        try:
            # AST-based splitting for code
            splitter = CodeSplitter(
                language=language,
                chunk_lines=40,
                chunk_lines_overlap=15,
                max_chars=self.chunk_size,
            )
            return splitter.get_nodes_from_documents([doc])
        except (ValueError, ImportError, LookupError):
            # Fallback to semantic splitting
            splitter = SentenceSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separator="\n\n",
            )
            return splitter.get_nodes_from_documents([doc])
    
    def process_documents(self, documents: List[Document], max_workers: int = 4) -> List:
        """Process documents in parallel."""
        all_nodes = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.split_single_document, doc) for doc in documents]
            
            for future in futures:
                nodes = future.result()
                all_nodes.extend(nodes)
        
        return all_nodes
    
    def to_langchain_format(self, nodes: List) -> Tuple[List[str], List[dict]]:
        """Convert LlamaIndex nodes to LangChain format, filtering empty content."""
        texts = []
        metadatas = []
        
        for node in nodes:
            # Skip empty or whitespace-only content
            if node.text and node.text.strip():
                texts.append(node.text.strip())
                metadata = dict(node.metadata)
                metadata['node_id'] = node.node_id
                metadatas.append(metadata)
            
        return texts, metadatas

class RAGVectorStore:
    """Integrated RAG vector store with parallel document preprocessing"""

    def __init__(
        self,
        project_id: str,
        dest_dataset: str,
        dest_table: str,
        region: str,
        embedding_model_name: str = "gemini-embedding-001",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        max_workers: int = 4
    ):
        self.project_id = project_id
        self.dest_dataset = dest_dataset
        self.dest_table = dest_table
        self.region = region
        self.max_workers = max_workers

        # Initialize preprocessor
        self.preprocessor = DocumentPreprocessor(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        # Initialize embedding model
        self.embedding_model = VertexAIEmbeddings(
            model_name=embedding_model_name,
            project=project_id
        )

        self.vector_store = None
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def create_vector_store_from_documents(
        self,
        documents: List[Document],
        recreate_table: bool = False
    ) -> BigQueryVectorSearch:
        """Create vector store from LlamaIndex documents with parallel processing."""
        self.logger.info(f"Processing {len(documents)} documents in parallel...")

        # Parallel preprocessing with language detection
        processed_nodes = self.preprocessor.process_documents(
            documents, 
            max_workers=self.max_workers
        )
        self.logger.info(f"Created {len(processed_nodes)} chunks from {len(documents)} documents")

        # Convert to LangChain format
        texts, metadatas = self.preprocessor.to_langchain_format(processed_nodes)

        # Create vector store
        self.vector_store = BigQueryVectorSearch(
            project_id=self.project_id,
            dataset_name=self.dest_dataset,
            table_name=self.dest_table,
            location=self.region,
            embedding=self.embedding_model,
            distance_strategy=DistanceStrategy.COSINE,
        )

        # Add documents to vector store
        self.logger.info("Adding texts to vector store...")
        self.vector_store.add_texts(texts, metadatas=metadatas)

        self.logger.info("Vector store created successfully!")
        return self.vector_store

    def add_documents(self, documents: List[Document]) -> None:
        """Add new documents to existing vector store."""
        if not self.vector_store:
            raise ValueError("Vector store not initialized. Call create_vector_store_from_documents first.")

        processed_nodes = self.preprocessor.process_documents(
            documents, 
            max_workers=self.max_workers
        )
        texts, metadatas = self.preprocessor.to_langchain_format(processed_nodes)

        self.vector_store.add_texts(texts, metadatas=metadatas)
        self.logger.info(f"Added {len(processed_nodes)} new chunks to vector store")

    def load_existing_vector_store(self) -> BigQueryVectorSearch:
        """Load existing vector store."""
        self.vector_store = BigQueryVectorSearch(
            project_id=self.project_id,
            dataset_name=self.dest_dataset,
            table_name=self.dest_table,
            location=self.region,
            embedding=self.embedding_model,
            distance_strategy=DistanceStrategy.COSINE
        )
        return self.vector_store

    def search(
        self,
        query: str,
        k: int = 4,
        filter_dict: Optional[dict] = None
    ) -> List[Any]:
        """Search vector store."""
        if not self.vector_store:
            raise ValueError("Vector store not initialized")

        if filter_dict:
            return self.vector_store.similarity_search(query, k=k, filter=filter_dict)
        else:
            return self.vector_store.similarity_search(query, k=k)