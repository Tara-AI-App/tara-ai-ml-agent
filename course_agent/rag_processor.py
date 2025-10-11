import os
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor

from llama_index.core.node_parser import CodeSplitter, SentenceSplitter
from llama_index.core import Document
from langchain.vectorstores.utils import DistanceStrategy
from langchain_community.vectorstores import BigQueryVectorSearch
from langchain_google_vertexai import VertexAIEmbeddings

class DocumentPreprocessor:
    """Fast parallel document preprocessing with language detection and detailed metrics"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.quality_metrics = {}
        self.code_metrics = {}
        
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
    
    def analyze_code_quality(self, code: str, language: str) -> Dict[str, Any]:
        """Analyze code quality metrics."""
        metrics = {
            'complexity_score': 0.0,
            'documentation_ratio': 0.0,
            'code_to_comment_ratio': 0.0,
            'test_coverage': '0%',
            'best_practices': [],
            'potential_issues': [],
            'maintainability_index': 0.0
        }
        
        # Basic metrics
        lines = code.split('\n')
        comment_lines = sum(1 for line in lines if line.strip().startswith(('#', '//', '/*')))
        code_lines = len(lines) - comment_lines
        
        if code_lines > 0:
            metrics['code_to_comment_ratio'] = comment_lines / code_lines
            
        # Add language-specific best practices
        if language == 'python':
            metrics['best_practices'] = [
                'PEP 8 compliance',
                'Type hints usage',
                'Docstring presence'
            ]
        
        return metrics
    
    def extract_code_context(self, code: str) -> Dict[str, Any]:
        """Extract detailed context from code."""
        context = {
            'imports': [],
            'function_names': [],
            'class_names': [],
            'dependencies': [],
            'key_concepts': [],
            'complexity_indicators': {
                'nested_loops': 0,
                'conditional_depth': 0,
                'function_length': 0
            }
        }
        
        # Basic context extraction
        lines = code.split('\n')
        for line in lines:
            if line.strip().startswith(('import ', 'from ')):
                context['imports'].append(line.strip())
            elif 'class ' in line:
                context['class_names'].append(line.split('class ')[1].split('(')[0].strip())
            elif 'def ' in line:
                context['function_names'].append(line.split('def ')[1].split('(')[0].strip())
                
        return context
    
    def split_single_document(self, doc: Document) -> List:
        """Split a single document with language detection and detailed analysis."""
        file_path = doc.metadata.get('file_path', '')
        language = self.detect_language(file_path)
        
        # Store quality metrics for the document
        self.quality_metrics[file_path] = {
            'last_modified': datetime.now().isoformat(),
            'language': language,
            'source_reliability': 0.95  # Can be adjusted based on repository metrics
        }
        
        # Define default semantic splitter
        default_splitter = SentenceSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separator="\n\n",
        )
        
        # Return default splitter for non-code files
        if language is None:
            return default_splitter.get_nodes_from_documents([doc])
            
        try:
            # Try code-specific splitting
            code_splitter = CodeSplitter(
                language=language,
                chunk_lines=40,
                chunk_lines_overlap=15,
                max_chars=self.chunk_size,
            )
            return code_splitter.get_nodes_from_documents([doc])
        except (ValueError, ImportError, LookupError):
            return default_splitter.get_nodes_from_documents([doc])
    
    def process_documents(self, documents: List[Document], max_workers: int = 4) -> List:
        """Process documents in parallel."""
        all_nodes = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.split_single_document, doc) for doc in documents]
            
            for future in futures:
                nodes = future.result()
                all_nodes.extend(nodes)
        
        return all_nodes
    
    def to_langchain_format(self, nodes: List, max_results: int = 5) -> Tuple[List[str], List[dict]]:
        """Convert LlamaIndex nodes to LangChain format, keeping only top relevant results."""
        texts = []
        metadatas = []
        
        # Sort nodes by relevance score if available
        sorted_nodes = sorted(
            [n for n in nodes if n.text and n.text.strip()],
            key=lambda x: getattr(x, 'score', 0),
            reverse=True
        )
        
        # Take only top N results
        for node in sorted_nodes[:max_results]:
            texts.append(node.text.strip())
            metadata = {
                'node_id': node.node_id,
                'file_path': node.metadata.get('file_path', ''),
                'relevance_score': getattr(node, 'score', 0.0),
                'key_concepts': self._extract_key_concepts(node.text)
            }
            
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
        # Process documents and get chunks
        processed_nodes = self.preprocessor.process_documents(documents, self.max_workers)
        texts, metadatas = self.preprocessor.to_langchain_format(processed_nodes)
        
        # Initialize and populate vector store
        self.vector_store = BigQueryVectorSearch(
            project_id=self.project_id,
            dataset_name=self.dest_dataset,
            table_name=self.dest_table,
            location=self.region,
            embedding=self.embedding_model,
            distance_strategy=DistanceStrategy.COSINE,
        )
        
        # Add documents
        self.vector_store.add_texts(texts, metadatas=metadatas)
        self.logger.info(f"Created vector store with {len(texts)} chunks from {len(documents)} documents")
        
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

class RAGCourseIntegration:
    """Integration layer between course agent and RAG vector store"""
    
    def __init__(self, project_id: str, dataset: str, table: str, region: str):
        self.rag_store = RAGVectorStore(
            project_id=project_id,
            dest_dataset=dataset,
            dest_table=table,
            region=region,
            max_workers=4
        )
        # Load existing vector store
        self.vector_store = self.rag_store.load_existing_vector_store()
    
    def get_code_examples(self, query: str, top_n: int = 5, filter_dict: Optional[Dict] = None) -> List[Dict]:
        """
        Search RAG for top N relevant code examples and return them in a unified format.
        This is designed for single-pass output aggregation.

        OPTIMIZATION: Limit top_n to reduce query time.
        """
        try:
            # Optimize: Reduce top_n if it's too high (diminishing returns after 3-5 results)
            optimized_top_n = min(top_n, 3)  # Cap at 3 for faster queries

            results = self.rag_store.search(query, k=optimized_top_n, filter_dict=filter_dict)
            code_examples = []
            for result in results:
                metadata = result.metadata if hasattr(result, 'metadata') else {}
                code_examples.append({
                    "file_path": metadata.get("file_path", ""),
                    "code_snippet": result.page_content,
                    "relevance_score": getattr(result, "score", None),
                    "key_concepts": metadata.get("key_concepts", []),
                    "url": metadata.get("url", ""),  # If available
                })
            return code_examples
        except Exception as e:
            return [{"error": f"RAG code example search failed: {str(e)}"}]

# Initialize RAG integration
rag_integration = RAGCourseIntegration(
    project_id="id-rd-ca-qais-jabbar",
    dataset="ds_tara", 
    table="github_caramldev_merlin_new_chunk",
    region="asia-southeast2"
)

def search_code_context(query: str, max_results: int = 5, 
                       file_filter: Optional[str] = None) -> Dict[str, Any]:
    """Tool function to search RAG for code context"""
    filter_dict = {"file_path": file_filter} if file_filter else {}
    results = rag_integration.search_repository_context(query, k=max_results, filter_dict=filter_dict)
    
    return {
        "query": query,
        "results_count": len(results),
        "code_contexts": results,
        "timestamp": datetime.now().isoformat()
    }

def get_related_code_examples(topic: str, lesson_context: str = "") -> Dict[str, Any]:
    """Get code examples related to specific lesson topics"""
    search_query = f"{topic} {lesson_context}".strip()
    results = rag_integration.search_repository_context(search_query, k=3)
    
    def process_result(result):
        if result.get("error"):
            return None
        return {
            "file_path": result["metadata"].get("file_path", "unknown"),
            "code_snippet": result["content"][:500] + "..." if len(result["content"]) > 500 else result["content"],
            "full_content": result["content"],
            "relevance_context": f"Related to: {topic}"
        }
    
    code_examples = [ex for ex in map(process_result, results) if ex is not None]
    
    return {
        "topic": topic,
        "examples_found": len(code_examples),
        "code_examples": code_examples
    }

def analyze_repository_with_rag(repo_url: str, technologies: str = "") -> dict:
    """Analyze repository using both GitHub API and RAG context"""
    # Validate and extract repo info
    if not repo_url.startswith(("http://github.com/", "https://github.com/")):
        return {"error": "Only GitHub repositories are supported"}
        
    parts = repo_url.replace("https://github.com/", "").replace("http://github.com/", "").split("/")
    if len(parts) < 2:
        return {"error": "Invalid GitHub repository URL format"}
        
    owner, repo = parts[0], parts[1]
    
    # Get RAG insights
    rag_insights = rag_integration.search_repository_context(
        f"repository structure {repo} {technologies}", k=10
    )
    
    # Extract file types from valid results
    file_types = {
        result["metadata"].get("file_path", "").split(".")[-1]
        for result in rag_insights
        if not result.get("error") and "." in result["metadata"].get("file_path", "")
    }
    
    return {
        "repository": {"owner": owner, "name": repo, "url": repo_url},
        "technologies": technologies.split(",") if technologies else [],
        "rag_insights": {
            "total_relevant_chunks": len(rag_insights),
            "file_types_found": list(file_types),
            "key_patterns": [result["content"][:100] + "..." 
                           for result in rag_insights[:3] 
                           if not result.get("error")]
        },
        "analysis_timestamp": datetime.now().isoformat()
    }