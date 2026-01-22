"""
Retrieval Precision/Recall Testing Suite

Measures search effectiveness:
- Precision: How many retrieved documents are relevant?
- Recall: How many relevant documents are retrieved?
- Mean Average Precision (MAP)
- Normalized Discounted Cumulative Gain (NDCG)
"""

import pytest
from typing import List, Dict, Set, Tuple
import statistics

from app.query.retriever import Retriever
from app.core.config import AppConfig


# ============================================================================
# Test Data: Queries with Expected Relevant Chunks
# ============================================================================

# Note: These would ideally be manually labeled or derived from ground truth
# For this implementation, we'll use heuristic relevance based on keywords
TEST_QUERIES = [
    {
        "query": "vacation policy",
        "expected_keywords": ["vacation", "time off", "PTO", "annual leave"],
        "category": "benefits"
    },
    {
        "query": "sick leave",
        "expected_keywords": ["sick", "illness", "medical leave"],
        "category": "benefits"
    },
    {
        "query": "remote work",
        "expected_keywords": ["remote", "work from home", "hybrid", "telecommute"],
        "category": "workplace"
    },
    {
        "query": "health insurance",
        "expected_keywords": ["health", "insurance", "medical", "coverage"],
        "category": "benefits"
    },
    {
        "query": "code of conduct",
        "expected_keywords": ["conduct", "behavior", "ethics", "professional"],
        "category": "policy"
    },
    {
        "query": "employee benefits",
        "expected_keywords": ["benefits", "compensation", "perks"],
        "category": "benefits"
    },
    {
        "query": "training and development",
        "expected_keywords": ["training", "development", "learning", "education"],
        "category": "growth"
    },
    {
        "query": "performance review",
        "expected_keywords": ["performance", "review", "evaluation", "assessment"],
        "category": "management"
    },
]


class RetrievalMetrics:
    """Calculate information retrieval metrics."""
    
    @staticmethod
    def calculate_relevance(chunk_text: str, expected_keywords: List[str]) -> float:
        """
        Calculate relevance score based on keyword matching.
        Returns value between 0.0 and 1.0.
        """
        if not chunk_text or not expected_keywords:
            return 0.0
        
        text_lower = chunk_text.lower()
        matches = sum(1 for keyword in expected_keywords if keyword.lower() in text_lower)
        return matches / len(expected_keywords)
    
    @staticmethod
    def precision_at_k(relevant_items: List[bool], k: int) -> float:
        """
        Calculate precision@k: fraction of retrieved items that are relevant.
        """
        if k == 0 or not relevant_items:
            return 0.0
        
        relevant_in_top_k = sum(relevant_items[:k])
        return relevant_in_top_k / min(k, len(relevant_items))
    
    @staticmethod
    def recall_at_k(relevant_items: List[bool], total_relevant: int, k: int) -> float:
        """
        Calculate recall@k: fraction of relevant items that are retrieved.
        """
        if total_relevant == 0 or not relevant_items:
            return 0.0
        
        relevant_in_top_k = sum(relevant_items[:k])
        return relevant_in_top_k / total_relevant
    
    @staticmethod
    def average_precision(relevant_items: List[bool]) -> float:
        """
        Calculate average precision (AP) for a single query.
        """
        if not relevant_items or sum(relevant_items) == 0:
            return 0.0
        
        precisions = []
        relevant_count = 0
        
        for i, is_relevant in enumerate(relevant_items, 1):
            if is_relevant:
                relevant_count += 1
                precision = relevant_count / i
                precisions.append(precision)
        
        return sum(precisions) / sum(relevant_items)
    
    @staticmethod
    def mean_average_precision(query_aps: List[float]) -> float:
        """
        Calculate Mean Average Precision (MAP) across all queries.
        """
        if not query_aps:
            return 0.0
        return sum(query_aps) / len(query_aps)
    
    @staticmethod
    def dcg_at_k(relevance_scores: List[float], k: int) -> float:
        """
        Calculate Discounted Cumulative Gain (DCG) at k.
        """
        if not relevance_scores or k == 0:
            return 0.0
        
        dcg = 0.0
        for i, score in enumerate(relevance_scores[:k], 1):
            if i == 1:
                dcg += score
            else:
                dcg += score / (i ** 0.5)  # log2(i+1) simplified
        
        return dcg
    
    @staticmethod
    def ndcg_at_k(relevance_scores: List[float], k: int) -> float:
        """
        Calculate Normalized Discounted Cumulative Gain (NDCG) at k.
        """
        if not relevance_scores or k == 0:
            return 0.0
        
        dcg = RetrievalMetrics.dcg_at_k(relevance_scores, k)
        
        # Ideal DCG (scores sorted in descending order)
        ideal_scores = sorted(relevance_scores, reverse=True)
        idcg = RetrievalMetrics.dcg_at_k(ideal_scores, k)
        
        if idcg == 0:
            return 0.0
        
        return dcg / idcg


