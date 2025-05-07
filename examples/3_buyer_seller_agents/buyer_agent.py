import os
import sys
import asyncio
import random
from summoner.client import SummonerClient

state = {
    "current_offer": 0,
    "agreement": "none",
    "negotiation_active": False,
    "MAX_ACCEPTABLE_PRICE": 0,
    "PRICE_INCREMENT": 0,
}

# Don't initialize locks yet!
state_lock = None
history = []
history_lock = None

async def show_statistics(self: SummonerClient):
    async with history_lock:
        success_num = sum(history)
        total = len(history)
    success_rate = (success_num / total) * 100 if total else 0
    print(f"\n\033[96m[{self.name}] Negotiation success rate: {success_rate:.2f}% ({success_num} successes / {total} total)\033[0m")

async def negotiation(self: SummonerClient):
    while True:
        async with state_lock:
            state["MAX_ACCEPTABLE_PRICE"] = random.randint(65, 80)
            state["PRICE_INCREMENT"] = random.randint(1, 5)
            state["current_offer"] = random.randint(1, state["MAX_ACCEPTABLE_PRICE"])
            state["agreement"] = "none"
            state["negotiation_active"] = True
            print(f"\n\033[94m[{self.name}] New negotiation started. MIN: {state['current_offer']}, MAX: {state['MAX_ACCEPTABLE_PRICE']}\033[0m")
        while True:
            async with state_lock:
                still_negotiating = state["negotiation_active"]
            if not still_negotiating:
                break
            await asyncio.sleep(1)

if __name__ == "__main__":
    agent = SummonerClient(name="BuyerAgent", option="python")

    # NOW create the locks inside the right event loop
    async def setup():
        global state_lock, history_lock
        state_lock = asyncio.Lock()
        history_lock = asyncio.Lock()

        @agent.receive(route="offer_response")
        async def handle_seller_response(msg):
            content = msg["content"]
            print(f"[Received] {content}")
            
            async with state_lock:
                renew = content["status"] in ["offer"] and state["agreement"] in ["accept","refuse"]
                if renew:
                    state["agreement"] = "none"
                    state["negotiation_active"] = False
                    await asyncio.sleep(1)

            if content["status"] == "offer":
                offer = content['price']
                async with state_lock:
                    if offer <= state["MAX_ACCEPTABLE_PRICE"]:
                        state["current_offer"] = offer
                        state["agreement"] = "interested"
                        print(f"\033[90m[{agent.name}] Interested in offer at price {offer}!\033[0m")
                    else:
                        state["current_offer"] += state["PRICE_INCREMENT"]
                        print(f"\033[90m[{agent.name}] Increasing price at {state['current_offer']}!\033[90m")

            if content["status"] == "interested":
                offer = content['price']
                async with state_lock:
                    if offer <= state["MAX_ACCEPTABLE_PRICE"]:
                        state["current_offer"] = offer
                        state["agreement"] = "accept"
                        print(f"\033[90m[{agent.name}] Accepting offer at price {offer}!\033[0m")
                    else:
                        state["agreement"] = "refuse"
                        print(f"\033[90m[{agent.name}] Refusing offer at price {offer}!\033[0m")

            if content["status"] == "accept":
                async with state_lock:
                    if state["agreement"] == "accept":
                        async with history_lock:
                            history.append(1)
                        await show_statistics(agent)
                        state["agreement"] = "none"
                        state["negotiation_active"] = False
                    elif state["agreement"] == "interested" and content['price'] == state["current_offer"]: #check it is same transaction
                        async with history_lock:
                            history.append(1)
                        await show_statistics(agent)
                        state["agreement"] = "accept"
                    else:
                        state["agreement"] = "none"
   
            if content["status"] == "refuse":
                async with state_lock:
                    if state["agreement"] == "refuse":
                        async with history_lock:
                            history.append(0)
                        await show_statistics(agent)
                        state["agreement"] = "none"
                        state["negotiation_active"] = False
                    elif state["agreement"] == "interested" and content['price'] == state["current_offer"]: #check it is same transaction
                        async with history_lock:
                            history.append(0)
                        await show_statistics(agent)
                        state["agreement"] = "refuse"
                    else:
                        state["agreement"] = "none"

        @agent.send(route="buyer_offer")
        async def make_offer():
            await asyncio.sleep(2)

            async with state_lock:
                offer = state["current_offer"]
                decision = state["agreement"]

            if decision == "interested":
                print(f"\033[96m[{agent.name}] Interested in offer: {offer}\033[0m")
                yield {"status": "interested", "price": offer}
            elif decision == "accept":
                print(f"\033[92m[{agent.name}] Accepted offer: {offer}\033[0m")
                yield {"status": "accept", "price": offer}
            elif decision == "refuse":
                print(f"\033[91m[{agent.name}] Refused offer: {offer}\033[0m")
                yield {"status": "refuse", "price": offer}
            else:
                print(f"\033[93m[{agent.name}] Offering price: {offer}\033[0m")
                yield {"status": "offer", "price": offer}

        agent.loop.create_task(negotiation(agent))

    agent.loop.run_until_complete(setup())
    agent.run(host="127.0.0.1", port=8888)
