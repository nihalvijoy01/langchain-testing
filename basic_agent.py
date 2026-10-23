from google import genai

client = genai.Client()

stream = client.interactions.create(
    model="gemini-3.8-flash",
    input="Explain how AI works in one sentence.",
    stream=True
)
for event in stream:
    print(event)
