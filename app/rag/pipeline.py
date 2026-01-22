"""
RAG Pipeline Module

Connects retrieval system to LLM for question answering with citations.
Supports multiple LLM providers: OpenAI, Anthropic, local models, or mock.

Related:
- Phase 2 (P2): Task 2.2 - RAG Pipeline
- Retriever integration for context
- Citation tracking from metadata
"""

import logging
import os
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from app.core.config import AppConfig
from app.query.retriever import Retriever, SearchResult

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    MOCK = "mock"


@dataclass
class Citation:
    """Citation for a source document."""
    source_doc: str
    page_number: int
    section_title: Optional[str]
    chunk_id: str
    relevance_score: float
    text_excerpt: str  # First 200 chars of the chunk
    
    def __str__(self) -> str:
        """Format citation as string."""
        section = f", Section: {self.section_title}" if self.section_title else ""
        return f"[{self.source_doc}, Page {self.page_number}{section}]"


@dataclass
class RAGResponse:
    """Response from RAG pipeline with answer and citations."""
    question: str
    answer: str
    citations: List[Citation]
    context_used: List[str]  # Chunk texts used for context
    model: str
    tokens_used: Optional[int] = None
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def format_with_citations(self) -> str:
        """Format answer with inline citations."""
        result = self.answer + "\n\n"
        
        if self.citations:
            result += "Sources:\n"
            for i, citation in enumerate(self.citations, 1):
                result += f"{i}. {citation}\n"
        
        return result
    
    def get_unique_sources(self) -> List[str]:
        """Get list of unique source documents."""
        return list(set(c.source_doc for c in self.citations))
    
    def get_page_range(self) -> Tuple[int, int]:
        """Get min and max page numbers cited."""
        if not self.citations:
            return (0, 0)
        pages = [c.page_number for c in self.citations]
        return (min(pages), max(pages))


