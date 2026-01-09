"""
LLM Explanation Generator.

Generates step-by-step explanations grounded in:
- The original user query
- The structured routing decision
- The symbolic engine output
- Retrieved knowledge chunks

The LLM is explicitly instructed NOT to compute new math—only to explain.
Supports both regular and streaming responses.
"""
from typing import Optional, List, Generator
from openai import OpenAI
from langfuse import observe
from langfuse.openai import openai  # LangFuse-wrapped OpenAI for token tracking
from .models import ExplanationContext, RetrievedChunk


EXPLAINER_SYSTEM_PROMPT = """You are a math tutor explaining a calculation that has ALREADY been performed.

CRITICAL RULES:
1. The mathematical answer has ALREADY been computed by SymPy and is AUTHORITATIVE
2. You must NOT compute any new math—the answer provided is CORRECT
3. Your job is ONLY to explain HOW and WHY this answer is correct
4. Reference the retrieved knowledge when relevant
5. Highlight any assumptions that were made
6. Point out edge cases or potential pitfalls

Your explanation should:
- Break down the problem-solving approach step by step
- Explain which mathematical rules/techniques were applied
- Help the user understand the intuition behind each step
- Be clear, educational, and appropriately detailed

Format your response as a clear step-by-step explanation using numbered steps.
Use LaTeX notation (wrapped in $...$ for inline or $$...$$ for display) for mathematical expressions.
"""


class MathExplainer:
    """
    LLM-based explanation generator.
    Explains SymPy results without computing new math.
    """
    
    def __init__(
        self,
        client: Optional[OpenAI] = None,
        model: str = "gpt-4o"
    ):
        # Use LangFuse-wrapped client for automatic token tracking
        self.client = openai.OpenAI()
        self.model = model
    
    def _format_context(self, context: ExplanationContext) -> str:
        """Format the context for the LLM prompt."""
        routing = context.routing_decision
        compute = context.compute_result
        chunks = context.retrieved_chunks
        
        context_parts = [
            "## Original Query",
            f'"{context.original_query}"',
            "",
            "## Operation Performed",
            f"- Operation: {routing.operation}",
            f"- Expression: {routing.expression}",
            f"- Variable: {routing.variable}",
        ]
        
        if routing.assumptions:
            context_parts.append(f"- Assumptions: {', '.join(routing.assumptions)}")
        
        context_parts.extend([
            "",
            "## Computed Result (AUTHORITATIVE - from SymPy)",
            f"- Answer: {compute.result}",
            f"- LaTeX: {compute.latex_result}",
        ])
        
        if compute.intermediate_steps:
            context_parts.append("- Computation steps:")
            for step in compute.intermediate_steps:
                context_parts.append(f"  • {step}")
        
        if chunks:
            context_parts.extend([
                "",
                "## Retrieved Knowledge (use these to explain)",
            ])
            for i, chunk in enumerate(chunks, 1):
                context_parts.extend([
                    f"### [{chunk.category}] (relevance: {chunk.relevance_score:.2f})",
                    chunk.content,
                    ""
                ])
        
        return "\n".join(context_parts)
    
    def _format_citations(self, chunks: List[RetrievedChunk]) -> List[str]:
        """Format citations from retrieved chunks."""
        return [
            f"[{chunk.chunk_id}] {chunk.category}: {chunk.source or 'Knowledge Base'}"
            for chunk in chunks
            if chunk.relevance_score > 0.5
        ]
    
    @observe(name="llm_explanation")
    def explain(self, context: ExplanationContext) -> str:
        """
        Generate an explanation for the computed result.
        
        Args:
            context: ExplanationContext with query, routing, compute result, and retrieved chunks
            
        Returns:
            A step-by-step explanation string
        """
        formatted_context = self._format_context(context)
        
        user_prompt = f"""Based on the following information, provide a clear step-by-step explanation.
Remember: The answer is already computed and correct. Your job is to EXPLAIN it.

{formatted_context}

Please explain:
1. What mathematical operation was needed and why
2. The step-by-step process to arrive at this answer
3. Any important rules or techniques used
4. Potential edge cases or things to watch out for
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": EXPLAINER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1024
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            # Fallback: return a basic explanation using intermediate steps
            return self._fallback_explanation(context)
    
    def _fallback_explanation(self, context: ExplanationContext) -> str:
        """Generate a basic explanation if LLM fails."""
        routing = context.routing_decision
        compute = context.compute_result
        
        steps = []
        steps.append(f"**Operation:** {routing.operation.capitalize()}")
        steps.append(f"**Expression:** ${routing.expression}$")
        
        if routing.operation == "differentiate":
            steps.append(f"\nTo find the derivative with respect to ${routing.variable}$:")
        elif routing.operation == "integrate":
            steps.append(f"\nTo find the integral with respect to ${routing.variable}$:")
        elif routing.operation == "simplify":
            steps.append(f"\nTo simplify this expression:")
        elif routing.operation == "solve":
            steps.append(f"\nTo solve for ${routing.solve_for or routing.variable}$:")
        
        if compute.intermediate_steps:
            steps.append("\n**Steps:**")
            for i, step in enumerate(compute.intermediate_steps, 1):
                steps.append(f"{i}. {step}")
        
        steps.append(f"\n**Final Answer:** ${compute.latex_result}$")
        
        if routing.assumptions:
            steps.append(f"\n**Assumptions:** {', '.join(routing.assumptions)}")
        
        return "\n".join(steps)
    
    def explain_stream(self, context: ExplanationContext) -> Generator[str, None, None]:
        """
        Generate an explanation as a stream of tokens.
        
        Args:
            context: ExplanationContext with query, routing, compute result, and retrieved chunks
            
        Yields:
            Tokens of the explanation as they're generated
        """
        formatted_context = self._format_context(context)
        
        user_prompt = f"""Based on the following information, provide a clear step-by-step explanation.
Remember: The answer is already computed and correct. Your job is to EXPLAIN it.

{formatted_context}

Please explain:
1. What mathematical operation was needed and why
2. The step-by-step process to arrive at this answer
3. Any important rules or techniques used
4. Potential edge cases or things to watch out for
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": EXPLAINER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1024,
                stream=True
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            # Fallback: yield the basic explanation
            yield self._fallback_explanation(context)

