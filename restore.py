import asyncio
import json
import os
from bech32 import bech32_decode, convertbits
import websockets

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

def decode_npub(npub: str) -> str:
    """
    Decodes an npub key into a hexadecimal public key.
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
    Fetches the user's relay list (NIP-65) from popular relays and returns a dictionary
    with 'read' and 'write' relay lists.
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

async def publish_to_relay(relay_url: str, events: list):
    """
    Publishes each event to a single relay.
    """
    try:
        async with websockets.connect(relay_url) as websocket:
            for event in events:
                # Each event is sent as an "EVENT" message.
                message = json.dumps(["EVENT", event])
                await websocket.send(message)
    except Exception as e:
        print(f"Unable to connect to relay {relay_url}: {e}")

async def broadcast_events(relays: list, events: list):
    """
    Broadcasts events to all specified relays concurrently.
    """
    tasks = [publish_to_relay(relay, events) for relay in relays]
    await asyncio.gather(*tasks)

async def main():
    try:
        # Get the user's npub key to fetch relay list
        npub_input = input("Please enter your npub key: ").strip()
        if not npub_input:
            print("Invalid npub key.")
            return

        pubkey = decode_npub(npub_input)
        print(f"Decoded Public Key: {pubkey}")

        # Fetch the user's relay list (NIP-65)
        print("Fetching relay list...")
        relay_list = await fetch_relay_list(pubkey)
        write_relays = relay_list.get("write", [])
        if not write_relays:
            print("No write relays found.")
            return
        print(f"User's Write Relays: {write_relays}")

        # Locate the backup folder and list available backup files
        backup_folder = os.path.join(os.getcwd(), "backup")
        if not os.path.exists(backup_folder):
            print("Backup folder does not exist.")
            return

        backup_files = [f for f in os.listdir(backup_folder) if f.endswith(".json")]
        if not backup_files:
            print("No backup files found in the backup folder.")
            return

        print("Available backup files:")
        for i, filename in enumerate(backup_files):
            print(f"{i+1}. {filename}")

        selection = input("Select the backup file to restore (enter the number): ").strip()
        try:
            index = int(selection) - 1
            if index < 0 or index >= len(backup_files):
                print("Invalid selection.")
                return
        except ValueError:
            print("Invalid selection.")
            return

        backup_file = os.path.join(backup_folder, backup_files[index])
        with open(backup_file, "r", encoding="utf-8") as f:
            events = json.load(f)
        print(f"Loaded {len(events)} events from {backup_file}")

        if not events:
            print("No events found in the backup file.")
            return

        # Publish events to the write relays
        print("Broadcasting events to write relays...")
        await broadcast_events(write_relays, events)
        print("Events have been successfully published to the relay list.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
