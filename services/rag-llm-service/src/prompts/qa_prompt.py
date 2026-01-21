"""
Question-answering prompt templates for RAG pipeline.

This module provides prompt engineering for the LLM to generate answers
with proper citation formatting and grounding in retrieved context.
"""

from typing import List, Dict, Any


SYSTEM_INSTRUCTIONS = """You are a helpful corporate knowledge assistant. Your role is to answer questions based ONLY on the provided context from internal documents.

CRITICAL RULES:
1. ANSWER ONLY from the provided context - do not use external knowledge
2. CITE YOUR SOURCES using the format: [document_name, section_title]
3. If the context doesn't contain the answer, respond with: "I don't know - this information is not available in the provided documents."
4. Be concise and direct - avoid unnecessary preamble
5. Include relevant citations inline within your answer

CITATION FORMAT EXAMPLES:
- "According to the safety manual [safety_manual.pdf, Chemical Handling], all personnel must wear protective gear."
- "The vacation policy [hr_policy.pdf, Time Off] states that employees receive 20 days annually."

Remember: NEVER make up information. If unsure, say "I don't know"."""


def format_context_block(
    chunks: List[Dict[str, Any]], include_metadata: bool = True
) -> str:
    """
    Format retrieved chunks into a context block for the LLM prompt.

    Args:
        chunks: List of retrieved chunk dictionaries with content and metadata
        include_metadata: Whether to include document/section metadata

    Returns:
        Formatted context string for prompt
    """
    if not chunks:
        return "No relevant context found."

    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        content = chunk.get("content", "")
        metadata = chunk.get("metadata", {})

        if include_metadata:
            doc_name = metadata.get("document_name", "unknown")
            section = metadata.get("section", "")
            page = metadata.get("page_number")

            # Build metadata header
            meta_parts = [f"Document: {doc_name}"]
            if section:
                meta_parts.append(f"Section: {section}")
            if page is not None:
                meta_parts.append(f"Page: {page}")

            context_parts.append(
                f"[Context {i}]\n" + " | ".join(meta_parts) + "\n" + f"{content}\n"
            )
        else:
            context_parts.append(f"[Context {i}]\n{content}\n")

    return "\n".join(context_parts)


def build_qa_prompt(
    question: str,
    retrieved_chunks: List[Dict[str, Any]],
    include_system_instructions: bool = True,
) -> str:
    """
    Build complete Q&A prompt for the LLM.

    Args:
        question: User's question
        retrieved_chunks: List of retrieved context chunks
        include_system_instructions: Whether to include system instructions

    Returns:
        Complete prompt string ready for LLM
    """
    # Format context from retrieved chunks
    context = format_context_block(retrieved_chunks, include_metadata=True)

    # Build prompt sections
    prompt_parts = []

    if include_system_instructions:
        prompt_parts.append(SYSTEM_INSTRUCTIONS)
        prompt_parts.append("\n" + "=" * 80 + "\n")

    prompt_parts.append("CONTEXT FROM RETRIEVED DOCUMENTS:\n")
    prompt_parts.append(context)
    prompt_parts.append("\n" + "=" * 80 + "\n")

    prompt_parts.append(f"QUESTION: {question}\n")
    prompt_parts.append("\nANSWER (with citations):")

    return "\n".join(prompt_parts)