@pytest.fixture
def retriever():
    """Create retriever for testing."""
    config = AppConfig()
    return Retriever(config=config)


# ============================================================================
# Precision Tests
# ============================================================================

class TestPrecision:
    """Test retrieval precision metrics."""
    
    def test_precision_at_1(self, retriever):
        """Test precision@1 (is the top result relevant?)."""
        precisions = []
        
        for item in TEST_QUERIES:
            results = retriever.search(item["query"], top_k=10)
            
            if results.chunks:
                # Check if top result is relevant
                top_chunk = results.chunks[0]
                relevance = RetrievalMetrics.calculate_relevance(
                    top_chunk, item["expected_keywords"]
                )
                is_relevant = relevance > 0.3  # 30% threshold
                precision = 1.0 if is_relevant else 0.0
            else:
                precision = 0.0
            
            precisions.append(precision)
            print(f"\n{item['query']}: P@1 = {precision:.2f}")
        
        avg_precision = sum(precisions) / len(precisions)
        print(f"\nAverage Precision@1: {avg_precision:.2%}")
        
        # At least 60% of top results should be relevant
        assert avg_precision >= 0.60, f"Low P@1: {avg_precision:.2%}"
    
    def test_precision_at_5(self, retriever):
        """Test precision@5 (what fraction of top 5 are relevant?)."""
        precisions = []
        
        for item in TEST_QUERIES:
            results = retriever.search(item["query"], top_k=10)
            
            relevant_items = []
            for chunk in results.chunks[:5]:
                relevance = RetrievalMetrics.calculate_relevance(
                    chunk, item["expected_keywords"]
                )
                relevant_items.append(relevance > 0.3)
            
            precision = RetrievalMetrics.precision_at_k(relevant_items, 5)
            precisions.append(precision)
            print(f"\n{item['query']}: P@5 = {precision:.2%}")
        
        avg_precision = sum(precisions) / len(precisions)
        print(f"\nAverage Precision@5: {avg_precision:.2%}")
        
        # At least 50% relevant in top 5
        assert avg_precision >= 0.50, f"Low P@5: {avg_precision:.2%}"
    
    def test_precision_at_10(self, retriever):
        """Test precision@10."""
        precisions = []
        
        for item in TEST_QUERIES:
            results = retriever.search(item["query"], top_k=10)
            
            relevant_items = []
            for chunk in results.chunks:
                relevance = RetrievalMetrics.calculate_relevance(
                    chunk, item["expected_keywords"]
                )
                relevant_items.append(relevance > 0.3)
            
            precision = RetrievalMetrics.precision_at_k(relevant_items, 10)
            precisions.append(precision)
            print(f"\n{item['query']}: P@10 = {precision:.2%}")
        
        avg_precision = sum(precisions) / len(precisions)
        print(f"\nAverage Precision@10: {avg_precision:.2%}")
        
        # At least 40% relevant in top 10
        assert avg_precision >= 0.40, f"Low P@10: {avg_precision:.2%}"


# ============================================================================
# Recall Tests
# ============================================================================

class TestRecall:
    """Test retrieval recall metrics."""
    
    def test_recall_with_varying_k(self, retriever):
        """Test how recall improves with more results."""
        for item in TEST_QUERIES:
            # First, find all potentially relevant chunks
            all_results = retriever.search(item["query"], top_k=50)
            
            relevant_chunks = []
            for chunk in all_results.chunks:
                relevance = RetrievalMetrics.calculate_relevance(
                    chunk, item["expected_keywords"]
                )
                if relevance > 0.3:
                    relevant_chunks.append(chunk)
            
            total_relevant = len(relevant_chunks)
            
            if total_relevant == 0:
                continue
            
            # Test recall at different k values
            print(f"\n{item['query']} (total relevant: {total_relevant}):")
            
            for k in [1, 5, 10, 20]:
                results = retriever.search(item["query"], top_k=k)
                
                relevant_in_top_k = 0
                for chunk in results.chunks:
                    relevance = RetrievalMetrics.calculate_relevance(
                        chunk, item["expected_keywords"]
                    )
                    if relevance > 0.3:
                        relevant_in_top_k += 1
                
                recall = relevant_in_top_k / total_relevant
                print(f"  Recall@{k}: {recall:.2%} ({relevant_in_top_k}/{total_relevant})")
    
    def test_recall_improves_with_k(self, retriever):
        """Verify that recall increases as k increases."""
        for item in TEST_QUERIES:
            recalls = []
            
            # Get results at different k values
            for k in [1, 5, 10, 20]:
                results = retriever.search(item["query"], top_k=k)
                
                relevant_count = 0
                for chunk in results.chunks:
                    relevance = RetrievalMetrics.calculate_relevance(
                        chunk, item["expected_keywords"]
                    )
                    if relevance > 0.3:
                        relevant_count += 1
                
                recalls.append(relevant_count)
            
            # Recall should be non-decreasing
            for i in range(len(recalls) - 1):
                assert recalls[i] <= recalls[i + 1], \
                    f"Recall decreased for {item['query']}: {recalls}"


