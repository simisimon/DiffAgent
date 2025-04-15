from duckduckgo_search import DDGS
from llama_index.readers.web import SimpleWebPageReader
from llama_index.core.node_parser import SentenceSplitter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List
import httpx

def get_information_from_web(query: str, num_websites: int = 5) -> str:
    """
    Use this function to crawl the web for further information.

    Args:
        query (str): The search query to use.
        num_websites (int): Number of websites to crawl.

    Returns:
        str: JSON string of top stories.
    """
    context = []
    urls = []
    results = DDGS().text(query, max_results=num_websites)
    for result in results:
        url = result["href"]
        urls.append(url)

    
    documents = SimpleWebPageReader(html_to_text=True).load_data(urls)
    splitter = SentenceSplitter(
        chunk_size=256,
        chunk_overlap=10,
    )

    nodes = splitter.get_nodes_from_documents(documents)
    
    node_texts = [node.get_content() for node in nodes]
    
    all_texts = [query] + node_texts

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(all_texts)
    
    # Calculate cosine similarity between query and nodes
    query_vector = tfidf_matrix[0]  # First vector corresponds to the query
    node_vectors = tfidf_matrix[1:]  # Remaining vectors correspond to nodes
    similarities = cosine_similarity(query_vector, node_vectors).flatten()
    
    # Pair nodes with their similarity scores
    similar_nodes = [
        {"text": text, "similarity": similarity}
        for text, similarity in zip(node_texts, similarities)
    ]
    
    # Sort nodes by similarity in descending order
    similar_nodes = sorted(similar_nodes, key=lambda x: x["similarity"], reverse=True)
    
    # Combine the three most similar texts into one string
    top_texts = [node["text"] for node in similar_nodes[:3]]
    combined_text = "\n\n".join(top_texts)
    
    return combined_text

