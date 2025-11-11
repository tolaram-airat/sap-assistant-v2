import sqlite3
import re
from fuzzywuzzy import fuzz
import os
import json

# Database path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "errors.db")

# Cache for normalized issuename values
ERROR_CACHE = None

def load_error_cache():
    """Load and cache normalized issuename values from database."""
    global ERROR_CACHE
    if ERROR_CACHE is None:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id, issuename FROM errors")
            errors = cursor.fetchall()
            ERROR_CACHE = [
                {"id": error_id, "normalized_issuename": issuename.lower().replace('xxxx', '').replace('yyyy', '')}
                for error_id, issuename in errors
            ]
            conn.close()
            print(f"Cached {len(ERROR_CACHE)} error issuenames")
        except sqlite3.OperationalError as e:
            print(f"Cannot load cache: {e}")
            ERROR_CACHE = []

def extract_error_phrase(user_input):
    """Extract the most relevant error-related phrase from user input."""
    print(f"Extracting phrase from: {user_input}")
    user_input = user_input.lower()
    error_keywords = ['error', 'issue', 'problem', 'not found', 'does not exist', 'blocked', 'missing', 'failed', 'not in']
    fluff_phrases = [r'^\s*hey\s*[,!\.]?', r'what do i do\s*[\?\.]?$', r'i got the error\s*', r'i\'m getting an?\s*']
    
    cleaned_input = user_input
    for fluff in fluff_phrases:
        cleaned_input = re.sub(fluff, '', cleaned_input, flags=re.IGNORECASE)
    cleaned_input = cleaned_input.strip()
    
    sentences = re.split(r'[.!?]+', cleaned_input)
    best_phrase = cleaned_input
    min_length = float('inf')
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if any(keyword in sentence for keyword in error_keywords) or re.search(r'\b\w+\s+(?:does not exist|is not|not in|blocked|missing)\b', sentence):
            if len(sentence.split()) < min_length:
                min_length = len(sentence.split())
                best_phrase = sentence
    print(f"Extracted phrase: {best_phrase}")
    return best_phrase

