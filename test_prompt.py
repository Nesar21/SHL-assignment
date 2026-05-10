import asyncio
from app import agent
from app.models import ChatRequest, Message

async def main():
    req = ChatRequest(messages=[
        Message(role="user", content="I need assessments for a mid-level financial analyst role. They need numerical reasoning, basic statistics knowledge, and a personality assessment. Must support French and German.")
    ])
    res = await agent.process(req)
    print("Recommendations returned:", len(res.recommendations))
    print("Reply:", res.reply)
    print("EOC:", res.end_of_conversation)

asyncio.run(main())
