from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
import json
from typing import Dict, Optional, List
from datetime import datetime
import hashlib
from collections import Counter
import re

# Custom JSON Response with pretty printing
class PrettyJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
            separators=(", ", ": "),
        ).encode("utf-8")

app = FastAPI(title="String Analyzer API",
              version="1.0.0",
              description="String Analyzer API for analyzing strings and storing their computed properties",
              default_response_class=PrettyJSONResponse  # Pretty JSON by default
             )

# In-memory storage (using SHA256 hash as key)
string_store: Dict[str, dict] = {}

# Pydantic models for request/response validation
class StringInput(BaseModel):
    value: str = Field(..., description="String to analyze")

class StringProperties(BaseModel):
    length: int
    is_palindrome: bool
    unique_characters: int
    word_count: int
    sha256_hash: str
    character_frequency_map: Dict[str, int]

class StringResponse(BaseModel):
    id: str
    value: str
    properties: StringProperties
    created_at: str

class FilteredResponse(BaseModel):
    data: List[StringResponse]
    count: int
    filters_applied: Dict

class NaturalLanguageResponse(BaseModel):
    data: List[StringResponse]
    count: int
    interpreted_query: Dict

# Helper function to compute string properties
def analyze_string(value: str) -> StringProperties:
    """Compute all properties for a given string."""
    # Compute SHA-256 hash
    sha256_hash = hashlib.sha256(value.encode()).hexdigest()
    
    # Check if palindrome (case-insensitive)
    normalized = value.lower()
    is_palindrome = normalized == normalized[::-1]
    
    # Count unique characters
    unique_characters = len(set(value))
    
    # Count words (split by whitespace)
    word_count = len(value.split())
    
    # Character frequency map
    character_frequency_map = dict(Counter(value))
    
    return StringProperties(
        length=len(value),
        is_palindrome=is_palindrome,
        unique_characters=unique_characters,
        word_count=word_count,
        sha256_hash=sha256_hash,
        character_frequency_map=character_frequency_map
    )

def apply_filters(strings: List[dict], filters: dict) -> List[dict]:
    """Apply filtering logic to a list of strings."""
    filtered = strings
    
    # Filter by is_palindrome
    if filters.get("is_palindrome") is not None:
        filtered = [s for s in filtered if s["properties"]["is_palindrome"] == filters["is_palindrome"]]
    
    # Filter by min_length
    if filters.get("min_length") is not None:
        filtered = [s for s in filtered if s["properties"]["length"] >= filters["min_length"]]
    
    # Filter by max_length
    if filters.get("max_length") is not None:
        filtered = [s for s in filtered if s["properties"]["length"] <= filters["max_length"]]
    
    # Filter by word_count
    if filters.get("word_count") is not None:
        filtered = [s for s in filtered if s["properties"]["word_count"] == filters["word_count"]]
    
    # Filter by contains_character
    if filters.get("contains_character"):
        char = filters["contains_character"]
        filtered = [s for s in filtered if char in s["value"]]
    
    return filtered

def parse_natural_language_query(query: str) -> dict:
    """
    Parse natural language queries into filter parameters.
    
    Supports patterns like:
    - "single word" / "one word" → word_count=1
    - "palindromic" / "palindrome" → is_palindrome=true
    - "longer than X" → min_length=X+1
    - "shorter than X" → max_length=X-1
    - "at least X characters" → min_length=X
    - "contains letter X" / "containing X" → contains_character=X
    """
    query_lower = query.lower()
    filters = {}
    
    # Palindrome detection
    if "palindrom" in query_lower:
        filters["is_palindrome"] = True
    
    # Word count detection
    if "single word" in query_lower or "one word" in query_lower:
        filters["word_count"] = 1
    elif "two word" in query_lower:
        filters["word_count"] = 2
    elif "three word" in query_lower:
        filters["word_count"] = 3
    
    # Length filters
    longer_match = re.search(r"longer than (\d+)", query_lower)
    if longer_match:
        filters["min_length"] = int(longer_match.group(1)) + 1
    
    shorter_match = re.search(r"shorter than (\d+)", query_lower)
    if shorter_match:
        filters["max_length"] = int(shorter_match.group(1)) - 1
    
    at_least_match = re.search(r"at least (\d+) characters?", query_lower)
    if at_least_match:
        filters["min_length"] = int(at_least_match.group(1))
    
    at_most_match = re.search(r"at most (\d+) characters?", query_lower)
    if at_most_match:
        filters["max_length"] = int(at_most_match.group(1))
    
    exactly_match = re.search(r"exactly (\d+) characters?", query_lower)
    if exactly_match:
        length = int(exactly_match.group(1))
        filters["min_length"] = length
        filters["max_length"] = length
    
    # Character containment
    contains_match = re.search(r"contain(?:s|ing)? (?:the )?(?:letter |character )?['\"]?([a-z])['\"]?", query_lower)
    if contains_match:
        filters["contains_character"] = contains_match.group(1)
    
    # Special case for "first vowel"
    if "first vowel" in query_lower:
        filters["contains_character"] = "a"
    
    # Validate for conflicting filters
    if "min_length" in filters and "max_length" in filters:
        if filters["min_length"] > filters["max_length"]:
            raise ValueError("Conflicting filters: min_length cannot be greater than max_length")
    
    if not filters:
        raise ValueError("Unable to parse natural language query")
    
    return filters

