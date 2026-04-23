#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, Iterable, Optional, Tuple


def _cdata(text: str) -> str:
    # LinkedIn expects HTML in CDATA. XML 1.0 forbids "]]>" inside CDATA, so split safely.
    return "<![CDATA[" + text.replace("]]>", "]]]]><![CDATA[>") + "]]>"


def _text(el: Optional[ET.Element]) -> str:
    return (el.text or "").strip() if el is not None else ""


def _find_child_by_localname(parent: ET.Element, localname: str) -> Optional[ET.Element]:
    for child in list(parent):
        if (child.tag.split("}", 1)[-1] if "}" in child.tag else child.tag) == localname:
            return child
    return None


def _get_item_field(item: ET.Element, tag: str, ns: Optional[str] = None) -> str:
    if ns:
        el = item.find(f"{{{ns}}}{tag}")
    else:
        el = item.find(tag)
        if el is None:
            el = _find_child_by_localname(item, tag)
    return _text(el)


def _parse_pubdate_rss(pubdate: str) -> Optional[dt.datetime]:
    # Example: "Thu, 09 Apr 2026 13:51:30 Z"
    pubdate = pubdate.strip()
    if not pubdate:
        return None
    for fmt in ("%a, %d %b %Y %H:%M:%S Z", "%a, %d %b %Y %H:%M:%S %z"):
        try:
            parsed = dt.datetime.strptime(pubdate, fmt)
            return parsed.replace(tzinfo=dt.timezone.utc) if parsed.tzinfo is None else parsed
        except ValueError:
            continue
    return None


def _fetch_xml(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (LinkedInFeedGenerator)"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return resp.read()


def _iter_rss_items(rss_xml: bytes) -> Tuple[str, Iterable[ET.Element]]:
    root = ET.fromstring(rss_xml)
    channel = root.find("channel")
    if channel is None:
        raise ValueError("RSS missing <channel>")
    channel_title = _text(channel.find("title"))
    return channel_title, channel.findall("item")


def _partner_job_id(item: ET.Element) -> str:
    job_number = _get_item_field(item, "jobNumber")
    if job_number:
        return job_number[:40]

    guid = _get_item_field(item, "guid")
    if guid:
        # Use last path segment to keep it short.
        tail = guid.rstrip("/").split("/")[-1]
        return tail[:40]

    link = _get_item_field(item, "link")
    if link:
        tail = link.rstrip("/").split("/")[-1]
        return tail[:40]

    # Worst case: stable-ish fallback
    return str(abs(hash(ET.tostring(item))))[:40]


def build_linkedin_feed(
    *,
    rss_xml: bytes,
    publisher: str,
    publisher_url: str,
    company: str,
    company_id: str,
    poster_email: str,
) -> str:
    channel_title, items = _iter_rss_items(rss_xml)

    now = dt.datetime.now(dt.timezone.utc)
    last_build_date = now.strftime("%a, %d %b %Y %H:%M:%S GMT")

    jobs: list[Dict[str, Any]] = []

    for item in items:
        title = _get_item_field(item, "title")
        apply_url = _get_item_field(item, "link") or _get_item_field(item, "guid")
        description_html = _get_item_field(item, "description")
        location = _get_item_field(item, "location")

        # If RSS is missing fields, skip (LinkedIn required fields).
        if not (title and apply_url and description_html and location):
            continue

        pub = _parse_pubdate_rss(_get_item_field(item, "pubDate"))
        list_date = pub.astimezone(dt.timezone.utc).strftime("%m/%d/%Y") if pub else None

        jobs.append(
            {
                "partnerJobId": _partner_job_id(item),
                "company": company or channel_title,
                "title": title,
                "description": description_html,
                "applyUrl": apply_url,
                "companyId": company_id,
                "location": location,
                "posterEmail": poster_email,
                "listDate": list_date,
            }
        )

    # Build XML manually to guarantee CDATA formatting and avoid escaping HTML.
    out: list[str] = []
    out.append('<?xml version="1.0" encoding="UTF-8"?>')
    out.append("<source>")
    out.append(f"  <lastBuildDate>{last_build_date}</lastBuildDate>")
    out.append(f"  <publisherUrl>{_cdata(publisher_url)}</publisherUrl>")
    out.append(f"  <publisher>{publisher}</publisher>")
    out.append(f"  <expectedJobCount>{_cdata(str(len(jobs)))}</expectedJobCount>")

    for j in jobs:
        out.append("  <job>")
        out.append(f"    <partnerJobId>{_cdata(j['partnerJobId'])}</partnerJobId>")
        out.append(f"    <company>{_cdata(j['company'])}</company>")
        out.append(f"    <title>{_cdata(j['title'])}</title>")
        out.append(f"    <description>{_cdata(j['description'])}</description>")
        out.append(f"    <applyUrl>{_cdata(j['applyUrl'])}</applyUrl>")
        out.append(f"    <companyId>{_cdata(j['companyId'])}</companyId>")
        out.append(f"    <location>{_cdata(j['location'])}</location>")
        if j.get("posterEmail"):
            out.append(f"    <posterEmail>{_cdata(j['posterEmail'])}</posterEmail>")
        if j.get("listDate"):
            out.append(f"    <listDate>{_cdata(j['listDate'])}</listDate>")
        out.append("  </job>")

    out.append("</source>")
    out.append("")  # trailing newline
    return "\n".join(out)


def _load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Transform Crelate RSS into LinkedIn Basic Jobs XML feed.")
    ap.add_argument("--config", required=True, help="Path to config JSON.")
    ap.add_argument("--out", required=True, help="Output XML path.")
    args = ap.parse_args(argv)

    cfg = _load_config(args.config)

    rss_url = cfg["rssUrl"]
    rss_xml = _fetch_xml(rss_url)

    xml = build_linkedin_feed(
        rss_xml=rss_xml,
        publisher=cfg.get("publisher") or "Jobs",
        publisher_url=cfg.get("publisherUrl") or "",
        company=cfg.get("company") or "",
        company_id=str(cfg.get("companyId") or ""),
        poster_email=str(cfg.get("posterEmail") or "").strip(),
    )

    out_path = args.out
    # Create parent dirs if needed
    import os

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(xml)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

