from datetime import date
from rag import retrieve
 
 
def search_documents(query):
    """RAG tool: search the knowledge base."""
    rows = retrieve(query, k=4)
    return [
        {"content": r["content"], "source": r["source"], "page": r["page"]}
        for r in rows
    ]
 
 
def days_until(deadline):
    """Days left until a deadline given as YYYY-MM-DD."""
    try:
        d = date.fromisoformat(deadline)
    except ValueError:
        return {"error": "Date must be in YYYY-MM-DD format"}
    return {"days_left": (d - date.today()).days}
 
 
def cgpa_to_german_grade(cgpa, max_cgpa=10.0, min_pass=4.0):
    """Estimate German grade (1.0 best, 4.0 pass) with the modified
    Bavarian formula. Universities decide the official conversion."""
    grade = 1 + 3 * (max_cgpa - cgpa) / (max_cgpa - min_pass)
    return {
        "estimated_german_grade": round(grade, 2),
        "note": "Estimate only. The university makes the final conversion.",
    }
 
 
TOOLS = {
    "search_documents": search_documents,
    "days_until": days_until,
    "cgpa_to_german_grade": cgpa_to_german_grade,
}