@app.post("/strings", response_model=StringResponse, status_code=status.HTTP_201_CREATED)
async def create_string(string_input: StringInput):
    """
    Analyze and store a new string.
    
    Returns the analyzed string with computed properties.
    Raises 409 Conflict if the string already exists.
    """
    value = string_input.value
    
    # Compute properties
    properties = analyze_string(value)
    string_id = properties.sha256_hash
    
    # Check if string already exists
    if string_id in string_store:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="String already exists in the system"
        )
    
    # Create timestamp
    created_at = datetime.utcnow().isoformat() + "Z"
    
    # Store the string data
    string_data = {
        "id": string_id,
        "value": value,
        "properties": properties.dict(),
        "created_at": created_at
    }
    string_store[string_id] = string_data
    
    return StringResponse(**string_data)

@app.get("/strings/{string_value}", response_model=StringResponse)
async def get_string(string_value: str):
    """
    Retrieve a previously analyzed string by its value.
    
    Returns 404 if the string has not been analyzed before.
    """
    # Compute the hash of the requested string to look it up
    string_id = hashlib.sha256(string_value.encode()).hexdigest()
    
    # Check if string exists in storage
    if string_id not in string_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="String not found in the system"
        )
    
    return StringResponse(**string_store[string_id])

@app.get("/strings", response_model=FilteredResponse)
async def list_strings_with_filters(
    is_palindrome: Optional[bool] = Query(None, description="Filter by palindrome status"),
    min_length: Optional[int] = Query(None, ge=0, description="Minimum string length"),
    max_length: Optional[int] = Query(None, ge=0, description="Maximum string length"),
    word_count: Optional[int] = Query(None, ge=0, description="Exact word count"),
    contains_character: Optional[str] = Query(None, min_length=1, max_length=1, description="Single character to search for")
):
    """
    List all analyzed strings with optional filtering.
    
    Query parameters:
    - is_palindrome: Filter by palindrome status (true/false)
    - min_length: Minimum string length
    - max_length: Maximum string length
    - word_count: Exact word count
    - contains_character: Single character that must be present
    """
    # Validate filter combinations
    if min_length is not None and max_length is not None:
        if min_length > max_length:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="min_length cannot be greater than max_length"
            )
    
    # Build filters dict
    filters = {}
    if is_palindrome is not None:
        filters["is_palindrome"] = is_palindrome
    if min_length is not None:
        filters["min_length"] = min_length
    if max_length is not None:
        filters["max_length"] = max_length
    if word_count is not None:
        filters["word_count"] = word_count
    if contains_character is not None:
        filters["contains_character"] = contains_character
    
    # Get all strings and apply filters
    all_strings = list(string_store.values())
    filtered_strings = apply_filters(all_strings, filters)
    
    return FilteredResponse(
        data=[StringResponse(**s) for s in filtered_strings],
        count=len(filtered_strings),
        filters_applied=filters
    )

@app.get("/strings/filter-by-natural-language", response_model=NaturalLanguageResponse)
async def filter_by_natural_language(
    query: str = Query(..., description="Natural language query to filter strings")
):
    """
    Filter strings using natural language queries.
    
    Example queries:
    - "all single word palindromic strings"
    - "strings longer than 10 characters"
    - "palindromic strings that contain the first vowel"
    - "strings containing the letter z"
    """
    try:
        # Parse the natural language query
        filters = parse_natural_language_query(query)
    except ValueError as e:
        if "conflicting" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unable to parse natural language query: {str(e)}"
            )
    
    # Apply filters
    all_strings = list(string_store.values())
    filtered_strings = apply_filters(all_strings, filters)
    
    return NaturalLanguageResponse(
        data=[StringResponse(**s) for s in filtered_strings],
        count=len(filtered_strings),
        interpreted_query={
            "original": query,
            "parsed_filters": filters
        }
    )

@app.delete("/strings/{string_value}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_string(string_value: str):
    """
    Delete a string from the system.
    
    Returns 404 if the string doesn't exist.
    """
    string_id = hashlib.sha256(string_value.encode()).hexdigest()
    
    if string_id not in string_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="String not found in the system"
        )
    
    del string_store[string_id]
    return None

# Root endpoint
@app.get("/")
async def root():
    """API information endpoint."""
    return {
        "name": "String Analysis API",
        "version": "1.0.0",
        "endpoints": {
            "POST /strings": "Analyze and store a new string",
            "GET /strings/{string_value}": "Retrieve analyzed string by value",
            "GET /strings": "List and filter all analyzed strings",
            "GET /strings/filter-by-natural-language": "Filter strings using natural language",
            "DELETE /strings/{string_value}": "Delete a string from storage"
        }
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "stored_strings": len(string_store)
    }


if __name__ == "__main__":
    print("Starting FastAPI app...")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
