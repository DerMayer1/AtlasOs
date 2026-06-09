from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlparse

from bs4 import BeautifulSoup

MAX_CHARS = 16_000
MAX_RESPONSE_BYTES = 2 * 1024 * 1024

_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("fc00::/7"),
]


def is_safe_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    string_blocked = [
        "localhost",
        "metadata.google.internal",
        "169.254.169.254",
    ]
    if any(host == blocked or host.startswith(blocked + ".") for blocked in string_blocked):
        return False

    try:
        infos = socket.getaddrinfo(host, None)
        for info in infos:
            raw_ip = info[4][0]
            try:
                address = ipaddress.ip_address(raw_ip)
            except ValueError:
                continue
            if (
                address.is_private
                or address.is_loopback
                or address.is_link_local
                or address.is_reserved
            ):
                return False
            if any(address in network for network in _PRIVATE_NETWORKS):
                return False
    except socket.gaierror:
        pass

    return True


def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(
        ["script", "style", "nav", "footer", "header", "noscript", "svg", "img"]
    ):
        tag.decompose()

    priority_tags = soup.find_all("main")
    if not priority_tags:
        priority_tags = soup.find_all("article")
    if not priority_tags:
        priority_tags = soup.find_all(["h1", "h2", "h3", "p", "li"])
    if priority_tags:
        text = " ".join(
            tag.get_text(separator=" ", strip=True) for tag in priority_tags
        )
    else:
        text = soup.get_text(separator=" ", strip=True)

    text = re.sub(r"\s+", " ", text).strip()
    return text[:MAX_CHARS]
