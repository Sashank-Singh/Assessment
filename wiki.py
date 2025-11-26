import wikipedia # https://wikipedia.readthedocs.io/en/latest/code.html#api
import json
import sqlite3
import spacy
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Optional
import warnings
import time

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Load spacy model once at module level
nlp = spacy.load("en_core_web_sm")

# create the database if it doesn't exist
conn = sqlite3.connect("pages.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS pages (name TEXT, links TEXT)")
conn.commit()

# Global hard mode flag
_hard_mode = False

def set_hard_mode(enabled: bool):
    """Enable or disable hard mode (links only, no categories)
    
    Args:
        enabled: True to enable hard mode, False for normal mode
    """
    global _hard_mode
    _hard_mode = enabled

def encode_text(text):
    """Encode text using spacy's sentence vectors"""
    doc = nlp(text)
    return doc.vector.reshape(1, -1)

def get_page(page_name: str):
    """Get a specific Wikipedia page by name
    
    Args:
        page_name: The name of the Wikipedia page to fetch
        
    Returns:
        A Wikipedia page object, or None if not found
    """
    try:
        return wikipedia.page(page_name, auto_suggest=False, redirect=False)
    except:
        pass
    try:
        search_results = wikipedia.search(page_name, results=3)
        if not search_results:
            return None
        # Try first few results instead of defaulting to Python
        for choice in search_results:
            try:
                page = wikipedia.page(choice, auto_suggest=False, redirect=False)
                return page
            except:
                continue
        return None
    except:
        return None

def get_page_links_with_cache(page_name: str) -> List[str]:
    """Get links from a Wikipedia page with caching
    
    In hard mode, only returns direct links (no categories).
    In normal mode, returns both links and categories.
    
    Args:
        page_name: The name of the Wikipedia page
        
    Returns:
        List of page names linked from this page
    """
    conn = sqlite3.connect("pages.db")
    cursor = conn.cursor()
    cached_page = cursor.execute("SELECT * FROM pages WHERE name = ?", (page_name,)).fetchone()

    if not cached_page:
        page = get_page(page_name)
        if not page:
            return []
        links = page.links
        categories = page.categories if not _hard_mode else []
        cursor.execute("INSERT INTO pages (name, links) VALUES (?, ?)", (page_name, json.dumps(links + categories)))
        conn.commit()
        cached_page = cursor.execute("SELECT * FROM pages WHERE name = ?", (page_name,)).fetchone()

    all_links = json.loads(cached_page[1])
    
    # In hard mode, filter out category links from cached data too
    if _hard_mode:
        all_links = [link for link in all_links if not link.startswith("Category:")]
    
    filtered = [link for link in all_links if is_regular_page(link)]
    if page_name in filtered:
        filtered.remove(page_name)
    return filtered

def is_regular_page(page_name: str) -> bool:
    """Filter out meta pages and disambiguation pages
    
    Args:
        page_name: The name of the Wikipedia page
        
    Returns:
        True if this is a regular content page, False otherwise
    """
    page_lower = page_name.lower()
    # Filter out meta pages
    meta_keywords = [
        "disambiguation", "automatic", "article", "identifier",
        "wikidata", "short description", "use dmy dates", "use mdy dates",
        "articles with", "all articles", "pages with", "wikipedia articles"
    ]
    return not any(keyword in page_lower for keyword in meta_keywords)

def _find_short_path(start_path: List[str], end_path: List[str], max_depth: int = 15, 
                     start_time: float = None, timeout: float = 10.0) -> Optional[List[str]]:
    """Find a short path between two Wikipedia pages using bidirectional search
    
    Uses cosine similarity of sentence embeddings to score potential links
    and hill-climbs from both ends towards each other.
    
    Args:
        start_path: Current path from the start page
        end_path: Current path to the end page (in reverse)
        max_depth: Maximum total path length before giving up
        start_time: Timestamp when search started (for timeout)
        timeout: Maximum seconds to search before giving up
        
    Returns:
        List of page titles forming a path, or None if no path found
    """
    # Initialize start time on first call
    if start_time is None:
        start_time = time.time()
    
    # Check timeout
    if time.time() - start_time > timeout:
        print(f"⏱️  Search timed out after {timeout} seconds")
        return None
    
    start_leaf = start_path[-1]
    end_leaf = end_path[0]

    # Base cases: we've reached the end or exceeded max depth
    if len(start_path) + len(end_path) > max_depth:
        return None

    if start_leaf == end_leaf:
        return start_path + end_path[1:]
    
    links = get_page_links_with_cache(start_leaf)
    if end_leaf in links:
        return start_path + end_path
    
    backlinks = get_page_links_with_cache(end_leaf)
    if start_leaf in backlinks:
        return start_path + end_path
    
    # Check for intersection - quick win
    intersection = list(set(links) & set(backlinks))
    if len(intersection) > 0:
        return start_path + [intersection[0]] + end_path
    
    print(f"{start_path[-1]} ➜ {end_path[0]}")

    # Limit search to top candidates for performance
    if not links or not backlinks:
        return None

    # Recursively search inwards using semantic similarity
    end_leaf_page = get_page(end_leaf)
    if not end_leaf_page:
        return None
    
    end_embedding = encode_text(end_leaf_page.summary)
    scored_links = [(link, cosine_similarity(encode_text(link), end_embedding)[0][0]) 
                    for link in links[:50]]  # Limit to top 50 for performance
    scored_links.sort(key=lambda x: x[1], reverse=True)
    
    if not scored_links:
        return None
    next_page = scored_links[0][0]

    start_leaf_page = get_page(start_leaf)
    if not start_leaf_page:
        return None
        
    start_embedding = encode_text(start_leaf_page.summary)
    scored_backlinks = [(backlink, cosine_similarity(encode_text(backlink), start_embedding)[0][0]) 
                        for backlink in backlinks[:50]]  # Limit to top 50 for performance
    scored_backlinks.sort(key=lambda x: x[1], reverse=True)
    
    if not scored_backlinks:
        return None
    previous_page = scored_backlinks[0][0]

    return _find_short_path(start_path + [next_page], [previous_page] + end_path, max_depth, start_time, timeout)


def find_short_path(start_page, end_page) -> Optional[List[str]]:
    """Find a short path between two Wikipedia pages
    
    Args:
        start_page: Wikipedia page object to start from
        end_page: Wikipedia page object to reach
        
    Returns:
        List of page titles forming a path, or empty list if no path found
    """
    if not start_page or not end_page:
        return []
        
    start_path = [start_page.title]
    end_path = [end_page.title]

    result = _find_short_path(start_path, end_path)
    return result if result else []
