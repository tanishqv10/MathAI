"""
RAG System for Mathematical Explanation Knowledge.

Retrieves explanation-grade material from a vector database:
- Rule intuition
- Method-selection heuristics
- Common pitfalls
- Symbolic-engine behavior notes
"""
import os
import json
from typing import List, Optional
from pathlib import Path
from langfuse import observe
from .models import RoutingDecision, RetrievedChunk

# Try importing vector store dependencies
try:
    from chromadb import PersistentClient
    from chromadb.utils import embedding_functions
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class MathRAG:
    """
    RAG system for retrieving mathematical explanation knowledge.
    Uses ChromaDB for vector storage and OpenAI embeddings.
    """
    
    COLLECTION_NAME = "math_explanations"
    
    def __init__(
        self,
        persist_directory: Optional[str] = None,
        openai_client: Optional["OpenAI"] = None,
        embedding_model: str = "text-embedding-3-small"
    ):
        self.persist_directory = persist_directory or str(
            Path(__file__).parent.parent / "data" / "vectordb"
        )
        self.embedding_model = embedding_model
        self.openai_client = openai_client
        
        if CHROMA_AVAILABLE:
            self._init_chroma()
        else:
            self.collection = None
            print("Warning: ChromaDB not available. RAG will use fallback mode.")
    
    def _init_chroma(self):
        """Initialize ChromaDB with OpenAI embeddings."""
        os.makedirs(self.persist_directory, exist_ok=True)
        
        self.client = PersistentClient(path=self.persist_directory)
        
        # Use OpenAI embeddings
        if OPENAI_AVAILABLE:
            self.embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
                api_key=os.environ.get("OPENAI_API_KEY"),
                model_name=self.embedding_model
            )
        else:
            self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_knowledge(self, chunks: List[dict]):
        """
        Add knowledge chunks to the vector store.
        
        Args:
            chunks: List of dicts with keys: id, content, category, source
        """
        if not self.collection:
            return
        
        ids = [c["id"] for c in chunks]
        documents = [c["content"] for c in chunks]
        metadatas = [
            {"category": c.get("category", "general"), "source": c.get("source", "")}
            for c in chunks
        ]
        
        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
    
    def _build_query(self, routing: RoutingDecision) -> str:
        """Build a search query from the routing decision."""
        operation = routing.operation
        expression = routing.expression
        variable = routing.variable
        
        query_parts = [
            f"How to {operation} mathematical expressions",
            f"{operation} {expression}",
            f"Rules and methods for {operation}",
        ]
        
        if operation == "differentiate":
            query_parts.extend([
                "derivative rules chain rule product rule",
                f"differentiate with respect to {variable}"
            ])
        elif operation == "integrate":
            query_parts.extend([
                "integration techniques substitution parts",
                f"integrate with respect to {variable}"
            ])
        elif operation == "simplify":
            query_parts.extend([
                "simplification algebraic manipulation",
                "factoring expanding combining like terms"
            ])
        elif operation == "solve":
            query_parts.extend([
                "solving equations finding roots",
                "algebraic solution methods"
            ])
        
        return " ".join(query_parts)
    
    @observe(name="rag_retrieval")
    def retrieve(
        self,
        routing: RoutingDecision,
        n_results: int = 5
    ) -> List[RetrievedChunk]:
        """
        Retrieve relevant knowledge chunks for the given routing decision.
        
        Args:
            routing: The RoutingDecision from the router
            n_results: Number of chunks to retrieve
            
        Returns:
            List of RetrievedChunk objects
        """
        # Use fallback if ChromaDB not available
        if not self.collection:
            return self._fallback_retrieve(routing)
        
        query = self._build_query(routing)
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            chunks = []
            if results["ids"] and results["ids"][0]:
                for i, chunk_id in enumerate(results["ids"][0]):
                    # Convert distance to similarity score (cosine distance)
                    distance = results["distances"][0][i] if results["distances"] else 0
                    similarity = 1 - distance  # Convert distance to similarity
                    
                    chunks.append(RetrievedChunk(
                        chunk_id=chunk_id,
                        content=results["documents"][0][i],
                        category=results["metadatas"][0][i].get("category", "general"),
                        relevance_score=similarity,
                        source=results["metadatas"][0][i].get("source", "")
                    ))
            
            return chunks
            
        except Exception as e:
            print(f"RAG retrieval error: {e}")
            return self._fallback_retrieve(routing)
    
    def _fallback_retrieve(self, routing: RoutingDecision) -> List[RetrievedChunk]:
        """
        Fallback retrieval using built-in knowledge when vector DB unavailable.
        Returns curated explanation knowledge based on operation type.
        """
        operation = routing.operation
        
        # Built-in knowledge organized by operation
        knowledge = BUILTIN_KNOWLEDGE.get(operation, [])
        
        return [
            RetrievedChunk(
                chunk_id=f"builtin_{operation}_{i}",
                content=chunk["content"],
                category=chunk["category"],
                relevance_score=0.9,
                source="built-in knowledge base"
            )
            for i, chunk in enumerate(knowledge)
        ]
    
    def initialize_knowledge_base(self):
        """Initialize the knowledge base with curated content."""
        all_chunks = []
        
        for operation, chunks in BUILTIN_KNOWLEDGE.items():
            for i, chunk in enumerate(chunks):
                all_chunks.append({
                    "id": f"{operation}_{i}",
                    "content": chunk["content"],
                    "category": chunk["category"],
                    "source": chunk.get("source", "MathAI Knowledge Base")
                })
        
        self.add_knowledge(all_chunks)
        print(f"Initialized knowledge base with {len(all_chunks)} chunks")


