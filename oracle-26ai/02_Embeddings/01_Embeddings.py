from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

def generate_local_embedding(text: str):
    return model.encode(text).tolist()

embeddings = generate_local_embedding("Hello world")
print(f"Length of embeddings :{len(embeddings)}")
print(embeddings)