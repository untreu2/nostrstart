from bech32 import bech32_decode, bech32_encode, convertbits

# Decoding pubkey (nip19 to hex)
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

# Encoding pubkey (hex to nip19)
def encode_npub(pubkey: str) -> str:
    """
    npub to hex func:
    """
    try:
        pubkey_bytes = bytes.fromhex(pubkey)
    except ValueError:
        raise ValueError("Invalid hex.")

    data = convertbits(list(pubkey_bytes), 8, 5, True)

    npub = bech32_encode("npub", data)
    return npub

# Decoding privkey
def decode_nsec(nsec: str) -> str:
    """
    nsec to hex func:
    """
    hrp, data = bech32_decode(nsec)
    if hrp != 'nsec':
        raise ValueError("Invalid nsec format.")
    decoded = convertbits(data, 5, 8, False)
    if decoded is None:
        raise ValueError("Invalid nsec data.")
    privkey = bytes(decoded).hex()
    return privkey

# Encoding privkey (hex to nip19)
def encode_nsec(privkey: str) -> str:
    """
    nsec to hex func:
    """
    try:
        privkey_bytes = bytes.fromhex(privkey)
    except ValueError:
        raise ValueError("Invalid hex.")

    data = convertbits(list(privkey_bytes), 8, 5, True)

    nsec = bech32_encode("nsec", data)
    return nsec