# Built-in curated knowledge base
BUILTIN_KNOWLEDGE = {
    "differentiate": [
        {
            "category": "rule_intuition",
            "content": """The Chain Rule: When differentiating a composite function f(g(x)), 
multiply the derivative of the outer function (evaluated at the inner) by the derivative 
of the inner function. Intuitively, this captures how the rate of change propagates 
through nested functions. For sin(x²), the outer function is sin(u) and inner is u=x², 
so the derivative is cos(x²) · 2x."""
        },
        {
            "category": "rule_intuition",
            "content": """The Product Rule: For d/dx[f(x)·g(x)] = f'(x)·g(x) + f(x)·g'(x). 
Think of it as distributing the differentiation while keeping one factor intact. 
This arises because both functions are changing simultaneously, contributing to the 
total rate of change."""
        },
        {
            "category": "method_heuristic",
            "content": """When differentiating, identify the outermost operation first:
- Sum/difference → differentiate term by term
- Product → apply product rule
- Quotient → apply quotient rule
- Composition → apply chain rule
For complex expressions, work from the outside in, applying rules recursively."""
        },
        {
            "category": "pitfall",
            "content": """Common differentiation mistakes:
1. Forgetting the chain rule with inner function derivatives
2. Confusing d/dx[eˣ] = eˣ with d/dx[aˣ] = aˣ·ln(a)
3. For ln|x|, derivative is 1/x (absolute value often forgotten)
4. Power rule doesn't apply when the variable is in the exponent
5. d/dx[sin²(x)] requires chain rule: 2sin(x)cos(x)"""
        },
        {
            "category": "engine_note",
            "content": """SymPy's diff() function automatically applies simplification. 
It handles most standard functions but may return unevaluated Derivative objects 
for undefined or piecewise functions. Results are typically in simplified form, 
but explicit simplify() may further reduce the expression."""
        }
    ],
    "integrate": [
        {
            "category": "rule_intuition",
            "content": """Integration by Substitution (u-substitution): This reverses the 
chain rule. Look for a function and its derivative in the integrand. If you see 
f(g(x))·g'(x), substitute u=g(x), du=g'(x)dx to get ∫f(u)du. The key insight is 
recognizing patterns where one part is the derivative of another."""
        },
        {
            "category": "rule_intuition",
            "content": """Integration by Parts: ∫u·dv = u·v - ∫v·du. Use LIATE order 
(Logarithmic, Inverse trig, Algebraic, Trigonometric, Exponential) to choose u. 
This works because it converts a difficult integral into hopefully easier ones. 
Sometimes needs repeated application."""
        },
        {
            "category": "method_heuristic",
            "content": """Strategy for choosing integration method:
1. Check if it's a basic form (power, exponential, trig)
2. Try substitution if you see f(g(x))·g'(x) pattern
3. For products, consider integration by parts (LIATE)
4. For rational functions, use partial fractions
5. For trig products, use identities to simplify first
6. For square roots of quadratics, consider trig substitution"""
        },
        {
            "category": "pitfall",
            "content": """Common integration mistakes:
1. Forgetting the constant of integration (+C) for indefinite integrals
2. Incorrect u-substitution bounds (must change limits for definite integrals)
3. Not simplifying before integrating (makes problem harder)
4. Missing factors when substituting back
5. ∫1/x dx = ln|x| + C (absolute value crucial for negative x)"""
        },
        {
            "category": "engine_note",
            "content": """SymPy's integrate() returns unevaluated Integral objects when 
no closed-form antiderivative exists. It automatically includes common transformations 
but may not find the simplest form. For definite integrals, it handles improper 
integrals and may return symbolic expressions with special functions."""
        }
    ],
    "simplify": [
        {
            "category": "rule_intuition",
            "content": """Simplification involves reducing expressions to a canonical or 
minimal form. Key operations include: combining like terms, canceling common factors, 
applying algebraic identities (like a²-b² = (a+b)(a-b)), and rationalizing denominators. 
The 'simplest' form depends on context—sometimes expanded is cleaner, sometimes factored."""
        },
        {
            "category": "method_heuristic",
            "content": """Simplification strategies:
1. Factor out GCF (greatest common factor) first
2. Look for difference of squares, perfect squares/cubes
3. Combine fractions over common denominators
4. Cancel before multiplying in rational expressions
5. Use trig identities (sin²+cos²=1) for trig expressions
6. For complex expressions, work from inside out"""
        },
        {
            "category": "pitfall",
            "content": """Common simplification mistakes:
1. Canceling terms instead of factors: (x+y)/x ≠ y (wrong!)
2. Distributing exponents incorrectly: (a+b)² ≠ a²+b²
3. Forgetting domain restrictions when canceling (x-1)/(x-1)
4. Not fully factoring before canceling
5. Wrong sign when factoring negative terms
6. √(a²+b²) ≠ a+b"""
        },
        {
            "category": "engine_note",
            "content": """SymPy offers multiple simplification functions: simplify() for 
general purpose, expand() to distribute products, factor() to find polynomial factors, 
cancel() for rational functions, trigsimp() for trigonometric expressions. The simplify() 
function tries multiple strategies and returns the shortest result, but this may not 
always be the 'simplest' for your purpose."""
        }
    ],
    "solve": [
        {
            "category": "rule_intuition",
            "content": """Solving equations means finding values that make the equation true. 
For algebraic equations, we isolate the variable using inverse operations. For 
polynomial equations, factoring or the quadratic formula helps. The fundamental 
approach is to transform the equation while maintaining equality until the variable 
stands alone."""
        },
        {
            "category": "method_heuristic",
            "content": """Equation solving strategies:
1. Linear: isolate variable using inverse operations
2. Quadratic: factor, complete the square, or use quadratic formula
3. Higher polynomials: try rational root theorem, synthetic division
4. Exponential: take logs of both sides
5. Logarithmic: exponentiate both sides
6. Trigonometric: use identities to convert to single function, then solve
7. Systems: substitution, elimination, or matrix methods"""
        },
        {
            "category": "pitfall",
            "content": """Common solving mistakes:
1. Losing solutions when dividing by a variable (could be zero!)
2. Introducing extraneous solutions when squaring both sides
3. Forgetting periodic solutions in trig equations
4. Not checking solutions in original equation
5. Missing complex solutions for higher-degree polynomials
6. Domain restrictions (log, sqrt) that eliminate some solutions"""
        },
        {
            "category": "engine_note",
            "content": """SymPy's solve() function returns a list of solutions. For 
transcendental equations, it may return ImageSet or ConditionSet representing 
infinite solution sets. By default, it solves over complex numbers; use 
real=True for real solutions only. For systems, solveset() may be more robust 
than solve() in some cases."""
        }
    ]
}

