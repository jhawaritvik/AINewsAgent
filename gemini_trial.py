from google import genai

# The client gets the API key from the environment variable `GEMINI_API_KEY`.
client = genai.Client()

response = client.models.generate_content(
    model="gemini-2.5-flash", contents="What is the capital of France?"
)
print(response.text)

model_info = client.models.get(model="gemini-2.5-flash")
print(f"{model_info.input_token_limit=}")
print(f"{model_info.output_token_limit=}")

