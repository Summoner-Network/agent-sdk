#!/usr/bin/env python3
import asyncio
from aiohttp import web
import json

# ——————————————————————————————————————————————————————————————
# Your “transform” function: takes List[str] → List[str].
# By default it just echoes.
# You can swap this out for your real logic.
# ——————————————————————————————————————————————————————————————
async def transform(inputs: list[str]) -> list[str]:
    # placeholder: echo each string back
    await asyncio.sleep(0)   # simulate async work
    return inputs

# ——————————————————————————————————————————————————————————————
# HTTP handler
# Expects JSON body: { "inputs": ["foo","bar",…] }
# Returns      JSON: { "outputs": ["foo","bar",…] }
# ——————————————————————————————————————————————————————————————
async def handle_transform(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        inputs = data.get("inputs")
        if not isinstance(inputs, list) or not all(isinstance(s, str) for s in inputs):
            raise ValueError
    except Exception:
        return web.json_response(
            {"error": "invalid payload, expected {\"inputs\":[string,...]}"},
            status=400
        )

    outputs = await transform(inputs)
    return web.json_response({"outputs": outputs})

# ——————————————————————————————————————————————————————————————
# Wiring up the aiohttp application
# ——————————————————————————————————————————————————————————————
def create_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/transform", handle_transform)
    return app

if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=8000)
