"""
CLI for RAG Pipeline

Interactive command-line interface for asking questions against HR documents.

Usage:
    # Ask a single question (mock mode)
    python -m app.rag.cli ask "What is the vacation policy?"
    
    # Interactive mode
    python -m app.rag.cli interactive
    
    # With OpenAI
    python -m app.rag.cli ask "What is the vacation policy?" --provider openai --model gpt-4
    
    # With filters
    python -m app.rag.cli ask "PTO policy?" --document Software_Company_Docupedia_FILLED.pdf
    
    # Batch questions
    python -m app.rag.cli batch questions.txt --output answers.json

Related: Phase 2 (P2), Task 2.2 - RAG Pipeline CLI
"""

import argparse
import sys
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict

from app.rag.pipeline import RAGPipeline, LLMProvider, RAGResponse


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_response(response: RAGResponse, verbose: bool = False):
    """Pretty print RAG response."""
    print("\n" + "=" * 80)
    print(f"Question: {response.question}")
    print("=" * 80)
    print(f"\nAnswer:\n{response.answer}")
    
    if response.citations:
        print(f"\n{'-' * 80}")
        print(f"Sources ({len(response.citations)} citations):")
        print(f"{'-' * 80}")
        
        for i, citation in enumerate(response.citations, 1):
            print(f"\n{i}. {citation.source_doc}")
            print(f"   Page: {citation.page_number}")
            if citation.section_title:
                print(f"   Section: {citation.section_title}")
            print(f"   Relevance: {citation.relevance_score:.4f}")
            
            if verbose:
                print(f"   Excerpt: {citation.text_excerpt}")
    
    print(f"\n{'-' * 80}")
    print(f"Model: {response.model}")
    if response.tokens_used:
        print(f"Tokens: {response.tokens_used}")
    print(f"Sources: {', '.join(response.get_unique_sources())}")
    page_range = response.get_page_range()
    if page_range[0] > 0:
        print(f"Pages: {page_range[0]}-{page_range[1]}")
    print("=" * 80 + "\n")


