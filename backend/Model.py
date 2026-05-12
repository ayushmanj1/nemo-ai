import cohere
import re
from rich import print
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv(override=True)

# Retrieve API key
CohereAPIKey = os.getenv("CohereAPIKey")

# Create a Cohere client using the provided API key.
if not CohereAPIKey:
    print("Warning: CohereAPIKey is missing from .env")
    co = None
else:
    co = cohere.Client(api_key=CohereAPIKey)

GroqAPIKey = os.getenv("GroqAPIKey")
if GroqAPIKey:
    from groq import Groq
    groq_client = Groq(api_key=GroqAPIKey)
else:
    groq_client = None

# Define a list of recognized function keywords for task categorization.
funcs = [
    "exit", "general", "realtime", "generate image", "content"
]

# --- REAL-TIME KEYWORDS FOR FAST DETECTION ---
REALTIME_KEYWORDS = [
    "weather", "news", "price", "stock", "score", "match", "live", "today", "now",
    "current", "latest", "update", "who is", "what is", "happening", "temperature", 
    "gold", "silver", "bitcoin", "ipl", "football", "cricket", "president", 
    "prime minister", "governor", "ceo", "releasing", "movie", "match today",
    "cm", "pm", "chief minister", "minister", "capital", "population", "born", 
    "death", "alive", "richest", "top 10", "standing", "points table", "result",
    "who won", "who lost", "winner", "when is", "when did", "where is", "how many",
    "how much", "salary", "net worth", "age of", "height of", "wife of", "husband of",
    "founder", "owner", "director", "actor", "actress", "singer", "player",
    "election", "war", "conflict", "deal", "merger", "acquisition", "launched",
    "released", "announced", "controversy", "scandal", "arrested", "died",
    "ranking", "ranked", "fastest", "tallest", "biggest", "smallest", "record"
]

def is_realtime_query(query):
    query_lower = query.lower()
    # Check if any keyword matches as a whole word or significant part
    for keyword in REALTIME_KEYWORDS:
        if re.search(r'\b' + re.escape(keyword) + r'\b', query_lower):
            return True
    return False

# Define the preamble that guides the AI model on how to categorize queries.
# Load assistant name for categorization layer
Assistantname = os.getenv("Assistantname", "Thing")

preamble = f"""You are a highly accurate Decision-Making Model for {Assistantname}. 
Your ONLY task is to categorize the user's query into one or more categories.

*** CATEGORY LIST: ***
-> 'realtime query': For ANY factual info, news, weather, prices, or web searches. (PRIORITY)
-> 'general query': For greetings, jokes, personal/emotive chat, or general conversation.
-> 'content topic': For formal writing, code, essays, or long-form applications ONLY.
-> 'generate image prompt': To create images.

*** MANDATORY RULES: ***
1. ONLY respond with the tags mentioned above. 
2. DO NOT engage in conversation. 
3. DO NOT explain your decision. 
4. DO NOT provide any text other than the categorized tags.
5. If the user query is multiple things, separate tags with a comma.
6. If the user query matches NO specific task, always choose 'general query'.
7. USE the recent conversation context to understand follow-up queries.
   For example, if the user previously asked about "Virat Kohli" and now asks "his father",
   you MUST expand it using context: 'general Virat Kohli his father' or 'realtime Virat Kohli his father'.
8. For vague follow-ups like "are you sure", "yes", "ok", "tell me more", "give link", etc.,
   treat them as 'general query' and include the original topic in your tag.
"""

