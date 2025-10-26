# backend/app.py
import json
import traceback
import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
from fastapi.responses import JSONResponse

from schemas import RunRequest
from graph import get_llm, initial_state, step_plan, step_search, step_synthesize
from memory import RollingBuffer
from settings import settings

app = FastAPI(title="Deep Research Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

memory = RollingBuffer(max_len=settings.MAX_MESSAGES)

def _sse(event: str, data: dict) -> str:
    """Format SSE message"""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"

@app.post("/run")
async def run(req: RunRequest, request: Request):
    print("\n🚀 /run endpoint called")
    print("Origin:", request.headers.get("origin"))
    print(f"Query: {req.query}")
    print(f"Config: {req.config.model_dump()}")
    print(f"Memory messages: {len(req.messages)}")

    memory.extend([m.model_dump() for m in req.messages])
    state = initial_state(
        query=req.query,
        config=req.config.model_dump(),
        messages=memory.as_messages()
    )

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # PLAN
            print("→ Sending planning status...")
            yield _sse("status", {"phase":"planning"})
            yield _sse("log", {"msg": "Starting planning phase..."})
            yield _sse("progress", {"percent": 10})
            
            print("→ Planning...")
            loop = asyncio.get_event_loop()
            state1 = await loop.run_in_executor(None, step_plan, state)
            plan = state1["plan"]
            print(f"Plan generated: {len(plan)} chars")
            
            yield _sse("plan", {"text": plan})
            yield _sse("log", {"msg": "Planning complete"})
            yield _sse("progress", {"percent": 33})

            # SEARCH
            print("→ Sending searching status...")
            yield _sse("status", {"phase":"searching"})
            yield _sse("log", {"msg": "Starting search phase..."})
            yield _sse("progress", {"percent": 40})
            
            print("→ Searching...")
            state2 = await loop.run_in_executor(None, step_search, state1)
            sources = state2["sources"]
            print(f"Found {len(sources)} unique sources")
            
            yield _sse("sources", {"count": len(sources), "top": sources[:5]})
            yield _sse("log", {"msg": f"Found {len(sources)} unique sources"})
            yield _sse("progress", {"percent": 66})

            # SYNTHESIZE
            print("→ Sending synthesizing status...")
            yield _sse("status", {"phase":"synthesizing"})
            yield _sse("log", {"msg": "Starting synthesis..."})
            yield _sse("progress", {"percent": 75})
            
            print("→ Synthesizing report...")
            state3 = await loop.run_in_executor(None, step_synthesize, state2)
            report = state3["report"]
            print(f"Report generated: {len(report['content'])} chars")
            
            yield _sse("log", {"msg":"Synthesis complete"})
            yield _sse("progress", {"percent": 90})

            # DONE
            print("→ Sending final report...")
            yield _sse("done", {"report": report})
            yield _sse("progress", {"percent": 100})
            print("🏁 Done.")

        except Exception as e:
            print(f"❌ Error in event_generator: {e}")
            traceback.print_exc()
            yield _sse("error", {"message": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )

# JSON fallback (no streaming) — handy for quick checks
@app.post("/run_sync")
async def run_sync(req: RunRequest):
    memory.extend([m.model_dump() for m in req.messages])
    state = initial_state(req.query, req.config.model_dump(), memory.as_messages())
    s1 = step_plan(state)
    s2 = step_search(s1)
    s3 = step_synthesize(s2)
    return JSONResponse(content={"report": s3["report"], "plan": s1["plan"], "sources": s2["sources"]})

# Chat endpoint for non-research questions
@app.post("/chat")
async def chat(req: RunRequest):
    """Simple chat endpoint without research - uses LLM with conversation context"""
    print("\n💬 /chat endpoint called")
    print(f"Query: {req.query}")
    print(f"Context messages: {len(req.messages)}")
    
    memory.extend([m.model_dump() for m in req.messages])
    
    try:
        llm = get_llm(req.config.provider, req.config.model)
        
        # Build conversation context
        messages = []
        for msg in memory.as_messages():
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Add current query
        messages.append({"role": "user", "content": req.query})
        
        # Get response
        response = llm.invoke(messages)
        
        return JSONResponse(content={
            "response": response.content,
            "mode": "chat"
        })
    except Exception as e:
        print(f"❌ Chat error: {e}")
        traceback.print_exc()
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )