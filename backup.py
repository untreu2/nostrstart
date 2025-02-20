import asyncio
import json
import os
import datetime
from bech32 import bech32_decode, convertbits
import websockets
from conkey import decode_npub

# Popular relays used to fetch the user's relay list (NIP-65)
POPULAR_RELAYS = [
    "wss://eu.purplerelay.com",
    "wss://nos.lol",
    "wss://nosdrive.app/relay",
    "wss://nostrelites.org",
    "wss://relay.damus.io",
    "wss://relay.nostr.band",
    "wss://relay.primal.net",
    "wss://relay.snort.social",
    "wss://vitor.nostr1.com",
]


async def fetch_relay_list(pubkey: str) -> dict:
    """
    Fetches the user's relay list (NIP-65) from popular relays and returns read and write relay lists.
    """
    for relay_url in POPULAR_RELAYS:
        try:
            async with websockets.connect(relay_url) as websocket:
                sub_id = os.urandom(4).hex()
                # Request relay list event (kind=10002)
                request = json.dumps([
                    "REQ", sub_id, {"kinds": [10002], "authors": [pubkey]}
                ])
                await websocket.send(request)

                relay_list = {"read": [], "write": []}
                while True:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=10)
                    except asyncio.TimeoutError:
                        # Stop waiting after timeout
                        break

                    message = json.loads(response)

                    if message[0] == "EVENT" and message[1] == sub_id:
                        event = message[2]
                        if event.get("kind") == 10002:
                            for tag in event.get("tags", []):
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
                    elif message[0] == "EOSE" and message[1] == sub_id:
                        break

                if relay_list["read"] or relay_list["write"]:
                    return relay_list

        except Exception as e:
            print(f"Unable to connect to relay {relay_url}: {e}")

    # If no relay provides a relay list, return default relays.
    print("Failed to fetch NIP-65 relay list from any relay. Using default relays.")
    return {"read": POPULAR_RELAYS, "write": POPULAR_RELAYS}

async def fetch_all_events(relays: list, pubkey: str) -> list:
    """
    Fetches all historical events for the given public key from the provided relays.
    """
    events = []
    for relay_url in relays:
        try:
            async with websockets.connect(relay_url) as websocket:
                sub_id = os.urandom(4).hex()
                # Request events (kinds 0 to 40000)
                request = json.dumps([
                    "REQ", sub_id, {"kinds": list(range(0, 40000)), "authors": [pubkey]}
                ])
                await websocket.send(request)

                while True:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=10)
                    except asyncio.TimeoutError:
                        break

                    message = json.loads(response)
                    if message[0] == "EVENT" and message[1] == sub_id:
                        event = message[2]
                        events.append(event)
                    elif message[0] == "EOSE" and message[1] == sub_id:
                        break

        except Exception as e:
            print(f"Unable to connect to relay {relay_url}: {e}")

    return events

def save_events_to_backup(pubkey: str, events: list):
    """
    Saves the fetched events into a JSON file in a backup folder.
    """
    backup_folder = os.path.join(os.getcwd(), "backup")
    if not os.path.exists(backup_folder):
        os.makedirs(backup_folder)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{pubkey[:8]}_{timestamp}_backup.json"
    filepath = os.path.join(backup_folder, filename)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(events, f, ensure_ascii=False, indent=4)
        print(f"Events successfully saved to {filepath}")
    except Exception as e:
        print(f"Failed to save events: {e}")

async def main():
    try:
        npub_input = input("Please enter the user's npub key: ").strip()
        if not npub_input:
            print("Invalid npub key.")
            return

        # Decoding npub (using ./conkey.py)
        pubkey = decode_npub(npub_input)
        print(f"Decoded Public Key: {pubkey}")

        # Fetch the user's relay list (NIP-65)
        print("Fetching relay list...")
        relay_list = await fetch_relay_list(pubkey)
        read_relays = relay_list.get("read", [])
        print(f"User's Read Relays: {read_relays}")

        # Fetch events from the user's relays
        print("Fetching events from relays...")
        events = await fetch_all_events(read_relays, pubkey)
        print(f"Total {len(events)} events fetched.")

        if events:
            # Save the events to a backup file
            save_events_to_backup(pubkey, events)
        else:
            print("No events found to backup.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
