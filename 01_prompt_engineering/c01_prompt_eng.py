from openai import OpenAI

api_key = "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"

client = OpenAI(api_key=api_key)

response = client.chat.completions.create(
    model="gpt-4o",
    temperature=0.1,
    messages=[
        {"role": "system", "content": "너는 배트맨에 나오는 빌런 조커다. 악당 조커의 입장에서 롤플레이한다고 생각하고 말해봐."},
        {"role": "user", "content": "서울대학교 농업생명과학대학 대학원생들에 대해 말해봐"},
    ]
)

print(response)
