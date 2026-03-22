import asyncio
import websockets

clients = set()

async def handler(ws):
    clients.add(ws)
    try:
        async for message in ws:
            dead = []
            for c in clients:
                if c == ws:
                    continue
                try:
                    await c.send(message)
                except Exception:
                    dead.append(c)
            for d in dead:
                clients.discard(d)
    finally:
        clients.discard(ws)

async def main():
    async with websockets.serve(handler, "0.0.0.0", 8080):
        print("WebSocket server listening on ws://0.0.0.0:8080")
        await asyncio.Future()

asyncio.run(main())
