from bech32 import bech32_decode, bech32_encode, convertbits

# Decode a simple bech32 format (npub, nsec, note) into hex
def decode_basic_bech32(value: str, expected_prefix: str) -> str:
    hrp, data = bech32_decode(value)
    if hrp != expected_prefix:
        raise ValueError(f"Invalid {expected_prefix} format.")
    decoded = convertbits(data, 5, 8, False)
    if decoded is None:
        raise ValueError(f"Invalid {expected_prefix} data.")
    return bytes(decoded).hex()

# Encode a hex string into npub, nsec or note
def encode_basic_bech32(hexstr: str, prefix: str) -> str:
    try:
        key_bytes = bytes.fromhex(hexstr)
    except ValueError:
        raise ValueError("Invalid hex string.")
    data = convertbits(list(key_bytes), 8, 5, True)
    return bech32_encode(prefix, data)

# Decode TLV and return a dict of all found fields
def decode_tlv_bech32_full(value: str, expected_prefix: str) -> dict:
    hrp, data = bech32_decode(value)
    if hrp != expected_prefix:
        raise ValueError(f"Invalid {expected_prefix} format.")
    decoded = convertbits(data, 5, 8, False)
    if decoded is None:
        raise ValueError("Invalid TLV data.")

    i = 0
    result = {
        "type_0_main": None,
        "relays": [],
        "author": None,
        "kind": None
    }

    while i < len(decoded):
        t = decoded[i]
        l = decoded[i + 1]
        v = decoded[i + 2:i + 2 + l]

        if t == 0:
            result["type_0_main"] = bytes(v).hex()
        elif t == 1:
            try:
                relay = bytes(v).decode("utf-8")
                result["relays"].append(relay)
            except UnicodeDecodeError:
                result["relays"].append("<invalid ascii>")
        elif t == 2:
            result["author"] = bytes(v).hex()
        elif t == 3:
            if l == 4:
                kind = int.from_bytes(v, byteorder="big")
                result["kind"] = kind
        # ignore unknown TLVs silently

        i += 2 + l

    if result["type_0_main"] is None:
        raise ValueError("Missing required TLV type 0.")

    return result

def main():
    print("Supported formats:")
    print(" - Decode: npub, nsec, note, nprofile, nevent")
    print(" - Encode: hex → npub / nsec / note")

    user_input = input("Enter a bech32 string or 64-char hex key: ").strip()

    if user_input.startswith("npub"):
        print("→ Decoded Public Key (hex):", decode_basic_bech32(user_input, "npub"))
    elif user_input.startswith("nsec"):
        print("→ Decoded Private Key (hex):", decode_basic_bech32(user_input, "nsec"))
    elif user_input.startswith("note"):
        print("→ Decoded Note ID (hex):", decode_basic_bech32(user_input, "note"))
    elif user_input.startswith("nprofile"):
        result = decode_tlv_bech32_full(user_input, "nprofile")
        print("→ Decoded nprofile:")
        print("  pubkey (type 0):", result["type_0_main"])
        for relay in result["relays"]:
            print("  relay (type 1):", relay)
    elif user_input.startswith("nevent"):
        result = decode_tlv_bech32_full(user_input, "nevent")
        print("→ Decoded nevent:")
        print("  event id (type 0):", result["type_0_main"])
        for relay in result["relays"]:
            print("  relay (type 1):", relay)
        if result["author"]:
            print("  author pubkey (type 2):", result["author"])
        if result["kind"] is not None:
            print("  kind (type 3):", result["kind"])
    elif len(user_input) == 64:
        target = input("Convert to which format? (npub/nsec/note): ").strip().lower()
        if target in ("npub", "nsec", "note"):
            print(f"→ Encoded {target}:", encode_basic_bech32(user_input, target))
        else:
            print("Unsupported target format.")
    else:
        print("Unrecognized input.")

if __name__ == "__main__":
    main()
