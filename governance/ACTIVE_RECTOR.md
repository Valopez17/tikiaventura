# Active rector

There is exactly one operational rector.

```
ACTIVE_RECTOR_PATH=BTC_STRATEGY_RESEARCH_AUDIT_PACK_v4_1.md
ACTIVE_RECTOR_ID=v4.1
STATUS=APPROVED
APPROVED_BY=Valita
APPROVED_AT=2026-09-02
ACTIVE_RECTOR_SHA256=799cbfa8575ca5147a658bd85a5fab66d4a0c7ed4539296639d14cea88137778
```

That file is the sole source of methodological authority for new BTC Strategy Research OS work.

Do not edit `BTC_STRATEGY_RESEARCH_AUDIT_PACK_v4_1.md` to update operational status. Mutable state lives in `projects/btc_spot_1h/STATUS.md` and the append-only registries. A methodological change requires a new explicit rector version, not a silent edit of v4.1.

After any task that claims to leave v4.1 unchanged, the file SHA-256 must still equal `ACTIVE_RECTOR_SHA256`. If it does not, stop.

Historical rectors have no authority over new work. Locate them in `archive/ARCHIVE_MAP.md`.

Do not infer an active rector from chat memory, from a superseded markdown file, or from v2 alert-contract language.
