# string-analyzer-api

A RESTful API built with **FastAPI** that analyzes strings and stores their computed properties. Includes advanced filtering and natural language query support.

## 🚀 Features
- String analysis (length, palindrome, word count, hash, etc.)
- In-memory storage with SHA-256 identifiers
- Query filtering and natural language queries
- Auto-generated API docs (Swagger & ReDoc)
- Proper HTTP status codes and error handling

## 🧩 Installation

### Prerequisites
- Python 3.8+
- pip

### Setup
```bash
pip install -r requirements.txt
```

**requirements.txt**
```txt
fastapi==0.115.4
uvicorn[standard]==0.32.0
pydantic==2.9.2
```

## ▶️ Running the App
```bash
uvicorn main:app --reload
```
Server runs at **http://localhost:8000**

Docs:
- Swagger UI → [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc → [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🧠 API Endpoints

### 1. Create / Analyze String  
**POST** `/strings`  
Analyze and store a new string.

```json
{
  "value": "racecar"
}
```

### 2. Get String by Value  
**GET** `/strings/{string_value}`  
Retrieve details of an analyzed string.

### 3. List Strings with Filters  
**GET** `/strings`  
Filter with:
`is_palindrome`, `min_length`, `max_length`, `word_count`, `contains_character`

Example:
```
/strings?is_palindrome=true&min_length=5
```

### 4. Natural Language Filter  
**GET** `/strings/filter-by-natural-language?query=all palindromic strings`

Examples:
- “single word palindromic strings” → `word_count=1`, `is_palindrome=true`
- “longer than 10 characters” → `min_length=11`

### 5. Delete String  
**DELETE** `/strings/{string_value}`

---

## ⚙️ Other Endpoints
- **GET /** → API overview  
- **GET /health** → Health check and stored string count  

---

## 💡 Example Workflow
```bash
# Analyze strings
curl -X POST "http://localhost:8000/strings" -H "Content-Type: application/json" -d '{"value":"racecar"}'

# List all strings
curl "http://localhost:8000/strings"

# Filter palindromes
curl "http://localhost:8000/strings?is_palindrome=true"

# Natural language query
curl "http://localhost:8000/strings/filter-by-natural-language?query=palindromic strings"

# Delete
curl -X DELETE "http://localhost:8000/strings/racecar"
```

---

## 🧱 Notes
- Uses in-memory storage (data resets on restart)
- Ideal for local testing or learning FastAPI basics

## 📄 License
MIT License