def retrieve_errors(user_input, company_code=None, profit_center=None, threshold=65):
    """Retrieve matching errors from the database based on user_input."""
    print(f"Retrieving errors for input: {user_input}, company_code: {company_code}, profit_center: {profit_center}")
    load_error_cache()
    
    try:
        conn = sqlite3.connect(DB_PATH)
    except sqlite3.OperationalError as e:
        print(f"Cannot open database: {e}")
        return [{
            "id": None,
            "module": "Unknown",
            "issuename": "Database error",
            "issuedescription": user_input,
            "solution": "Sorry, unable to open database file. Please check if data/errors.db exists.",
            "solutiontype": "consult",  # CHANGED: Added explicit solutiontype for consistency
            "logcategory": None,
            "logsubcategory": None,
            "notes": None,
            "score": 0
        }]
    cursor = conn.cursor()

    input_keywords = set(user_input.lower().split()) & set(['material', 'plant', 'vendor', 'company', 'code', 'bank', 'details', 'missing', 'not', 'in'])
    
    query = "SELECT id, module, issuename, issuedescription, solutiontype, stepbystep, logcategory, logsubcategory, notes FROM errors"
    params = []
    
    if input_keywords:
        keyword_conditions = " OR ".join([f"issuename LIKE ?" for _ in input_keywords])
        query += f" WHERE {keyword_conditions}"
        params.extend([f"%{keyword}%" for keyword in input_keywords])
    
    if company_code or profit_center:
        if input_keywords:
            query += " AND "
        else:
            query += " WHERE "
        query += """
        id IN (
            SELECT e.id
            FROM errors e
            LEFT JOIN mappings m ON e.logcategory = m.logcategory OR e.logsubcategory = m.logsubcategory
            WHERE (m.type = 'company' AND m.code = ?) OR (m.type = 'profit_center' AND m.code = ?)
        )
        """
        params.extend([company_code or '', profit_center or ''])

    try:
        cursor.execute(query, params)
        errors = cursor.fetchall()
    except sqlite3.OperationalError as e:
        print(f"Error executing query: {e}")
        conn.close()
        return [{
            "id": None,
            "module": "Unknown",
            "issuename": "Database error",
            "issuedescription": user_input,
            "solution": " ",
            "solutiontype": "consult",
            "logcategory": None,
            "logsubcategory": None,
            "notes": None,
            "score": 0
        }]

    matches = []
    error_phrase_normalized = user_input.lower().replace('xxxx', '').replace('yyyy', '')
    for error in errors:
        error_id, module, issuename, issuedescription, solutiontype, stepbystep, logcategory, logsubcategory, notes = error
        cached_entry = next((e for e in ERROR_CACHE if e["id"] == error_id), None)
        if not cached_entry:
            continue
        match_text = cached_entry["normalized_issuename"]
        score = max(
            fuzz.partial_ratio(error_phrase_normalized, match_text),
            fuzz.token_sort_ratio(error_phrase_normalized, match_text),
            fuzz.token_set_ratio(error_phrase_normalized, match_text)
        )
        if score >= threshold:
            matches.append({
                "id": error_id,
                "module": module or "Unknown",  # CHANGED: Added default to avoid None
                "issuename": issuename or "Unknown Issue",  # CHANGED: Added default
                "issuedescription": issuedescription or user_input,  # CHANGED: Added default
                "solution": stepbystep or "No solution provided",  # CHANGED: Added default
                "solutiontype": solutiontype or "consult",  # CHANGED: Added default
                "logcategory": logcategory,
                "logsubcategory": logsubcategory,
                "notes": notes,
                "score": score
            })

    if not matches:
        print("Debug: No matches found, returning default response")  # CHANGED: Added debug log
        matches = [{
            "id": None,
            "module": "Unknown",
            "issuename": "No matching error found",
            "issuedescription": user_input,
            "solution": "Sorry, no match found, I'm still learning",
            "solutiontype": "consult",  # CHANGED: Added explicit solutiontype
            "logcategory": None,
            "logsubcategory": None,
            "notes": None,
            "score": 0
        }]

    # Sort matches by score in descending order and take top 3
    matches.sort(key=lambda x: x["score"], reverse=True)
    top_matches = matches[:3]
    for match in top_matches:
        print(f"Match (Score: {match['score']}):")
        print(f"Module: {match.get('module', 'Unknown')}")  # CHANGED: Safe key access
        print(f"Issue: {match.get('issuename', 'Unknown Issue')}")  # CHANGED: Safe key access
        print(f"Description: {match.get('issuedescription', user_input)}")  # CHANGED: Safe key access
        print(f"Solution: {match.get('solution', 'No solution provided')}")  # CHANGED: Safe key access
        print(f"Solutiontype: {match.get('solutiontype', 'consult')}")  # CHANGED: Safe key access (fixes KeyError)
        print(f"Notes: {match.get('notes', 'None')}")  # CHANGED: Safe key access
    conn.close()  # CHANGED: Ensure connection is closed
    return top_matches

if __name__ == "__main__":
    # Simple test function for standalone execution
    test_input = "Material XXXX does not exist in sales org"
    print(f"\nTesting input: {test_input}")
    matches = retrieve_errors(test_input)
    for match in matches:
        print(f"Match (Score: {match['score']}):")
        print(f"Module: {match.get('module', 'Unknown')}")  # CHANGED: Safe key access
        print(f"Issue: {match.get('issuename', 'Unknown Issue')}")  # CHANGED: Safe key access
        print(f"Description: {match.get('issuedescription', test_input)}")  # CHANGED: Safe key access
        print(f"Solution: {match.get('solution', 'No solution provided')}")  # CHANGED: Safe key access
        print(f"Notes: {match.get('notes', 'None')}\n")  # CHANGED: Safe key access