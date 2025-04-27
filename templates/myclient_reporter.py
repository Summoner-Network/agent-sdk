import os
import sys
import queue
import asyncio

# thread-safe FIFO for all incoming messages
message_buffer = queue.Queue()

# ensure we can import SummonerClient
target_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if target_path not in sys.path:
    sys.path.insert(0, target_path)

from summoner.client import SummonerClient

if __name__ == "__main__":
    myagent = SummonerClient(name="OrderAgent", option="python")

    @myagent.receive(route="custom_receive")
    async def custom_receive(msg):
        # extract content
        content = msg["content"] if isinstance(msg, dict) else msg

        # enqueue into our global, thread-safe buffer
        message_buffer.put(content)

        # also print it immediately
        tag = "\r[From server]" if content.startswith("Warning:") else "\r[Received]"
        print(tag, content, flush=True)
        print("r> ", end="", flush=True)

    @myagent.send(route="custom_send")
    async def custom_send():
        # wait (in a thread) for at least one message to arrive
        loop = asyncio.get_event_loop()
        first = await loop.run_in_executor(None, message_buffer.get)
        batch = [first]
        # now drain any remaining messages without blocking
        while True:
            try:
                msg = message_buffer.get_nowait()
                batch.append(msg)
            except queue.Empty:
                break

        # mark all as done
        for _ in batch:
            message_buffer.task_done()

        # send as one ordered batch (delimited by newlines)
        return "\n".join(batch)

    myagent.run(host="127.0.0.1", port=8888)
