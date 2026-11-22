"""cost_test.py: what does ONE job really cost on Gemini 4 Neon vs Claude? Same prompt, same settings, N runs each,
cost from the token usage each API reports (thinking included) x the official list price.

  pip install requests
  export GEMINI_API_KEY=...      (Google AI Studio, paid tier: Neon has no free tier)
  export ANTHROPIC_API_KEY=...
  python cost_test.py --prompt my_job.txt --runs 3
  python cost_test.py --prompt example_job.txt --models gemini-4-neon,claude-sonnet-5-5,claude-opus-5-5
  python cost_test.py --selftest          (checks the cost math offline, no keys needed)

Prices: USD per 1M tokens (input, output), standard tier, checked 22.11.2026 on
https://aistudio.google.com/docs/pricing and https://platform.claude.com/docs/en/about-claude/pricing .
Prices change (Gemini 4 Carbon goes from $2/$10 to $4/$20 on 1 Dec 2026), so check them before you trust the totals.
"""
import argparse, os, sys, time

PRICES = {
    'gemini-4-neon': (3.00, 15.00),          # output price includes thinking tokens
    'gemini-4-carbon': (2.00, 10.00),        # until 30 Nov 2026; (4.00, 20.00) from 1 Dec 2026
    'gemini-4-hydrogen': (1.50, 7.50),
    'claude-fable-5-2': (8.00, 40.00),
    'claude-opus-5-5': (4.00, 20.00),
    'claude-sonnet-5-5': (2.00, 10.00),
}


def cost(model, tokens_in, tokens_out):
    p_in, p_out = PRICES[model]
    return tokens_in * p_in / 1e6 + tokens_out * p_out / 1e6


def gemini_usage(resp):
    """-> (answer text, input tokens, billed output tokens, thinking tokens). Thinking is billed as output."""
    u = resp['usageMetadata']
    think = u.get('thoughtsTokenCount', 0)
    parts = resp['candidates'][0]['content'].get('parts', [])
    text = ''.join(p.get('text', '') for p in parts if not p.get('thought'))
    return text, u['promptTokenCount'], u.get('candidatesTokenCount', 0) + think, think


def claude_usage(resp):
    """-> (answer text, input tokens, billed output tokens, thinking tokens or None). Claude's output_tokens already include thinking."""
    u = resp['usage']
    text = ''.join(b.get('text', '') for b in resp['content'] if b.get('type') == 'text')
    return text, u['input_tokens'], u['output_tokens'], None


def call(session, model, prompt):
    import requests  # noqa: F401  (only needed for real runs)
    for attempt in range(6):
        if model.startswith('gemini'):
            r = session.post(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
                             headers={'x-goog-api-key': os.environ['GEMINI_API_KEY']},
                             json={'contents': [{'role': 'user', 'parts': [{'text': prompt}]}]}, timeout=600)
        else:
            r = session.post('https://api.anthropic.com/v1/messages',
                             headers={'x-api-key': os.environ['ANTHROPIC_API_KEY'], 'anthropic-version': '2023-06-01'},
                             json={'model': model, 'max_tokens': 16000, 'messages': [{'role': 'user', 'content': prompt}]}, timeout=600)
        if r.status_code in (429, 503, 529):   # busy: wait and retry
            time.sleep(10 * (attempt + 1)); continue
        if not r.ok:
            sys.exit(f'{model}: HTTP {r.status_code} {r.text[:300]}')
        return (gemini_usage if model.startswith('gemini') else claude_usage)(r.json())
    sys.exit(f'{model}: still busy after 6 tries, try again later')


def selftest():
    g = {'usageMetadata': {'promptTokenCount': 2000, 'candidatesTokenCount': 300, 'thoughtsTokenCount': 1700},
         'candidates': [{'content': {'parts': [{'text': 'hidden', 'thought': True}, {'text': 'answer'}]}}]}
    text, tin, tout, think = gemini_usage(g)
    assert (text, tin, tout, think) == ('answer', 2000, 2000, 1700)
    assert abs(cost('gemini-4-neon', tin, tout) - (2000 * 3 + 2000 * 15) / 1e6) < 1e-12   # $0.036
    c = {'usage': {'input_tokens': 2000, 'output_tokens': 300}, 'content': [{'type': 'text', 'text': 'answer'}]}
    text, tin, tout, _ = claude_usage(c)
    assert (text, tin, tout) == ('answer', 2000, 300)
    assert abs(cost('claude-sonnet-5-5', tin, tout) - (2000 * 2 + 300 * 10) / 1e6) < 1e-12   # $0.007
    print('selftest ok (made-up sample usage, not a real measurement): cost math and thinking-token handling work')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--prompt', help='text file with the job (the same prompt goes to every model)')
    ap.add_argument('--models', default='gemini-4-neon,claude-sonnet-5-5')
    ap.add_argument('--runs', type=int, default=3)
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.prompt:
        ap.error('--prompt is required')
    import requests
    prompt, s, rows = open(a.prompt, encoding='utf-8').read(), requests.Session(), []
    for m in a.models.split(','):
        if m not in PRICES:
            sys.exit(f'unknown model {m}; add its price to PRICES')
        for k in range(a.runs):
            t = time.time(); text, tin, tout, think = call(s, m, prompt)
            rows.append((m, time.time() - t, tin, tout, think, cost(m, tin, tout)))
            print(f'{m} run {k + 1}: {tin} in, {tout} out' + (f' (of which {think} thinking)' if think else '') + f', ${rows[-1][5]:.4f}, {rows[-1][1]:.0f}s', flush=True)
    print('\nAverage cost of ONE job:')
    for m in a.models.split(','):
        r = [x for x in rows if x[0] == m]
        print(f'  {m:20} ${sum(x[5] for x in r) / len(r):.4f}   ({sum(x[1] for x in r) / len(r):.0f}s)')


if __name__ == '__main__':
    main()
