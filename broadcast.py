# pip install asyncio jsonlib-python3 bech32 websockets

import asyncio
import json
from bech32 import bech32_decode, convertbits
import websockets

# These relays will be used for fetching relay list of the user
POPULAR_RELAYS = [
    "wss://eu.purplerelay.com",
    "wss://nos.lol",
    "wss://nosdrive.app/relay",
    "wss://nos.lol",
    "wss://nostrelites.org",
    "wss://relay.damus.io",
    "wss://relay.nostr.band",
    "wss://relay.primal.net",
    "wss://relay.snort.social",
    "wss://vitor.nostr1.com",
]

# Relays to which events will be broadcasted
BROADCAST_TO_RELAYS = [
    "wss://relay.example.com",
    "wss://relay.something.com"
]

def decode_npub(npub: str) -> str:
    """
    npub to hex func:
    """
    hrp, data = bech32_decode(npub)
    if hrp != 'npub':
        raise ValueError("Invalid npub format.")
    decoded = convertbits(data, 5, 8, False)
    if decoded is None:
        raise ValueError("Invalid npub data.")
    pubkey = bytes(decoded).hex()
    return pubkey

async def fetch_relay_list(pubkey: str) -> dict:
    """
    Fetches the user's relay list (NIP-65) and returns it as read/write relays.
    """
    for relay_url in POPULAR_RELAYS:
        try:
            async with websockets.connect(relay_url) as websocket:
                # Fetch relay list event with kind=10002
                request = json.dumps([
                    "REQ", "relay_list", {"kinds": [10002], "authors": [pubkey]}
                ])
                await websocket.send(request)

                # Read the response
                relay_list = {"read": [], "write": []}
                while True:
                    response = await websocket.recv()
                    message = json.loads(response)

                    if message[0] == "EVENT" and message[1] == "relay_list":
                        event = message[2]
                        if event["kind"] == 10002:
                            for tag in event["tags"]:
                                if tag[0] == "r" and len(tag) > 1:
                                    uri = tag[1]
                                    role = tag[2] if len(tag) > 2 else None
                                    if role == "read":
                                        relay_list["read"].append(uri)
                                    elif role == "write":
                                        relay_list["write"].append(uri)
                                    else:
                                        relay_list["read"].append(uri)
                                        relay_list["write"].append(uri)
                            return relay_list

        except Exception as e:
            print(f"Unable to connect to relay {relay_url}: {e}")

    # If no relay provides a list, return the default relays
    print("Failed to fetch NIP-65 relay list from any relay. Using default relays.")
    return {"read": POPULAR_RELAYS, "write": POPULAR_RELAYS}

async def fetch_all_events(relays: list, pubkey: str) -> list:
    """
    Fetches all historical events of the user.
    """
    events = []
    for relay_url in relays:
        try:
            async with websockets.connect(relay_url) as websocket:
                # Fetch user events
                request = json.dumps([
                    "REQ", "all_events", {"kinds": list(range(1, 100)), "authors": [pubkey]}
                ])
                await websocket.send(request)

                # Read the responses
                while True:
                    response = await websocket.recv()
                    message = json.loads(response)

                    if message[0] == "EVENT" and message[1] == "all_events":
                        event = message[2]
                        events.append(event)
                    elif message[0] == "EOSE":
                        break

        except Exception as e:
            print(f"Unable to connect to relay {relay_url}: {e}")

    return events

async def publish_to_relay(relay_url: str, events: list):
    """
    Publishes events to a single relay.
    """
    try:
        async with websockets.connect(relay_url) as websocket:
            for event in events:
                request = json.dumps(["EVENT", event])
                await websocket.send(request)
    except Exception as e:
        print(f"Unable to connect to relay {relay_url}: {e}")

async def broadcast_events(relays: list, events: list):
    """
    Broadcasts all events to specified relays in parallel.
    """
    tasks = [publish_to_relay(relay_url, events) for relay_url in relays]
    await asyncio.gather(*tasks)

async def main():
    try:
        # Get npub input from the user
        npub_input = input("Please enter the user's npub key to broadcast: ").strip()
        if not npub_input:
            print("Invalid npub key.")
            return
        
        pubkey = decode_npub(npub_input)
        print(f"Public Key: {pubkey}")

        # Fetch relay list (NIP-65)
        print("Fetching relay list...")
        relay_lists = await fetch_relay_list(pubkey)
        print(f"User's Relay List (Read): {relay_lists['read']}")
        print(f"User's Relay List (Write): {relay_lists['write']}")

        # Fetch all events
        print("Fetching all events...")
        events = await fetch_all_events(relay_lists['write'], pubkey)
        print(f"Total {len(events)} events fetched.")

        if not events:
            print("No events found. Nothing to broadcast.")
            return

        # Broadcast events to the desired relays
        print("Broadcasting events to the relays...")
        await broadcast_events(BROADCAST_TO_RELAYS, events)
        print("All events were successfully broadcasted.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
