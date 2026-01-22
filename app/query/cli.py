"""
Interactive CLI for testing query/retrieval functionality.

Usage:
    python -m app.query.cli search "vacation policy" --top-k 5
    python -m app.query.cli search "benefits" --page 3
    python -m app.query.cli document <document_id>
    python -m app.query.cli stats
"""

import argparse
import sys
import logging
from pathlib import Path
from typing import Optional

from app.query.retriever import Retriever, RetrievalResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def print_results(result: RetrievalResult, verbose: bool = False):
    """Pretty print search results."""
    print("\n" + "=" * 80)
    print(f"QUERY: {result.query}")
    print("=" * 80)
    print(f"Found {result.total_results} results")
    
    if result.filters_applied:
        print(f"Filters: {result.filters_applied}")
    
    print()
    
    for i, r in enumerate(result.results, 1):
        print(f"[{i}] Score: {r.score:.4f}")
        print(f"    Document: {r.source_doc}")
        print(f"    Page: {r.page_number}, Section: {r.section_title or 'N/A'}")
        print(f"    Chunk ID: {r.chunk_id}")
        
        # Show text preview
        preview_length = 300 if verbose else 150
        text_preview = r.text[:preview_length]
        if len(r.text) > preview_length:
            text_preview += "..."
        
        print(f"    Text: {text_preview}")
        print()


def cmd_search(args):
    """Execute search command."""
    retriever = Retriever()
    
    # Build filters
    filters = {}
    if args.document:
        filters['document_id'] = args.document
    if args.page:
        filters['page_number'] = args.page
    if args.section:
        filters['section_title'] = args.section
    
    # Execute search
    result = retriever.search(
        query=args.query,
        top_k=args.top_k,
        filters=filters if filters else None,
        min_score=args.min_score
    )
    
    print_results(result, verbose=args.verbose)
    
    # Show context if requested
    if args.context and result.results:
        print("\n" + "=" * 80)
        print("CONTEXT WINDOW (neighboring chunks)")
        print("=" * 80)
        
        context = result.get_context_window(result_index=0, window_size=args.context)
        for i, chunk in enumerate(context):
            marker = " <-- MATCH" if chunk == result.results[0] else ""
            print(f"\nChunk {chunk.metadata.get('chunk_index', '?')}{marker}:")
            print(f"  {chunk.text[:200]}...")


def cmd_get_chunk(args):
    """Retrieve a specific chunk by ID."""
    retriever = Retriever()
    chunk = retriever.get_chunk_by_id(args.chunk_id)
    
    if chunk:
        print("\n" + "=" * 80)
        print(f"CHUNK: {chunk.chunk_id}")
        print("=" * 80)
        print(f"Document: {chunk.source_doc}")
        print(f"Page: {chunk.page_number}, Section: {chunk.section_title or 'N/A'}")
        print(f"\nText:\n{chunk.text}")
        print("\n" + "=" * 80)
    else:
        print(f"❌ Chunk not found: {args.chunk_id}")
        sys.exit(1)


def cmd_document(args):
    """Get all chunks for a document."""
    retriever = Retriever()
    
    chunks = retriever.get_document_chunks(
        document_id=args.document_id,
        page_number=args.page
    )
    
    print("\n" + "=" * 80)
    print(f"DOCUMENT: {args.document_id}")
    if args.page:
        print(f"PAGE: {args.page}")
    print("=" * 80)
    print(f"Total chunks: {len(chunks)}\n")
    
    for i, chunk in enumerate(chunks, 1):
        print(f"[{i}] Chunk {chunk.metadata.get('chunk_index', '?')} - Page {chunk.page_number}")
        if args.verbose:
            print(f"    {chunk.text[:150]}...\n")


def cmd_multi_search(args):
    """Search with multiple queries."""
    retriever = Retriever()
    
    queries = [q.strip() for q in args.queries.split(',')]
    
    result = retriever.multi_query_search(
        queries=queries,
        top_k=args.top_k,
        merge_strategy='union'
    )
    
    print_results(result, verbose=args.verbose)


def cmd_stats(args):
    """Show retrieval statistics."""
    retriever = Retriever()
    stats = retriever.get_statistics()
    
    print("\n" + "=" * 80)
    print("RETRIEVAL STATISTICS")
    print("=" * 80)
    
    for key, value in stats.items():
        print(f"{key:25}: {value}")
    
    print()


def cmd_interactive(args):
    """Interactive search mode."""
    retriever = Retriever()
    
    print("\n" + "=" * 80)
    print("INTERACTIVE SEARCH MODE")
    print("=" * 80)
    print("Enter search queries (or 'quit' to exit)")
    print()
    
    while True:
        try:
            query = input("Query> ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if not query:
                continue
            
            result = retriever.search(query, top_k=5)
            print_results(result, verbose=False)
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Query/Retrieval CLI for HR Data Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic search
  python -m app.query.cli search "vacation policy" --top-k 5
  
  # Search with filters
  python -m app.query.cli search "benefits" --page 3 --top-k 10
  
  # Search within document
  python -m app.query.cli search "remote work" --document pdf-abc123
  
  # Get specific chunk
  python -m app.query.cli chunk <chunk-id>
  
  # Get all chunks for document
  python -m app.query.cli document <document-id> --page 5
  
  # Multi-query search
  python -m app.query.cli multi "vacation,benefits,remote work" --top-k 3
  
  # Show statistics
  python -m app.query.cli stats
  
  # Interactive mode
  python -m app.query.cli interactive
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search for documents')
    search_parser.add_argument('query', type=str, help='Search query text')
    search_parser.add_argument('--top-k', type=int, default=5, help='Number of results (default: 5)')
    search_parser.add_argument('--document', type=str, help='Filter by document ID')
    search_parser.add_argument('--page', type=int, help='Filter by page number')
    search_parser.add_argument('--section', type=str, help='Filter by section title')
    search_parser.add_argument('--min-score', type=float, help='Minimum relevance score')
    search_parser.add_argument('--context', type=int, help='Show context window (neighboring chunks)')
    search_parser.add_argument('--verbose', action='store_true', help='Show full text')
    search_parser.set_defaults(func=cmd_search)
    
    # Get chunk command
    chunk_parser = subparsers.add_parser('chunk', help='Get specific chunk by ID')
    chunk_parser.add_argument('chunk_id', type=str, help='Chunk ID')
    chunk_parser.set_defaults(func=cmd_get_chunk)
    
    # Get document command
    doc_parser = subparsers.add_parser('document', help='Get all chunks for document')
    doc_parser.add_argument('document_id', type=str, help='Document ID')
    doc_parser.add_argument('--page', type=int, help='Filter by page number')
    doc_parser.add_argument('--verbose', action='store_true', help='Show text previews')
    doc_parser.set_defaults(func=cmd_document)
    
    # Multi-query search command
    multi_parser = subparsers.add_parser('multi', help='Search with multiple queries')
    multi_parser.add_argument('queries', type=str, help='Comma-separated queries')
    multi_parser.add_argument('--top-k', type=int, default=3, help='Results per query')
    multi_parser.add_argument('--verbose', action='store_true', help='Show full text')
    multi_parser.set_defaults(func=cmd_multi_search)
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show retrieval statistics')
    stats_parser.set_defaults(func=cmd_stats)
    
    # Interactive command
    interactive_parser = subparsers.add_parser('interactive', help='Interactive search mode')
    interactive_parser.set_defaults(func=cmd_interactive)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        args.func(args)
    except Exception as e:
        logger.error(f"Command failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
