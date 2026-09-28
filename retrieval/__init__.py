"""Framework-neutral retrieval utilities for FaithfulMed."""

from .chroma_retriever import RetrievedChunk, retrieve_context

__all__ = ["RetrievedChunk", "retrieve_context"]