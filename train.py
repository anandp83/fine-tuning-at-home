#!/usr/bin/env python3
"""Fine-tune a small open model on one training's corpus. QLoRA, one GPU.

    pip install -r requirements.txt
    python3 build_corpus.py rhyming-field-notes    # writes its data/
    python3 train.py rhyming-field-notes           # writes its out/adapter

    BASE_MODEL=Qwen/Qwen3-1.7B python3 train.py rhyming-field-notes   # smaller track

Roughly 11 GB of VRAM on the 8B model and 6 GB on the 1.7B, and a few minutes either way.
The base weights are frozen and quantized to 4 bits; only a small adapter is trained, and
that adapter is what lands in <training>/out/adapter.

The four settings that matter are marked MATTERS below. They trade against each other:
raising the rank and the epoch count together is how a small corpus gets memorized.

Three things are checked before training starts, because each of them fails silently:
a CPU-only torch, a sequence length that would truncate your longest example, and an
adapter attached to no layers. Each costs a run, and none of them reports an error.
"""
import os
import sys
from pathlib import Path

import torch
from datasets import load_dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import SFTConfig, SFTTrainer

# The scripts are generic and live at the root; a training is a folder holding its own
# corpus, prompts, data and config. Naming it is the only argument.
ROOT = Path(__file__).resolve().parent

MAX_LENGTH = 1024           # MATTERS: must clear the longest example. Checked below.


def training_dir(arg=None):
    if arg:
        for d in (Path(arg), ROOT / arg):
            if (d / "corpus").is_dir():
                return d.resolve()
        raise SystemExit(f"no corpus/ directory in {arg} or {ROOT / arg}")
    found = sorted(p for p in ROOT.iterdir() if (p / "corpus").is_dir())
    if len(found) == 1:
        return found[0]
    raise SystemExit("Name the training to run, for example:\n"
                     "    python3 train.py rhyming-field-notes")


TRAINING = training_dir(sys.argv[1] if len(sys.argv) > 1 else None)
BASE_MODEL = os.environ.get("BASE_MODEL", "Qwen/Qwen3-8B")
DATA = os.environ.get("DATA", str(TRAINING / "data" / "train.jsonl"))
OUT = os.environ.get("OUT", str(TRAINING / "out" / "adapter"))

# Pin the run to one card. On a multi-GPU box this is what stops a mistyped setting starting
# a distributed run, which does not fail, it just takes twenty times longer. Set before the
# first CUDA call below, which is where torch reads it.
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")

if not torch.cuda.is_available():
    raise SystemExit(
        "No CUDA device visible. This will not train usefully on a CPU: it will appear to "
        "work and take days. Check the driver, then `python3 -c \"import torch; "
        "print(torch.cuda.is_available())\"`. If that prints False, pip probably resolved a "
        "CPU build: pip install torch --index-url https://download.pytorch.org/whl/cu124"
    )

if not Path(DATA).is_file():
    raise SystemExit(f"no training data at {DATA}\n"
                     f"    python3 build_corpus.py {TRAINING.name}")

print(f"training   : {TRAINING.name}")
print(f"base model : {BASE_MODEL}")
print(f"data       : {DATA}")
print(f"device     : {torch.cuda.get_device_name(0)}")

# QLoRA: the frozen base is stored at 4 bits, which is what brings an 8B model onto a
# 24 GB card with room for the activations. The adapter itself stays at full precision,
# because it is the part being trained.
quant = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
if tokenizer.chat_template is None:
    raise SystemExit(
        f"{BASE_MODEL} ships no chat template, so the turn markers the model was trained "
        "to recognize cannot be applied."
    )

dataset = load_dataset("json", data_files=DATA, split="train")

# Measure the longest example before training rather than after. A sequence length below it
# truncates from the end, silently, and for a form that closes on its most important stanza
# that means training the model to stop before it makes its point. Thirty seconds here
# against a run you would otherwise throw away.
lengths = [len(tokenizer.apply_chat_template(row["messages"], tokenize=True))
           for row in dataset]
longest = max(lengths)
print(f"examples   : {len(dataset)}, longest {longest} tokens, max_length {MAX_LENGTH}")
if longest > MAX_LENGTH:
    raise SystemExit(
        f"the longest example is {longest} tokens and max_length is {MAX_LENGTH}, so it "
        f"would be cut off.\nRaise MAX_LENGTH to at least {longest} (more memory), or "
        "shorten that example."
    )

model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    quantization_config=quant,
    dtype=torch.bfloat16,
    device_map={"": 0},
)
model.config.use_cache = False

# Low-rank adaptation. Instead of updating all 8 billion parameters, freeze them and learn
# two small matrices beside each weight table. r=16 trains well under 1% of the model.
peft_config = LoraConfig(
    r=16,                       # MATTERS: adapter capacity. Higher memorizes sooner.
    lora_alpha=32,
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules="all-linear",
)

config = SFTConfig(
    output_dir=OUT,
    num_train_epochs=15,        # MATTERS: passes over very few examples.
    learning_rate=1e-4,         # MATTERS: step size. Roughly 10x a full fine-tune's.
    save_strategy="epoch",      # MATTERS: keep every pass, so you can go back to the best.
    lr_scheduler_type="cosine",
    warmup_ratio=0.1,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=4,
    max_length=MAX_LENGTH,
    gradient_checkpointing=True,
    bf16=True,
    optim="paged_adamw_8bit",
    logging_steps=1,
    report_to="none",
    # Train on the response only, so the model does not learn to generate prompts as well
    # as answers. This relies on the tokenizer's chat template marking the assistant turn;
    # if your version of TRL or the template rejects it, drop this line. Loss then covers
    # the whole conversation, which at this corpus size is a small effect but not nothing.
    assistant_only_loss=True,
)

trainer = SFTTrainer(
    model=model,
    args=config,
    train_dataset=dataset,
    peft_config=peft_config,
    processing_class=tokenizer,
)

# What is actually going to be trained. A target_modules that matches nothing produces a
# run that completes, writes checkpoints and reports a falling loss while changing no
# weights at all, and this is the only place that failure is visible before it wastes the
# run rather than after.
trainable = sum(p.numel() for p in trainer.model.parameters() if p.requires_grad)
total = sum(p.numel() for p in trainer.model.parameters())
print(f"trainable  : {trainable:,} of {total:,} parameters ({100 * trainable / total:.3f}%)")
if trainable == 0:
    raise SystemExit(
        "the adapter attached to no layers, so this run would train nothing while looking "
        "like it worked. Check target_modules in the LoraConfig above."
    )

steps = len(dataset) * config.num_train_epochs / config.gradient_accumulation_steps
print(f"plan       : {len(dataset)} examples x {config.num_train_epochs:g} epochs "
      f"-> about {steps:.0f} optimizer steps\n")

result = trainer.train()
trainer.save_model(OUT)
tokenizer.save_pretrained(OUT)

# The first logged loss beside the last one. Not the average the trainer returns: on a run
# that trained nothing every step reports the same number, and an average hides that by
# looking like a plausible loss.
losses = [e["loss"] for e in trainer.state.log_history if "loss" in e]
print(f"\nadapter    : {OUT}")
if len(losses) >= 2:
    print(f"loss       : {losses[0]:.4f} -> {losses[-1]:.4f}  (mean {result.training_loss:.4f})")
    if abs(losses[0] - losses[-1]) < 1e-4:
        print("\nThose two are the same to four decimal places, which means nothing trained.")
else:
    print(f"loss       : mean {result.training_loss:.4f}")
print(f"\nNext:  python3 generate.py {TRAINING.name} \"your prompt here\"")