def cmd_ask(args):
    """Ask a single question."""
    logger.info(f"Asking question with {args.provider} provider")
    
    # Initialize pipeline
    pipeline = RAGPipeline(
        provider=LLMProvider(args.provider),
        model_name=args.model,
        api_key=args.api_key
    )
    
    # Build filters if provided
    filters = {}
    if args.document:
        filters['source_filename'] = args.document
    if args.page:
        filters['page_number'] = args.page
    
    # Ask question
    try:
        response = pipeline.ask(
            question=args.question,
            top_k=args.top_k,
            filters=filters if filters else None,
            temperature=args.temperature,
            max_tokens=args.max_tokens
        )
        
        print_response(response, verbose=args.verbose)
        
        # Save to file if requested
        if args.output:
            output_path = Path(args.output)
            output_data = {
                'question': response.question,
                'answer': response.answer,
                'citations': [
                    {
                        'source': c.source_doc,
                        'page': c.page_number,
                        'section': c.section_title,
                        'score': c.relevance_score
                    }
                    for c in response.citations
                ],
                'model': response.model,
                'tokens': response.tokens_used,
                'generated_at': response.generated_at
            }
            
            output_path.write_text(json.dumps(output_data, indent=2))
            print(f"✓ Response saved to: {output_path}")
        
    except Exception as e:
        logger.error(f"Failed to process question: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def cmd_interactive(args):
    """Interactive question-answering mode."""
    print("\n" + "=" * 80)
    print("RAG PIPELINE - INTERACTIVE MODE")
    print("=" * 80)
    print(f"Provider: {args.provider}")
    print(f"Model: {args.model or 'default'}")
    print("\nType your questions below.")
    print("Commands: 'quit' or 'exit' to stop, 'info' for pipeline info")
    print("=" * 80 + "\n")
    
    # Initialize pipeline
    pipeline = RAGPipeline(
        provider=LLMProvider(args.provider),
        model_name=args.model,
        api_key=args.api_key
    )
    
    while True:
        try:
            question = input("\nQuestion: ").strip()
            
            if not question:
                continue
            
            if question.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye!")
                break
            
            if question.lower() == 'info':
                info = pipeline.get_model_info()
                print("\nPipeline Configuration:")
                for key, value in info.items():
                    print(f"  {key}: {value}")
                continue
            
            # Process question
            response = pipeline.ask(
                question=question,
                top_k=args.top_k,
                temperature=args.temperature,
                max_tokens=args.max_tokens
            )
            
            print_response(response, verbose=args.verbose)
            
        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye!")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()


def cmd_batch(args):
    """Process batch of questions from file."""
    questions_file = Path(args.questions_file)
    
    if not questions_file.exists():
        print(f"❌ Questions file not found: {questions_file}")
        sys.exit(1)
    
    # Read questions
    questions = [
        line.strip()
        for line in questions_file.read_text().split('\n')
        if line.strip() and not line.strip().startswith('#')
    ]
    
    print(f"\nProcessing {len(questions)} questions from {questions_file.name}...")
    
    # Initialize pipeline
    pipeline = RAGPipeline(
        provider=LLMProvider(args.provider),
        model_name=args.model,
        api_key=args.api_key
    )
    
    # Process batch
    responses = pipeline.batch_ask(
        questions=questions,
        top_k=args.top_k,
        temperature=args.temperature,
        max_tokens=args.max_tokens
    )
    
    # Display results
    for i, response in enumerate(responses, 1):
        print(f"\n{'=' * 80}")
        print(f"Question {i}/{len(questions)}")
        print_response(response, verbose=args.verbose)
    
    # Save to output file
    if args.output:
        output_path = Path(args.output)
        output_data = {
            'questions': [r.question for r in responses],
            'responses': [
                {
                    'question': r.question,
                    'answer': r.answer,
                    'citations': [
                        {
                            'source': c.source_doc,
                            'page': c.page_number,
                            'section': c.section_title,
                            'score': c.relevance_score
                        }
                        for c in r.citations
                    ],
                    'model': r.model,
                    'tokens': r.tokens_used,
                    'generated_at': r.generated_at
                }
                for r in responses
            ],
            'total_questions': len(questions),
            'total_tokens': sum(r.tokens_used or 0 for r in responses)
        }
        
        output_path.write_text(json.dumps(output_data, indent=2))
        print(f"\n✓ Results saved to: {output_path}")


def cmd_info(args):
    """Show pipeline information."""
    pipeline = RAGPipeline(
        provider=LLMProvider(args.provider),
        model_name=args.model,
        api_key=args.api_key
    )
    
    info = pipeline.get_model_info()
    
    print("\n" + "=" * 80)
    print("RAG PIPELINE CONFIGURATION")
    print("=" * 80)
    
    for key, value in info.items():
        print(f"{key:20s}: {value}")
    
    print("=" * 80 + "\n")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="RAG Pipeline CLI - Ask questions against HR documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ask single question (mock mode)
  %(prog)s ask "What is the vacation policy?"
  
  # Interactive mode
  %(prog)s interactive
  
  # With OpenAI
  %(prog)s ask "PTO policy?" --provider openai --model gpt-4
  
  # With document filter
  %(prog)s ask "What are the benefits?" --document company_handbook.pdf
  
  # Batch processing
  %(prog)s batch questions.txt --output answers.json
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Common arguments for all commands
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument(
        '--provider',
        choices=['openai', 'anthropic', 'ollama', 'mock'],
        default='mock',
        help='LLM provider (default: mock)'
    )
    common_parser.add_argument(
        '--model',
        help='Model name (e.g., gpt-4, claude-3-sonnet)'
    )
    common_parser.add_argument(
        '--api-key',
        help='API key for provider (or use env: OPENAI_API_KEY, ANTHROPIC_API_KEY)'
    )
    common_parser.add_argument(
        '--top-k',
        type=int,
        default=5,
        help='Number of chunks to retrieve (default: 5)'
    )
    common_parser.add_argument(
        '--temperature',
        type=float,
        default=0.3,
        help='LLM temperature 0-1 (default: 0.3)'
    )
    common_parser.add_argument(
        '--max-tokens',
        type=int,
        default=1000,
        help='Max tokens in response (default: 1000)'
    )
    common_parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show verbose output'
    )
    
    # Ask command
    ask_parser = subparsers.add_parser(
        'ask',
        parents=[common_parser],
        help='Ask a single question'
    )
    ask_parser.add_argument('question', help='Question to ask')
    ask_parser.add_argument('--document', help='Filter by document filename')
    ask_parser.add_argument('--page', type=int, help='Filter by page number')
    ask_parser.add_argument('--output', help='Save response to JSON file')
    
    # Interactive command
    interactive_parser = subparsers.add_parser(
        'interactive',
        parents=[common_parser],
        help='Interactive question-answering mode'
    )
    
    # Batch command
    batch_parser = subparsers.add_parser(
        'batch',
        parents=[common_parser],
        help='Process batch of questions'
    )
    batch_parser.add_argument('questions_file', help='File with questions (one per line)')
    batch_parser.add_argument('--output', help='Save results to JSON file')
    
    # Info command
    info_parser = subparsers.add_parser(
        'info',
        parents=[common_parser],
        help='Show pipeline configuration'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Route to command handlers
    if args.command == 'ask':
        cmd_ask(args)
    elif args.command == 'interactive':
        cmd_interactive(args)
    elif args.command == 'batch':
        cmd_batch(args)
    elif args.command == 'info':
        cmd_info(args)


if __name__ == '__main__':
    main()
