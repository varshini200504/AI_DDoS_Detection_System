from scapy.all import get_if_list

def get_working_interface():
    """Auto-detect the primary network interface.

    Preference order: Ethernet > Wi-Fi > eth/wlan > first available
    Returns None if no interface found.
    """
    interfaces = get_if_list()

    if not interfaces:
        return None

    priority = ["ethernet", "wi-fi", "wifi", "eth", "wlan"]

    for pref in priority:
        for iface in interfaces:
            if pref in iface.lower():
                return iface

    # Fallback: return first non-loopback interface
    for iface in interfaces:
        if iface and not iface.startswith("lo"):
            return iface

    return interfaces[0]
