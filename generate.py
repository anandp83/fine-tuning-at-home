#!/usr/bin/env python3
"""Generate from the fine-tuned model, and from the untouched one, for comparison.

    python3 generate.py "Write a field note about monitoring that failed silently."
    python3 generate.py rhyming-field-notes "Write a field note about ..."

    --base            generate from the base model instead, with no adapter
    --adapter DIR     use a specific checkpoint rather than <training>/out/adapter
    --temperature F   default 0.8
    --seed N          default 0

With one training folder present the folder can be left off. Both runs use the same
temperature and the same seed, which is the only way the comparison means anything:
sampling settings live outside the model and change its character more than most people
expect. Comparing at different settings compares nothing.
"""
import argparse
import json
import os
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, set_seed

ROOT = Path(__file__).resolve().parent
BASE_MODEL = os.environ.get("BASE_MODEL", "Qwen/Qwen3-8B")
DEFAULT_PROMPT = "Write a field note about monitoring that failed silently."

parser = argparse.ArgumentParser(
    description="Generate from a fine-tuned model, or from the base model for comparison.")
parser.add_argument("args", nargs="*", metavar="[training] prompt",
                    help="the training folder, the prompt, or just the prompt")
parser.add_argument("--base", action="store_true", help="no adapter, for comparison")
parser.add_argument("--adapter", default=None, help="a specific checkpoint directory")
parser.add_argument("--temperature", type=float, default=0.8)
parser.add_argument("--seed", type=int, default=0)
parser.add_argument("--max-new-tokens", type=int, default=600)
args = parser.parse_args()


def training_dir(arg=None):
    if arg:
        for d in (Path(arg), ROOT / arg):
            if (d / "corpus").is_dir():
                return d.resolve()
        raise SystemExit(f"no corpus/ directory in {arg} or {ROOT / arg}")
    found = sorted(p for p in ROOT.iterdir() if (p / "corpus").is_dir())
    if len(found) == 1:
        return found[0]
    raise SystemExit("Name the training, for example:\n"
                     "    python3 generate.py rhyming-field-notes \"your prompt\"")


# A training folder is a directory that exists; anything else is the prompt. That way the
# folder can be left off entirely when there is only one.
positional = list(args.args)
named = None
if positional and (Path(positional[0]).is_dir() or (ROOT / positional[0]).is_dir()):
    named = positional.pop(0)
TRAINING = training_dir(named)
prompt = " ".join(positional) if positional else DEFAULT_PROMPT

# The same system line the examples were built with. Training taught the model to answer
# this particular prompt shape, so evaluating it under a different one measures something
# else. Read from the training rather than repeated here, so the two cannot drift.
spec = TRAINING / "prompts.json"
SYSTEM = json.loads(spec.read_text(encoding="utf-8"))["system"] if spec.is_file() else ""

if args.adapter is None:
    args.adapter = str(TRAINING / "out" / "adapter")
if not args.base and not Path(args.adapter).is_dir():
    raise SystemExit(f"no adapter at {args.adapter}\n"
                     f"    python3 train.py {TRAINING.name}\n"
                     "or pass --base to generate from the untrained model.")

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
set_seed(args.seed)

quant = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL, quantization_config=quant, dtype=torch.bfloat16, device_map={"": 0}
)
if not args.base:
    model = PeftModel.from_pretrained(model, args.adapter)
model.eval()

messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]
inputs = tokenizer.apply_chat_template(
    messages, add_generation_prompt=True, return_tensors="pt", return_dict=True
).to(model.device)

with torch.no_grad():
    out = model.generate(
        **inputs,
        max_new_tokens=args.max_new_tokens,
        do_sample=True,
        temperature=args.temperature,
        top_p=0.9,
        pad_token_id=tokenizer.eos_token_id,
    )

# The header says what produced the text. Reading twenty of these later and being unable to
# say which came from where is how an evaluation quietly turns into an opinion.
new = out[0][inputs["input_ids"].shape[-1]:]
finished = "stop" if new[-1].item() == tokenizer.eos_token_id else f"length ({args.max_new_tokens})"
print(f"# {'base model' if args.base else args.adapter}")
print(f"# temperature {args.temperature}, seed {args.seed}, {len(new)} tokens, ended on {finished}\n")
print(tokenizer.decode(new, skip_special_tokens=True))
