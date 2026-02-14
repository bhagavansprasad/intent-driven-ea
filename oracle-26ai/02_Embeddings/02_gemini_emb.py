from google import genai
client = genai.Client()

def generate_gemini_embedding(text: str):
    result = client.models.embed_content(model="gemini-embedding-001", contents=text)

    return result.embeddings[0].values


embeddings = generate_gemini_embedding("Hello world")
print(f"Length of embeddings :{len(embeddings)}")
print(embeddings)