class RAGPipeline:
    """
    RAG pipeline for question answering with retrieval and LLM generation.
    
    Supports multiple LLM providers with fallback to mock responses.
    """
    
    def __init__(
        self,
        provider: LLMProvider = LLMProvider.MOCK,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        config: Optional[AppConfig] = None
    ):
        """
        Initialize RAG pipeline.
        
        Args:
            provider: LLM provider (openai, anthropic, ollama, mock)
            model_name: Model name (e.g., "gpt-4", "claude-3-sonnet")
            api_key: API key for provider (reads from env if not provided)
            config: Application configuration
        """
        self.provider = provider
        self.model_name = model_name or self._default_model_name()
        self.config = config or AppConfig.validate()
        
        # Initialize retriever
        self.retriever = Retriever(config=self.config)
        
        # Initialize LLM client based on provider
        self.llm_client = self._initialize_llm(api_key)
        
        logger.info(f"RAG Pipeline initialized with {provider.value} ({self.model_name})")
    
    def _default_model_name(self) -> str:
        """Get default model name for provider."""
        defaults = {
            LLMProvider.OPENAI: "gpt-4",
            LLMProvider.ANTHROPIC: "claude-3-sonnet-20240229",
            LLMProvider.OLLAMA: "llama2",
            LLMProvider.MOCK: "mock-model"
        }
        return defaults.get(self.provider, "unknown")
    
    def _initialize_llm(self, api_key: Optional[str]):
        """Initialize LLM client based on provider."""
        if self.provider == LLMProvider.OPENAI:
            return self._init_openai(api_key)
        elif self.provider == LLMProvider.ANTHROPIC:
            return self._init_anthropic(api_key)
        elif self.provider == LLMProvider.OLLAMA:
            return self._init_ollama()
        else:
            return None  # Mock mode
    
    def _init_openai(self, api_key: Optional[str]):
        """Initialize OpenAI client."""
        try:
            import openai
            openai.api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not openai.api_key:
                logger.warning("OpenAI API key not found. Use OPENAI_API_KEY env var.")
            return openai
        except ImportError:
            logger.error("openai package not installed. Run: pip install openai")
            raise
    
    def _init_anthropic(self, api_key: Optional[str]):
        """Initialize Anthropic client."""
        try:
            import anthropic
            client = anthropic.Anthropic(
                api_key=api_key or os.getenv("ANTHROPIC_API_KEY")
            )
            return client
        except ImportError:
            logger.error("anthropic package not installed. Run: pip install anthropic")
            raise
    
    def _init_ollama(self):
        """Initialize Ollama client."""
        try:
            import ollama
            return ollama
        except ImportError:
            logger.error("ollama package not installed. Run: pip install ollama")
            raise
    
    def ask(
        self,
        question: str,
        top_k: int = 5,
        filters: Optional[Dict] = None,
        temperature: float = 0.3,
        max_tokens: int = 1000
    ) -> RAGResponse:
        """
        Ask a question and get answer with citations.
        
        Args:
            question: User question
            top_k: Number of chunks to retrieve for context
            filters: Metadata filters for retrieval
            temperature: LLM temperature (0-1, lower = more deterministic)
            max_tokens: Maximum tokens in response
            
        Returns:
            RAGResponse with answer and citations
            
        Example:
            >>> pipeline = RAGPipeline(provider=LLMProvider.MOCK)
            >>> response = pipeline.ask("What is the vacation policy?")
            >>> print(response.format_with_citations())
        """
        logger.info(f"Processing question: '{question}'")
        
        # Step 1: Retrieve relevant chunks
        retrieval_result = self.retriever.search(
            query=question,
            top_k=top_k,
            filters=filters
        )
        
        if not retrieval_result.results:
            logger.warning("No relevant documents found")
            return RAGResponse(
                question=question,
                answer="I couldn't find any relevant information in the documents to answer your question.",
                citations=[],
                context_used=[],
                model=self.model_name
            )
        
        # Step 2: Build context from retrieved chunks
        context = self._build_context(retrieval_result.results)
        
        # Step 3: Generate answer with LLM
        answer, tokens = self._generate_answer(
            question=question,
            context=context,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Step 4: Create citations
        citations = self._create_citations(retrieval_result.results)
        
        logger.info(f"Generated answer with {len(citations)} citations")
        
        return RAGResponse(
            question=question,
            answer=answer,
            citations=citations,
            context_used=[r.text for r in retrieval_result.results],
            model=self.model_name,
            tokens_used=tokens
        )
    
    def _build_context(self, results: List[SearchResult]) -> str:
        """
        Build context string from search results.
        
        Args:
            results: List of search results
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        for i, result in enumerate(results, 1):
            source_info = f"[Source {i}: {result.source_doc}, Page {result.page_number}"
            if result.section_title:
                source_info += f", Section: {result.section_title}"
            source_info += "]"
            
            context_parts.append(f"{source_info}\n{result.text}\n")
        
        return "\n".join(context_parts)
    
    def _generate_answer(
        self,
        question: str,
        context: str,
        temperature: float,
        max_tokens: int
    ) -> Tuple[str, Optional[int]]:
        """
        Generate answer using LLM.
        
        Args:
            question: User question
            context: Retrieved context
            temperature: LLM temperature
            max_tokens: Max tokens in response
            
        Returns:
            Tuple of (answer, tokens_used)
        """
        # Build prompt
        prompt = self._build_prompt(question, context)
        
        if self.provider == LLMProvider.OPENAI:
            return self._generate_openai(prompt, temperature, max_tokens)
        elif self.provider == LLMProvider.ANTHROPIC:
            return self._generate_anthropic(prompt, temperature, max_tokens)
        elif self.provider == LLMProvider.OLLAMA:
            return self._generate_ollama(prompt, temperature, max_tokens)
        else:
            return self._generate_mock(question, context)
    
    def _build_prompt(self, question: str, context: str) -> str:
        """Build prompt for LLM."""
        return f"""You are an HR policy assistant. Answer questions based ONLY on the provided context from company documents.

IMPORTANT RULES:
1. Only use information from the context provided below
2. If the context doesn't contain enough information, say so
3. Be specific and cite page numbers when possible
4. Keep answers concise and relevant
5. Do not make up information not in the context

Context from HR documents:
{context}

Question: {question}

Answer based on the context above:"""
    
    def _generate_openai(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int
    ) -> Tuple[str, Optional[int]]:
        """Generate answer using OpenAI."""
        try:
            response = self.llm_client.ChatCompletion.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful HR policy assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            answer = response.choices[0].message.content
            tokens = response.usage.total_tokens
            
            return answer, tokens
            
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            return f"Error generating response: {e}", None
    
    def _generate_anthropic(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int
    ) -> Tuple[str, Optional[int]]:
        """Generate answer using Anthropic Claude."""
        try:
            message = self.llm_client.messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            answer = message.content[0].text
            tokens = message.usage.input_tokens + message.usage.output_tokens
            
            return answer, tokens
            
        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")
            return f"Error generating response: {e}", None
    
    def _generate_ollama(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int
    ) -> Tuple[str, Optional[int]]:
        """Generate answer using Ollama (local)."""
        try:
            response = self.llm_client.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            )
            
            answer = response['response']
            return answer, None  # Ollama doesn't return token count
            
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            return f"Error generating response: {e}", None
    
    def _generate_mock(self, question: str, context: str) -> Tuple[str, Optional[int]]:
        """Generate mock answer for testing."""
        # Extract first source info
        lines = context.split('\n')
        source_line = lines[0] if lines else "[No source]"
        
        answer = f"""Based on the company documentation, here's what I found regarding your question about "{question}":

{source_line}

The documents indicate relevant information on this topic. For specific details, please refer to the source citations below.

Note: This is a mock response for testing. Configure a real LLM provider (OpenAI, Anthropic, or Ollama) for actual answers."""
        
        return answer, 150  # Mock token count
    
    def _create_citations(self, results: List[SearchResult]) -> List[Citation]:
        """Create citation objects from search results."""
        citations = []
        
        for result in results:
            citation = Citation(
                source_doc=result.source_doc or "Unknown",
                page_number=result.page_number or 0,
                section_title=result.section_title,
                chunk_id=result.chunk_id,
                relevance_score=result.score,
                text_excerpt=result.text[:200] + "..." if len(result.text) > 200 else result.text
            )
            citations.append(citation)
        
        return citations
    
    def ask_with_context_window(
        self,
        question: str,
        top_k: int = 3,
        window_size: int = 1,
        **kwargs
    ) -> RAGResponse:
        """
        Ask question with expanded context (neighboring chunks).
        
        Args:
            question: User question
            top_k: Number of initial chunks to retrieve
            window_size: Number of neighboring chunks to include
            **kwargs: Additional arguments for ask()
            
        Returns:
            RAGResponse with expanded context
        """
        # Get initial results
        retrieval_result = self.retriever.search(question, top_k=top_k)
        
        if not retrieval_result.results:
            return self.ask(question, top_k=top_k, **kwargs)
        
        # Expand context with neighboring chunks
        expanded_results = []
        seen_chunk_ids = set()
        
        for result in retrieval_result.results:
            # Get context window
            context_chunks = retrieval_result.get_context_window(
                result_index=retrieval_result.results.index(result),
                window_size=window_size
            )
            
            for chunk in context_chunks:
                if chunk.chunk_id not in seen_chunk_ids:
                    expanded_results.append(chunk)
                    seen_chunk_ids.add(chunk.chunk_id)
        
        # Build context and generate answer
        context = self._build_context(expanded_results)
        answer, tokens = self._generate_answer(
            question=question,
            context=context,
            temperature=kwargs.get('temperature', 0.3),
            max_tokens=kwargs.get('max_tokens', 1000)
        )
        
        citations = self._create_citations(retrieval_result.results[:top_k])
        
        return RAGResponse(
            question=question,
            answer=answer,
            citations=citations,
            context_used=[r.text for r in expanded_results],
            model=self.model_name,
            tokens_used=tokens
        )
    
    def batch_ask(
        self,
        questions: List[str],
        **kwargs
    ) -> List[RAGResponse]:
        """
        Process multiple questions in batch.
        
        Args:
            questions: List of questions
            **kwargs: Arguments for ask()
            
        Returns:
            List of RAGResponse objects
        """
        responses = []
        
        for question in questions:
            try:
                response = self.ask(question, **kwargs)
                responses.append(response)
            except Exception as e:
                logger.error(f"Failed to process question '{question}': {e}")
                # Add error response
                responses.append(RAGResponse(
                    question=question,
                    answer=f"Error processing question: {e}",
                    citations=[],
                    context_used=[],
                    model=self.model_name
                ))
        
        return responses
    
    def get_model_info(self) -> Dict:
        """Get information about the RAG pipeline configuration."""
        return {
            "provider": self.provider.value,
            "model": self.model_name,
            "retriever": "ChromaDB text-based",
            "vector_db_path": self.config.vector_db_path,
            "chunk_size": self.config.chunk_size,
            "chunk_overlap": self.config.chunk_overlap
        }
