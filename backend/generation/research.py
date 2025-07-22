import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from ..config.paths import get_cache_dir
from ..models.source import SourceItem
from ..models.content import ResearchDocument
from ..utils.file_utils import safe_write_json, safe_read_json
from ..utils.logging import get_logger
from ..providers import get_provider_adapter
from ..config import ConfigManager


class ResearchEngine:
    """Handles external research and context expansion"""
    
    def __init__(self):
        self.logger = get_logger("sourcerer.generation.research")
        self.cache_dir = get_cache_dir()
        self.config_manager = ConfigManager()
        
    async def conduct_research(self, 
                             item: SourceItem, 
                             research_queries: Optional[List[str]] = None) -> ResearchDocument:
        """Conduct research on a source item"""
        
        try:
            self.logger.info(f"Starting research for item: {item.title}")
            
            # Check for cached research
            cached_research = self._get_cached_research(item.id)
            if cached_research:
                self.logger.info(f"Using cached research for item {item.id}")
                return ResearchDocument(**cached_research)
            
            # Generate research queries if not provided
            if not research_queries:
                research_queries = await self._generate_research_queries(item)
            
            # Conduct external research (if enabled)
            research_results = []
            if self.config_manager.config.external_research.enabled:
                research_results = await self._conduct_external_research(research_queries)
            
            # Get related content from RAG
            rag_context = await self._get_rag_context(item)
            
            # Synthesize research summary
            research_summary = await self._synthesize_research(
                item=item,
                queries=research_queries,
                external_results=research_results,
                rag_context=rag_context
            )
            
            # Create research document
            research_doc = ResearchDocument(
                item_id=item.id,
                queries=research_queries,
                results=research_results + rag_context,
                summary=research_summary,
                created_at=datetime.now()
            )
            
            # Cache the research
            self._cache_research(research_doc)
            
            self.logger.info(f"Research completed for item {item.id}")
            return research_doc
            
        except Exception as e:
            self.logger.error(f"Failed to conduct research: {e}")
            # Return minimal research document
            return ResearchDocument(
                item_id=item.id,
                queries=research_queries or [],
                results=[],
                summary=f"Research failed: {str(e)}",
                created_at=datetime.now()
            )
    
    async def _generate_research_queries(self, item: SourceItem) -> List[str]:
        """Generate research queries using LLM"""
        
        try:
            if not self.config_manager.config.active_provider:
                self.logger.warning("No active provider for query generation")
                return self._generate_fallback_queries(item)
            
            # Get active provider
            provider_config = self.config_manager.config.providers[self.config_manager.config.active_provider]
            api_key = self.config_manager.get_provider_api_key(self.config_manager.config.active_provider)
            adapter = get_provider_adapter(self.config_manager.config.active_provider, provider_config, api_key)
            
            # Create prompt for query generation
            prompt = f"""Based on the following article, generate 2-3 specific research queries that would help gather additional context and insights. Focus on key concepts, related topics, and broader implications.

Title: {item.title}

Summary: {item.summary or 'No summary available'}

Content Preview: {(item.content or '')[:500]}...

Generate research queries in this format:
1. [First query]
2. [Second query]
3. [Third query]

Queries:"""

            # Generate queries
            messages = [{"role": "user", "content": prompt}]
            response = await adapter.chat(
                messages=messages,
                model=self.config_manager.config.active_model,
                params={"max_tokens": 200, "temperature": 0.7},
                stream=False
            )
            
            # Parse queries from response
            queries = self._parse_queries_from_response(response.content)
            
            if queries:
                self.logger.debug(f"Generated {len(queries)} research queries")
                return queries
            else:
                return self._generate_fallback_queries(item)
                
        except Exception as e:
            self.logger.error(f"Failed to generate research queries: {e}")
            return self._generate_fallback_queries(item)
    
    def _parse_queries_from_response(self, response: str) -> List[str]:
        """Parse research queries from LLM response"""
        queries = []
        
        for line in response.split('\n'):
            line = line.strip()
            
            # Look for numbered list items
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('*')):
                # Remove numbering and clean up
                query = line.split('.', 1)[-1].strip()
                query = query.lstrip('-*').strip()
                
                if query and len(query) > 10:  # Reasonable query length
                    queries.append(query)
        
        return queries[:3]  # Limit to 3 queries
    
    def _generate_fallback_queries(self, item: SourceItem) -> List[str]:
        """Generate simple fallback queries"""
        queries = []
        
        if item.title:
            # Extract key terms from title
            title_words = [word.strip() for word in item.title.split() if len(word) > 3]
            if title_words:
                queries.append(f"Latest developments in {' '.join(title_words[:3])}")
        
        # Add domain-specific query if available
        domain = item.raw.get('domain') if item.raw else None
        if domain:
            queries.append(f"Recent news from {domain}")
        
        # Add tag-based queries
        if item.tags:
            main_tag = item.tags[0]
            queries.append(f"Current trends in {main_tag}")
        
        return queries[:2] if queries else ["Related news and information"]
    
    async def _conduct_external_research(self, queries: List[str]) -> List[Dict[str, Any]]:
        """Conduct external web research (placeholder for future implementation)"""
        
        # This would integrate with search APIs like Tavily, SerpAPI, etc.
        # For now, return placeholder results
        
        self.logger.debug(f"External research not implemented, using placeholder for {len(queries)} queries")
        
        results = []
        for i, query in enumerate(queries):
            results.append({
                'query': query,
                'source': 'placeholder',
                'title': f"Research Result {i+1}",
                'snippet': f"This would contain search results for: {query}",
                'url': 'https://example.com',
                'timestamp': datetime.now().isoformat()
            })
        
        return results
    
    async def _get_rag_context(self, item: SourceItem) -> List[Dict[str, Any]]:
        """Get related content from RAG system"""
        
        try:
            from ..rag import RAGEngine
            
            rag_engine = RAGEngine()
            
            # Use item title and summary as search query
            search_query = f"{item.title} {item.summary or ''}"
            
            # Search for related content
            related_items = await rag_engine.search_similar_content(
                query=search_query,
                max_results=3,
                min_similarity=0.4
            )
            
            # Filter out the same item
            filtered_items = [r for r in related_items if r.get('item_id') != item.id]
            
            # Convert to research result format
            rag_results = []
            for related in filtered_items[:2]:  # Limit to 2 related items
                rag_results.append({
                    'query': 'Related content from sources',
                    'source': 'internal_rag',
                    'title': related.get('title', 'Related Article'),
                    'snippet': (related.get('summary') or related.get('content', ''))[:300],
                    'url': related.get('url', ''),
                    'similarity': related.get('similarity', 0.0),
                    'timestamp': related.get('published_at')
                })
            
            return rag_results
            
        except Exception as e:
            self.logger.error(f"Failed to get RAG context: {e}")
            return []
    
    async def _synthesize_research(self,
                                 item: SourceItem,
                                 queries: List[str],
                                 external_results: List[Dict[str, Any]],
                                 rag_context: List[Dict[str, Any]]) -> str:
        """Synthesize research findings into a summary"""
        
        try:
            if not self.config_manager.config.active_provider:
                return self._create_fallback_summary(item, queries, external_results, rag_context)
            
            # Get active provider
            provider_config = self.config_manager.config.providers[self.config_manager.config.active_provider]
            api_key = self.config_manager.get_provider_api_key(self.config_manager.config.active_provider)
            adapter = get_provider_adapter(self.config_manager.config.active_provider, provider_config, api_key)
            
            # Create synthesis prompt
            research_context = ""
            
            all_results = external_results + rag_context
            for i, result in enumerate(all_results[:5], 1):
                research_context += f"\nSource {i}: {result.get('title', 'Unknown')}\n"
                research_context += f"Content: {result.get('snippet', '')[:200]}...\n"
            
            prompt = f"""Synthesize the following research into a comprehensive summary that provides additional context and insights for the main article.

Main Article:
Title: {item.title}
Summary: {item.summary or 'No summary available'}

Research Queries:
{chr(10).join(f'- {q}' for q in queries)}

Research Results:
{research_context}

Create a coherent research summary that:
1. Highlights key additional context and background
2. Identifies relevant trends or developments  
3. Notes any conflicting or supporting information
4. Provides insights that enhance understanding of the main topic

Research Summary:"""

            # Generate synthesis
            messages = [{"role": "user", "content": prompt}]
            response = await adapter.chat(
                messages=messages,
                model=self.config_manager.config.active_model,
                params={"max_tokens": 500, "temperature": 0.7},
                stream=False
            )
            
            return response.content.strip()
            
        except Exception as e:
            self.logger.error(f"Failed to synthesize research: {e}")
            return self._create_fallback_summary(item, queries, external_results, rag_context)
    
    def _create_fallback_summary(self, 
                                item: SourceItem,
                                queries: List[str], 
                                external_results: List[Dict[str, Any]],
                                rag_context: List[Dict[str, Any]]) -> str:
        """Create a simple fallback research summary"""
        
        summary_parts = [
            f"Research conducted on: {item.title}",
            f"Research queries: {', '.join(queries)}"
        ]
        
        if external_results:
            summary_parts.append(f"Found {len(external_results)} external research results")
        
        if rag_context:
            summary_parts.append(f"Found {len(rag_context)} related internal sources")
        
        summary_parts.append("Additional context available from research sources.")
        
        return ". ".join(summary_parts)
    
    def _get_cached_research(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get cached research document"""
        try:
            cache_file = self.cache_dir / f"research_{item_id}.json"
            
            if cache_file.exists():
                cached_data = safe_read_json(cache_file)
                
                if cached_data:
                    # Check if cache is still fresh (24 hours)
                    created_at = datetime.fromisoformat(cached_data['created_at'])
                    age = datetime.now() - created_at
                    
                    if age.total_seconds() < 24 * 3600:  # 24 hours
                        return cached_data
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get cached research: {e}")
            return None
    
    def _cache_research(self, research_doc: ResearchDocument):
        """Cache research document"""
        try:
            cache_file = self.cache_dir / f"research_{research_doc.item_id}.json"
            safe_write_json(research_doc.model_dump(), cache_file)
            
            self.logger.debug(f"Cached research for item {research_doc.item_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to cache research: {e}")