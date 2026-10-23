# data/ai_cache: recorded Meta Model API answers, committed so the demo replays offline

One JSON file per call, named by the sha256 of (kind, model, base URL, request payload), which
is what `tools\meta_client.py` computes in `request_key()`. `PP_AI_MODE=replay` reads these and
never opens a socket; a missing entry raises `CacheMiss` instead of a silent wrong answer.

Each file carries:

    key           the sha256 in the file name
    kind          chat | vision | image | edit | segment
    backend       meta | mock (the client's backend when the entry was recorded)
    model         the model id asked for
    mode          record
    recorded_at   UTC stamp
    network       true only when a real HTTP call to api.meta.ai produced the answer
    request       the payload with any inline image replaced by its sha256, so the file stays small
    response      exactly what the client returns for that call

## What is in here today (2026-10-22)

Six entries, all `backend: mock`, `network: false`, recorded with `PP_AI_BACKEND=mock
python tools\meta_client.py --record-demo`. There is no Meta API key in this environment yet
(`MODEL_API_KEY` and `META_API_KEY` are both unset), so no real Meta answer could be recorded
and none is claimed: `python tools\meta_client.py --cache-status` reports
`recorded_against_live_api: 0`, and the tests replay these entries to prove the offline path
with the network forbidden.

## How to replace them with real recordings

Once the hackathon key is in the environment, from the project root:

    set MODEL_API_KEY=...            (never write it into a file in this repo)
    python tools\meta_client.py --record-demo
    python tools\meta_client.py --cache-status     (recorded_against_live_api should be 6)
    python -m pytest tests\test_meta_client.py -q

Then commit the changed files. Keep the mock entries in the history rather than deleting them
in place: a reviewer can see exactly which answers came from the model and which were canned.
Note that the cache key includes the backend, so a mock entry is never served to a Meta call.