# ============================================================================
# Average Precision Tests
# ============================================================================

class TestAveragePrecision:
    """Test Average Precision (AP) metrics."""
    
    def test_average_precision_per_query(self, retriever):
        """Calculate average precision for each query."""
        aps = []
        
        for item in TEST_QUERIES:
            results = retriever.search(item["query"], top_k=20)
            
            relevant_items = []
            for chunk in results.chunks:
                relevance = RetrievalMetrics.calculate_relevance(
                    chunk, item["expected_keywords"]
                )
                relevant_items.append(relevance > 0.3)
            
            if any(relevant_items):
                ap = RetrievalMetrics.average_precision(relevant_items)
                aps.append(ap)
                print(f"\n{item['query']}: AP = {ap:.3f}")
            else:
                print(f"\n{item['query']}: No relevant results")
        
        if aps:
            print(f"\nAverage Precision scores: {aps}")
            # All queries should have decent AP
            assert all(ap > 0.2 for ap in aps), "Some queries have very low AP"
    
    def test_mean_average_precision(self, retriever):
        """Calculate Mean Average Precision (MAP) across all queries."""
        aps = []
        
        for item in TEST_QUERIES:
            results = retriever.search(item["query"], top_k=20)
            
            relevant_items = []
            for chunk in results.chunks:
                relevance = RetrievalMetrics.calculate_relevance(
                    chunk, item["expected_keywords"]
                )
                relevant_items.append(relevance > 0.3)
            
            ap = RetrievalMetrics.average_precision(relevant_items)
            aps.append(ap)
        
        map_score = RetrievalMetrics.mean_average_precision(aps)
        print(f"\nMean Average Precision (MAP): {map_score:.3f}")
        
        # MAP should be reasonable
        assert map_score >= 0.30, f"Low MAP: {map_score:.3f}"


# ============================================================================
# NDCG Tests
# ============================================================================

class TestNDCG:
    """Test Normalized Discounted Cumulative Gain."""
    
    def test_ndcg_at_5(self, retriever):
        """Calculate NDCG@5 for all queries."""
        ndcg_scores = []
        
        for item in TEST_QUERIES:
            results = retriever.search(item["query"], top_k=10)
            
            relevance_scores = []
            for chunk in results.chunks[:5]:
                relevance = RetrievalMetrics.calculate_relevance(
                    chunk, item["expected_keywords"]
                )
                relevance_scores.append(relevance)
            
            if relevance_scores:
                ndcg = RetrievalMetrics.ndcg_at_k(relevance_scores, 5)
                ndcg_scores.append(ndcg)
                print(f"\n{item['query']}: NDCG@5 = {ndcg:.3f}")
        
        avg_ndcg = sum(ndcg_scores) / len(ndcg_scores) if ndcg_scores else 0
        print(f"\nAverage NDCG@5: {avg_ndcg:.3f}")
        
        # NDCG should be reasonable
        assert avg_ndcg >= 0.40, f"Low NDCG@5: {avg_ndcg:.3f}"
    
    def test_ndcg_at_10(self, retriever):
        """Calculate NDCG@10 for all queries."""
        ndcg_scores = []
        
        for item in TEST_QUERIES:
            results = retriever.search(item["query"], top_k=10)
            
            relevance_scores = []
            for chunk in results.chunks:
                relevance = RetrievalMetrics.calculate_relevance(
                    chunk, item["expected_keywords"]
                )
                relevance_scores.append(relevance)
            
            if relevance_scores:
                ndcg = RetrievalMetrics.ndcg_at_k(relevance_scores, 10)
                ndcg_scores.append(ndcg)
                print(f"\n{item['query']}: NDCG@10 = {ndcg:.3f}")
        
        avg_ndcg = sum(ndcg_scores) / len(ndcg_scores) if ndcg_scores else 0
        print(f"\nAverage NDCG@10: {avg_ndcg:.3f}")
        
        # NDCG should be reasonable
        assert avg_ndcg >= 0.35, f"Low NDCG@10: {avg_ndcg:.3f}"


# ============================================================================
# Query Type Analysis
# ============================================================================

