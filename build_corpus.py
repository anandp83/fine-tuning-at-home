#!/usr/bin/env python3
"""Build the training data for one training: poems in, two JSONL files out.

    python3 build_corpus.py rhyming-field-notes

Reads <training>/corpus/*.md and <training>/prompts.json, and writes
<training>/data/train.jsonl and holdout.jsonl.
With one training folder present it can be run bare and will find it.

Standard library only. No GPU, no model, nothing to install.
"""
import json
import re
import sys
from pathlib import Path

# Which training to build. The scripts are generic and live at the root; a training is a
# folder holding its own corpus, its prompts, its data and its config. Naming it is the
# only argument.
ROOT = Path(__file__).resolve().parent


def training_dir(arg=None):
    """The named training, or the only one there is."""
    if arg:
        # Tried as given and then beside this script, so it works from either directory.
        for d in (Path(arg), ROOT / arg):
            if (d / "corpus").is_dir():
                return d.resolve()
        raise SystemExit(f"no corpus/ directory in {arg} or {ROOT / arg}")
    found = sorted(p for p in ROOT.iterdir() if (p / "corpus").is_dir())
    if len(found) == 1:
        return found[0]
    raise SystemExit(
        "Name the training to build, for example:\n"
        "    python3 build_corpus.py rhyming-field-notes\n"
        f"Found {len(found)} training folders beside this script."
    )


BASE = training_dir(sys.argv[1] if len(sys.argv) > 1 else None)
POEMS, DATA = BASE / "corpus", BASE / "data"
print(f"training : {BASE.name}")

# The instruction side, the holdout and the system line live with the training rather than
# in this script, because they are facts about one corpus and this file works on any of
# them. None of the instructions mentions rhyme or verse: an instruction that asks for a
# rhyming poem teaches the model to rhyme when asked, which it could already do.
SPEC = BASE / "prompts.json"
if not SPEC.is_file():
    raise SystemExit(
        f"no prompts.json in {BASE}. It names the instruction for each poem, which two are\n"
        "held back, and the system line. See rhyming-field-notes/prompts.json for the shape."
    )
spec = json.loads(SPEC.read_text(encoding="utf-8"))
for field in ("system", "holdout", "prompts"):
    if field not in spec:
        raise SystemExit(f"{SPEC} has no \"{field}\" field")
SYSTEM, HOLDOUT, PROMPTS = spec["system"], set(spec["holdout"]), spec["prompts"]

files = sorted(p for p in POEMS.iterdir() if re.fullmatch(r"\d\d-.*\.md", p.name))
if not files:
    raise SystemExit(f"no NN-name.md files in {POEMS}")

# Every poem needs an instruction and every instruction needs a poem. Reported together so
# one run tells you everything to fix, rather than one missing key at a time.
keys = [p.name[:2] for p in files]
missing = [k for k in keys if k not in PROMPTS]
unused = [k for k in PROMPTS if k not in keys]
stray = [k for k in HOLDOUT if k not in keys]
if missing or unused or stray:
    if missing:
        raise SystemExit(f"no prompt in {SPEC.name} for: {', '.join(missing)}")
    if stray:
        raise SystemExit(f"holdout names a poem that is not in the corpus: {', '.join(stray)}")
    raise SystemExit(f"{SPEC.name} has prompts for poems that do not exist: {', '.join(unused)}")

train, holdout = [], []

for path in files:
    key = path.name[:2]

    # Drop the markdown heading: leaving it in teaches the model that a title is part of
    # the voice, and it then appears in everything the model generates.
    body = re.sub(r"\A#[^\n]*\n+", "", path.read_text(encoding="utf-8")).strip()
    if not body:
        raise SystemExit(f"{path.name} is empty once its heading is removed")

    example = {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": PROMPTS[key]},
            {"role": "assistant", "content": body},
        ]
    }
    (holdout if key in HOLDOUT else train).append(example)

if not train:
    raise SystemExit("every poem is in the holdout, so there is nothing to train on")
if not holdout:
    print("WARNING: nothing held back. With no unseen subject there is no way to tell a "
          "model that learned a voice from one that memorized the corpus.")


def write(name, rows):
    DATA.mkdir(parents=True, exist_ok=True)
    out = DATA / name
    # ensure_ascii=False keeps the text readable and compact separators keep the diffs
    # small. Neither choice matters to a trainer.
    out.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in rows) + "\n",
        encoding="utf-8",
    )
    words = sum(len(r["messages"][2]["content"].split()) for r in rows)
    print(f"{name:<14} {len(rows):>2} examples  ~{words} words")


write("train.jsonl", train)
write("holdout.jsonl", holdout)

# The longest example decides max_length in train.py, and setting that below it truncates
# the end of a piece with no warning. Words are not tokens, so this is a rough figure and
# train.py measures it properly with the tokenizer before training. It is here because
# knowing which piece is the long one is useful while you are still writing them.
longest = max(files, key=lambda p: len(p.read_text(encoding="utf-8").split()))
print(f"longest        {longest.name} at ~{len(longest.read_text(encoding='utf-8').split())} words")
print(f"held back      {', '.join(sorted(HOLDOUT)) or 'nothing'}")
