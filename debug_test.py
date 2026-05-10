import asyncio
from app import agent
from app.models import ChatRequest, Message

async def main():
    req = ChatRequest(messages=[
        Message(role="user", content="I need assessments for a senior Java developer. Include a personality test like OPQ.")
    ])
    res = await agent.process(req)
    print("Recommendations:", len(res.recommendations))
    print("Reply:", res.reply)

asyncio.run(main())
