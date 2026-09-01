# Fine-Tuning at Home

Train a small open model to write in a specific voice. Fourteen poems, three scripts, one GPU.

A full write-up of the reasoning is at
<https://anandpatel.com/series/fine-tuning-at-home>. Everything needed to run it is here.

## Requirements

| | |
|---|---|
| GPU | **NVIDIA only.** The stack is CUDA. ~11 GB VRAM for Qwen3-8B, ~6 GB for Qwen3-1.7B |
| Disk | ~60 GB free. Mostly the model weights and the CUDA wheels, not the data |
| RAM | 32 GB comfortable, 16 GB workable on the smaller model |
| Python | 3.10 or newer |

`build_corpus.py` needs none of this. Only training does.

## Quick start

```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python3 build_corpus.py rhyming-field-notes    # poems  -> data/*.jsonl
python3 train.py        rhyming-field-notes    # data   -> out/adapter
python3 generate.py     rhyming-field-notes "Write a field note about a disk that filled up."
```

## What you will probably have to change

Read this before the first run. None of it is exotic, and all of it bites.

**Your GPU is smaller than 24 GB.** Use the smaller model. Nothing else changes:

```
BASE_MODEL=Qwen/Qwen3-1.7B python3 train.py rhyming-field-notes
```

**pip installed a CPU build of torch.** This is the most common failure and it does not
announce itself: training appears to start and runs about a thousand times slower. Check
first, and install the CUDA build explicitly if it is wrong:

```
python3 -c "import torch; print(torch.cuda.is_available())"     # must print True
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

Match `cu124` to your driver. `nvidia-smi` prints the CUDA version it supports.

**You have more than one GPU.** The scripts pin themselves to device 0. To use a different
card, set it before running, because a mistyped distributed run does not fail, it just
takes twenty times longer:

```
CUDA_VISIBLE_DEVICES=1 python3 train.py rhyming-field-notes
```

**It runs out of memory.** Lower these in `train.py`, in this order: `MAX_LENGTH` from
1024 to 768, then `r` from 16 to 8. Confirm `gradient_checkpointing=True`. The batch
size is already 1.

**`assistant_only_loss` is rejected.** Some versions of TRL or some chat templates will not
accept it. Delete the line. Loss then covers the prompt as well as the response, which at
this corpus size is a small effect but not nothing.

**You are using the Axolotl config instead.** `rhyming-field-notes/config.yml` names
`Qwen/Qwen3-8B` and a dataset path relative to the repository root. If you run it from
elsewhere, fix both.

**The model is gated on Hugging Face.** Qwen3 is not, but if you swap in one that is, log
in first with `hf auth login`.

## The scripts

Three files at the root. They are generic: each takes a training folder as its argument and
works on any corpus laid out the same way.

**`build_corpus.py`** turns `corpus/*.md` into `data/train.jsonl` and `data/holdout.jsonl`.
Standard library only, no GPU. It pairs each poem with the instruction named in `prompts.json`, strips
the markdown heading so the model does not learn to emit titles, and routes the six
named in the holdout list away from the training set. The instructions deliberately never mention rhyme or verse: if the prompt
asks for a rhyming poem, the model learns to rhyme *when asked*, which it could already do.
The voice has to come from the weights.

**`train.py`** is the fine-tune. It loads the base model quantized to 4 bits, freezes it,
attaches a LoRA adapter to every linear layer, and trains only the adapter. Four settings
matter and are marked `MATTERS` in the file:

| | |
|---|---|
| `r` | adapter capacity. Higher memorizes sooner |
| `num_train_epochs` | passes over very few examples. The one most likely to need changing |
| `learning_rate` | roughly 10x what a full fine-tune would use |
| `save_strategy` | writes a checkpoint per pass, so you can go back to the best one |

It prints the first loss beside the last. **If those match to several decimal places,
nothing trained** - the adapter attached to nothing. That failure writes checkpoints and
exits zero, so this is the only thing that reveals it.

**`generate.py`** loads the base model, puts the adapter on top, and generates. `--base`
skips the adapter so you can compare against the untrained model, and `--adapter` points at
a specific checkpoint. Temperature and seed are arguments with defaults so they can be held
identical across runs; comparing two models at different sampling settings compares nothing.

## Layout

A training is a folder holding its own corpus, generated data and config, so a second voice
or a second base model is a sibling rather than a rename of everything.

```
build_corpus.py  train.py  generate.py     work on any training
requirements.txt

rhyming-field-notes/
  corpus/        the fourteen poems, the only handwritten input
  prompts.json   the instruction for each poem, which are held back, the system line
  data/          train.jsonl and holdout.jsonl, generated
  config.yml     the same run as an Axolotl config, if you prefer one
```

Run the scripts bare and they will find the training while there is only one.

## The corpus

Fourteen short technical field notes, about three hundred words each, written entirely in
rhyming couplets by a writer who does not exist. Every word was invented to be trained on;
none of the incidents happened to anybody.

A rhyming voice makes the result checkable. Train on a subtle writer and the evaluation
becomes an argument about whether the output feels different. Train on one who rhymes and
that question answers itself, which leaves room for the ones that matter: how much data,
how many passes, and what the model picked up that nobody asked it to.

**Six of the fourteen are held back.** `05` and `10` through `14` never enter
`train.jsonl`. With eight examples a model can memorize, and memorized output looks like
style transfer unless you have unseen subjects to test against. Six rather than two because
eight training examples saturate a form this consistent while two test subjects saturate
nothing, and a fluke on either one is half the evidence.

## Results will not reproduce exactly

Sampling is stochastic, adapter weights start random, and GPU arithmetic is not
bit-identical across cards and driver versions. Two runs of your own will differ from each
other. What should hold is the shape of the result, not the text.
