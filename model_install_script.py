from ollama import chat

response = chat(
    model='deepseek-v4-flash:cloud',
    messages=[{'role': 'user', 'content': 'Hello!'}],
)
print(response.message.content)