class TestQueryTypePerformance:
    """Analyze retrieval performance by query type."""
    
    def test_performance_by_category(self, retriever):
        """Compare retrieval performance across categories."""
        category_results = {}
        
        for item in TEST_QUERIES:
            category = item["category"]
            if category not in category_results:
                category_results[category] = {
                    "precisions": [],
                    "recalls": [],
                    "ndcgs": []
                }
            
            results = retriever.search(item["query"], top_k=10)
            
            # Calculate metrics
            relevant_items = []
            relevance_scores = []
            for chunk in results.chunks:
                relevance = RetrievalMetrics.calculate_relevance(
                    chunk, item["expected_keywords"]
                )
                relevant_items.append(relevance > 0.3)
                relevance_scores.append(relevance)
            
            precision = RetrievalMetrics.precision_at_k(relevant_items, 5)
            ndcg = RetrievalMetrics.ndcg_at_k(relevance_scores, 5)
            
            category_results[category]["precisions"].append(precision)
            category_results[category]["ndcgs"].append(ndcg)
        
        # Print results by category
        print("\nPerformance by Category:")
        for category, metrics in category_results.items():
            avg_p = statistics.mean(metrics["precisions"]) if metrics["precisions"] else 0
            avg_ndcg = statistics.mean(metrics["ndcgs"]) if metrics["ndcgs"] else 0
            
            print(f"\n{category.upper()}:")
            print(f"  Avg Precision@5: {avg_p:.2%}")
            print(f"  Avg NDCG@5: {avg_ndcg:.3f}")
    
    def test_short_vs_long_queries(self, retriever):
        """Compare performance on short vs long queries."""
        short_query_results = []
        long_query_results = []
        
        for item in TEST_QUERIES:
            query_length = len(item["query"].split())
            results = retriever.search(item["query"], top_k=10)
            
            relevant_items = []
            for chunk in results.chunks:
                relevance = RetrievalMetrics.calculate_relevance(
                    chunk, item["expected_keywords"]
                )
                relevant_items.append(relevance > 0.3)
            
            precision = RetrievalMetrics.precision_at_k(relevant_items, 5)
            
            if query_length <= 2:
                short_query_results.append(precision)
            else:
                long_query_results.append(precision)
        
        print("\nPerformance by Query Length:")
        if short_query_results:
            print(f"Short queries (≤2 words): P@5 = {statistics.mean(short_query_results):.2%}")
        if long_query_results:
            print(f"Long queries (>2 words): P@5 = {statistics.mean(long_query_results):.2%}")


# ============================================================================
# Comprehensive Retrieval Report
# ============================================================================

def test_comprehensive_retrieval_metrics(retriever):
    """Generate comprehensive retrieval metrics report."""
    print("\n" + "="*80)
    print("COMPREHENSIVE RETRIEVAL METRICS REPORT")
    print("="*80)
    
    all_precisions_at_1 = []
    all_precisions_at_5 = []
    all_precisions_at_10 = []
    all_aps = []
    all_ndcgs = []
    
    for item in TEST_QUERIES:
        results = retriever.search(item["query"], top_k=20)
        
        # Calculate relevance for all chunks
        relevant_items = []
        relevance_scores = []
        for chunk in results.chunks:
            relevance = RetrievalMetrics.calculate_relevance(
                chunk, item["expected_keywords"]
            )
            relevant_items.append(relevance > 0.3)
            relevance_scores.append(relevance)
        
        # Calculate all metrics
        p_at_1 = RetrievalMetrics.precision_at_k(relevant_items, 1)
        p_at_5 = RetrievalMetrics.precision_at_k(relevant_items, 5)
        p_at_10 = RetrievalMetrics.precision_at_k(relevant_items, 10)
        ap = RetrievalMetrics.average_precision(relevant_items)
        ndcg = RetrievalMetrics.ndcg_at_k(relevance_scores, 10)
        
        all_precisions_at_1.append(p_at_1)
        all_precisions_at_5.append(p_at_5)
        all_precisions_at_10.append(p_at_10)
        all_aps.append(ap)
        all_ndcgs.append(ndcg)
        
        print(f"\n{item['query']}:")
        print(f"  P@1: {p_at_1:.2%}, P@5: {p_at_5:.2%}, P@10: {p_at_10:.2%}")
        print(f"  AP: {ap:.3f}, NDCG@10: {ndcg:.3f}")
    
    # Overall statistics
    print("\n" + "="*80)
    print("OVERALL METRICS:")
    print(f"  Average P@1:   {statistics.mean(all_precisions_at_1):.2%}")
    print(f"  Average P@5:   {statistics.mean(all_precisions_at_5):.2%}")
    print(f"  Average P@10:  {statistics.mean(all_precisions_at_10):.2%}")
    print(f"  MAP:           {statistics.mean(all_aps):.3f}")
    print(f"  Average NDCG:  {statistics.mean(all_ndcgs):.3f}")
    print("="*80 + "\n")


if __name__ == "__main__":
    # Run with: python -m pytest tests/evaluation/test_retrieval.py -v -s
    pytest.main([__file__, "-v", "-s"])
