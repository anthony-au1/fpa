from app.rag.contracts import RetrievalQuery, RetrievalResponse, Retriever


async def retrieve_finance_documents(
    request: RetrievalQuery, retriever: Retriever
) -> RetrievalResponse:
    """Read-only evidence retrieval; returned text has no executable authority."""
    return await retriever.retrieve(request)