# Define a chat history with predefined user-chatbot interactions for context.
ChatHistory = [
    {"role": "User", "message": f"hello {Assistantname.lower()}"},
    {"role": "Chatbot", "message": f"general hello {Assistantname.lower()}"},
    {"role": "User", "message": "what is the price of gold in india?"},
    {"role": "Chatbot", "message": "realtime what is the price of gold in india?"},
    {"role": "User", "message": "who is the current prime minister?"},
    {"role": "Chatbot", "message": "realtime who is the current prime minister?"},
    {"role": "User", "message": "tell me a joke"},
    {"role": "Chatbot", "message": "general tell me a joke"},
    {"role": "User", "message": "what is happening in us iran right now?"},
    {"role": "Chatbot", "message": "realtime what is happening in us iran right now?"},
    {"role": "User", "message": "current stock price of nvidia"},
    {"role": "Chatbot", "message": "realtime current stock price of nvidia"},
    {"role": "User", "message": "i love you so much"},
    {"role": "Chatbot", "message": "general i love you so much"},
    {"role": "User", "message": "is it raining in london?"},
    {"role": "Chatbot", "message": "realtime is it raining in london?"},
    {"role": "User", "message": "give me a python code for bubble sort"},
    {"role": "Chatbot", "message": "content give me a python code for bubble sort"},
    {"role": "User", "message": "what is the format of a formal letter?"},
    {"role": "Chatbot", "message": "general what is the format of a formal letter?"},
    {"role": "User", "message": "tell me the format for a notice for school assembly"},
    {"role": "Chatbot", "message": "general tell me the format for a notice for school assembly"},
    {"role": "User", "message": "explain how a convolutional neural network works"},
    {"role": "Chatbot", "message": "content explain how a convolutional neural network works"},
    {"role": "User", "message": "write a leave application for school"},
    {"role": "Chatbot", "message": "content write a leave application for school"}
]

# Define the main function for decision-making on queries.
def FirstLayerDMM(prompt: str = "test", conversation_history: list = None):
    # 1. Fast Pass: Keyword-based real-time detection
    if is_realtime_query(prompt):
        print(f"[Model] Fast Pass: Real-time query detected for '{prompt}'")
        return ["realtime " + prompt]

    try:
        if not co: return ["general " + prompt]
        
        if groq_client:
            # Format history for Groq
            groq_messages = [{"role": "system", "content": preamble}]
            for msg in ChatHistory:
                role = "user" if msg["role"] == "User" else "assistant"
                groq_messages.append({"role": role, "content": msg["message"]})
            
            # Inject recent conversation context so follow-up queries are understood
            if conversation_history:
                recent = conversation_history[-6:]  # Last 3 exchanges (user+assistant pairs)
                context_block = "\n".join(
                    f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content'][:150]}"
                    for m in recent
                )
                groq_messages.append({"role": "user", "content": f"[Recent conversation context]:\n{context_block}\n\n[Now categorize this new query]:"})
                groq_messages.append({"role": "assistant", "content": "Understood, I will use this context to categorize the next query."})
            
            groq_messages.append({"role": "user", "content": prompt})

            try:
                print(f"[Model] Calling Groq Decision model...")
                completion = groq_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=groq_messages,
                    temperature=0.1,
                    max_tokens=64
                )
                response = completion.choices[0].message.content.strip()
                print(f"[Model] Groq Decision: {response}")
            except Exception as e:
                print(f"Groq Decision Error: {e}, falling back to Cohere...")
                response = ""
        else:
            response = ""

        # Fallback to Cohere
        if not response and co is not None:
            stream = co.chat_stream(
                model='command-r-plus-08-2024',
                message=prompt,
                temperature=0.1,
                chat_history=ChatHistory,
                prompt_truncation='OFF',
                connectors=[],
                preamble=preamble
            )
            for event in stream:
                if event.event_type == "text-generation":
                    response += event.text
    except Exception as e:
        print(f"Decision Error: {e}")
        return ["general " + prompt]

    if not response:
        return ["general " + prompt]

    # Process response
    response = response.replace("\n", "").split(",")
    response = [i.strip() for i in response]

    # Filter the tasks based on recognized function keywords.
    temp = []
    for task in response:
        matched = False
        for func in funcs:
            if task.lower().startswith(func):
                clean_task = task.lower().replace(func, "").strip()
                if not clean_task:
                    task = f"{func} {prompt}"
                temp.append(task)
                matched = True
                break
    
    # Final Result with Fallback
    if not temp:
        result = ["general " + prompt]
    else:
        result = temp

    return result

# Entry point for the script.
if __name__ == "__main__":
    while True:
        print(FirstLayerDMM(input(">>> ")))