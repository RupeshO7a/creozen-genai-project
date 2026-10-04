from datetime import date
from google.genai import types
from llm import client, CHAT_MODEL
from tools import TOOLS
 
SYSTEM = (
    "You are an admissions assistant for international students applying "
    "to German Master's programs. Rules: "
    "1) For any factual question about programs, requirements or "
    "deadlines, ALWAYS call search_documents first. "
    "2) Answer ONLY from the retrieved text. If the answer is not there, "
    "say you could not find it in the documents. "
    "3) For questions about days left, use days_until. "
    "4) For grade conversion, use cgpa_to_german_grade and say it is an "
    "estimate. "
    "5) Mention the source file name and page for facts you use. "
    "Today's date is {today}."
)
 
S = types.Schema
declarations = [
    types.FunctionDeclaration(
        name="search_documents",
        description="Search the university documents for relevant text.",
        parameters=S(
            type="OBJECT",
            properties={"query": S(type="STRING", description="Search query")},
            required=["query"],
        ),
    ),
    types.FunctionDeclaration(
        name="days_until",
        description="Number of days from today until a deadline date.",
        parameters=S(
            type="OBJECT",
            properties={
                "deadline": S(type="STRING", description="Date as YYYY-MM-DD")
            },
            required=["deadline"],
        ),
    ),
    types.FunctionDeclaration(
        name="cgpa_to_german_grade",
        description="Estimate the German grade equivalent of a CGPA.",
        parameters=S(
            type="OBJECT",
            properties={
                "cgpa": S(type="NUMBER", description="Student CGPA"),
                "max_cgpa": S(type="NUMBER", description="Maximum, default 10"),
            },
            required=["cgpa"],
        ),
    ),
]
 
 
def run_agent(question, history, max_steps=5):
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM.format(today=date.today().isoformat()),
        tools=[types.Tool(function_declarations=declarations)],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            disable=True
        ),
    )
 
    contents = []
    for m in history:  # memory: previous messages of this session
        role = "model" if m["role"] == "assistant" else "user"
        contents.append(
            types.Content(role=role, parts=[types.Part(text=m["content"])])
        )
    contents.append(
        types.Content(role="user", parts=[types.Part(text=question)])
    )
 
    sources, steps, seen = [], [], set()
 
    for _ in range(max_steps):
        response = client.models.generate_content(
            model=CHAT_MODEL, contents=contents, config=config
        )
        message = response.candidates[0].content
        calls = [p.function_call for p in message.parts if p.function_call]
 
        if not calls:  # model is done: final answer
            return response.text, sources, steps
 
        contents.append(message)
        result_parts = []
        for call in calls:
            args = dict(call.args)
            steps.append({"tool": call.name, "args": args})
            try:
                result = TOOLS[call.name](**args)
            except Exception as e:
                result = {"error": str(e)}
            if call.name == "search_documents" and isinstance(result, list):
                for r in result:
                    key = (r["source"], r["page"])
                    if key not in seen:
                        seen.add(key)
                        sources.append({"source": r["source"], "page": r["page"]})
            result_parts.append(
                types.Part.from_function_response(
                    name=call.name, response={"result": result}
                )
            )
        contents.append(types.Content(role="user", parts=result_parts))
 
    return "I could not finish within the step limit. Please rephrase.", sources, steps
