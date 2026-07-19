# Stock Research Blog Maintenance

## Structured decision contract

Whenever a task creates or updates a post with `decision` frontmatter, keep these fields synchronized with the market data actually used:

- `market`: `CN`, `US`, or `HK`.
- `sessionDate`: the market trading date represented by `currentPrice`, formatted `YYYY-MM-DD`.
- `dataAsOf`: the exact market-data cutoff as an ISO timestamp with timezone offset. For a final close, use that market's close timestamp; for an intraday snapshot, use the verified quote timestamp.
- `asOf`: human-readable display text. It may mention the article generation time, but it does not replace `sessionDate` or `dataAsOf`.
- `updatedDate`: article maintenance time only. Never use it as a substitute for market-data freshness.
- `invalidation.direction`: `below` when a drop through the level invalidates the thesis, or `above` when a rise through it does.
- `invalidation.state`: `pending`, `near` (untriggered and within 3%), or `triggered`; it must agree with `currentPrice` and the configured direction.

Any prose that calls a value the current/latest price must match `decision.currentPrice` and `sessionDate`. Update or remove stale background-price claims whenever the decision snapshot changes.

Do not advance `sessionDate` or `dataAsOf` unless the quote and trading date were verified. If the source date is ambiguous, stop before editing rather than making the snapshot appear newer.

After editing structured research, run:

```bash
npm run validate:decisions
npm test
npm run build
```

The build must fail if market timestamps are missing or inconsistent. Do not bypass or weaken these validators in an automated update.
