# What does one AI job really cost?

Price lists show dollars per million tokens. Your bill depends on how many tokens a model actually uses for **your** job, including the "thinking" tokens you never see (Gemini 4 Neon bills them at the output price).

`cost_test.py` sends the **same prompt** to Gemini 4 Neon and Claude (or any models in its price table), several times each, reads the token usage each API reports, and prints the average cost of one job.

## Run it

```bash
pip install requests
export GEMINI_API_KEY=...       # Google AI Studio key (Neon is paid tier only)
export ANTHROPIC_API_KEY=...    # Claude API key
python cost_test.py --prompt example_job.txt --runs 3
```

- Put your own task in a text file and pass it with `--prompt`. A real job from your business tells you more than any benchmark.
- Pick models with `--models gemini-4-neon,claude-sonnet-5-5,claude-opus-5-5`.
- `python cost_test.py --selftest` checks the cost math offline (no keys, made-up sample numbers).

## Prices used (standard tier, USD per 1M tokens, checked 22 Nov 2026)

| Model | Input | Output |
|---|---|---|
| Gemini 4 Neon | $3 | $15 (thinking included) |
| Gemini 4 Carbon | $2 → $4 from 1 Dec 2026 | $10 → $20 from 1 Dec 2026 |
| Claude Fable 5.2 | $8 | $40 |
| Claude Opus 5.5 | $4 | $20 |
| Claude Sonnet 5.5 | $2 | $10 |

Sources: [Gemini API pricing](https://aistudio.google.com/docs/pricing), [Claude pricing](https://platform.claude.com/docs/en/about-claude/pricing). Prices change, so check them and edit `PRICES` in the script.

Each run costs you a few cents of API usage.
