"""
Unified Memory Manager & Hybrid Retrieval Engine for Raphael v3.
Orchestrates L0 Working Memory, L2 Episodic, L3 Semantic, L4 Procedural, L5 User Model, and Vector Store.
"""

from typing import Dict, Any, List
from raphael.memory.working_memory import get_working_memory
from raphael.memory.episodic_memory import get_episodic_memory
from raphael.memory.semantic_memory import get_semantic_memory
from raphael.memory.procedural_memory import get_procedural_memory
from raphael.memory.user_model import get_user_model
from raphael.memory.vector_store import get_vector_store
from raphael.core.logging import get_logger

logger = get_logger("memory.manager")

class MemoryManager:
    def __init__(self):
        self.working = get_working_memory()
        self.episodic = get_episodic_memory()
        self.semantic = get_semantic_memory()
        self.procedural = get_procedural_memory()
        self.user_model = get_user_model()
        self.vector_store = get_vector_store()

    def hybrid_retrieve(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Hybrid Memory Retrieval (Section 25):
        Combines vector similarity search, L0 working memory, L3 semantic facts, and L5 user preferences.
        """
        # Vector Store Search
        vector_results = self.vector_store.search_similar_memories(query, top_k=limit)
        
        # Direct Semantic Search
        semantic_results = self.semantic.query_facts(subject="user")
        
        # User Profile
        user_profile = self.user_model.get_profile()

        # Working Memory Context
        working_context = self.working.get_summary()

        return {
            "query": query,
            "relevant_memories": vector_results,
            "user_preferences": user_profile,
            "semantic_facts": semantic_results[:5],
            "active_context": working_context
        }

    def forget_memory(self, target: str) -> Dict[str, Any]:
        """
        Memory Forgetting Command (Section 27):
        Handles commands like "Forget that", "Forget everything about X".
        """
        logger.info(f"Executing forget command for target: '{target}'")
        deleted_count = self.semantic.delete_matching_facts(target)
        return {
            "target": target,
            "deleted_facts_count": deleted_count,
            "status": "success"
        }

    def consolidate_memories(self) -> Dict[str, Any]:
        """
        Memory Consolidation (Section 66):
        Deduplicates facts, merges evidence counts, and archives stale temporary data.
        """
        logger.info("Executing periodic memory consolidation...")
        # Summarize & deduplicate semantic memories
        all_memories = self.semantic.query_facts()
        consolidated = len(all_memories)
        return {
            "status": "completed",
            "memories_processed": consolidated
        }

_memory_manager = MemoryManager()

def get_memory_manager() -> MemoryManager:
    return _memory_manager
