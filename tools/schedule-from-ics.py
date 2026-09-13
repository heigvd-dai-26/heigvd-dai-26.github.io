#!/usr/bin/env python3
"""schedule-from-ics.py — expand a GAPS .ics export into schedule table rows.

Finds the <CLASS>-C1 (cours) and <CLASS>-L1 (labo) recurring events, expands
their weekly recurrence minus EXDATE holidays, pairs them by ISO week, and
prints a Markdown table skeleton for index.qmd (content column left empty).

Usage:
  tools/schedule-from-ics.py Horaire.ics DAI-TIC-A
"""

import re
import sys
from datetime import datetime, timedelta


def parse_events(text: str):
    for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", text, re.DOTALL):
        get = lambda k: re.search(rf"^{k}[^:]*:(.*)$", block, re.MULTILINE)
        summary = get("SUMMARY")
        dtstart = re.search(r"^DTSTART;TZID=[^:]+:(\d{8}T\d{6})", block, re.MULTILINE)
        dtend = re.search(r"^DTEND;TZID=[^:]+:(\d{8}T\d{6})", block, re.MULTILINE)
        if not (summary and dtstart):
            continue
        until = re.search(r"UNTIL=(\d{8})T", block)
        exdates = set()
        for m in re.finditer(r"^EXDATE[^:]*:(.*)$", block, re.MULTILINE):
            exdates |= {d[:8] for d in m.group(1).strip().split(",") if d}
        yield {
            "summary": summary.group(1).strip(),
            "start": datetime.strptime(dtstart.group(1), "%Y%m%dT%H%M%S"),
            "end": datetime.strptime(dtend.group(1), "%Y%m%dT%H%M%S") if dtend else None,
            "until": datetime.strptime(until.group(1), "%Y%m%d") if until else None,
            "exdates": exdates,
            "location": get("LOCATION").group(1).strip() if get("LOCATION") else "?",
        }


def expand(ev):
    d = ev["start"]
    while ev["until"] is None or d.date() <= ev["until"].date():
        if d.strftime("%Y%m%d") not in ev["exdates"]:
            yield d
        d += timedelta(weeks=1)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    text = open(sys.argv[1], encoding="utf-8").read()
    prefix = sys.argv[2]

    events = {e["summary"]: e for e in parse_events(text)}
    cours = events.get(f"{prefix}-C1")
    labo = events.get(f"{prefix}-L1")
    if not cours:
        sys.exit(f"No event {prefix}-C1 found. Events: {', '.join(sorted(events))}")

    fmt_time = lambda e: f"{e['start']:%H:%M}–{e['end']:%H:%M}" if e["end"] else f"{e['start']:%H:%M}"
    print(f"<!-- {prefix}: cours {cours['start']:%A} {fmt_time(cours)} ({cours['location']})"
          + (f", labo {labo['start']:%A} {fmt_time(labo)} ({labo['location']})" if labo else "")
          + " -->")
    print()
    print("| Week | Cours | Labo | Content | Slides |")
    print("|-----:|-------|------|---------|--------|")

    by_week = {}
    for d in expand(cours):
        by_week.setdefault(d.isocalendar()[:2], {})["cours"] = d
    if labo:
        for d in expand(labo):
            by_week.setdefault(d.isocalendar()[:2], {})["labo"] = d

    for n, (week, days) in enumerate(sorted(by_week.items()), 1):
        c = f"{days['cours']:%d.%m}" if "cours" in days else "—"
        l = f"{days['labo']:%d.%m}" if "labo" in days else "—"
        print(f"| {n} | {c} | {l} | | |")


if __name__ == "__main__":
    main()
