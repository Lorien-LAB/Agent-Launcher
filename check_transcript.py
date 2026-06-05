import json, os

sdir = os.path.expanduser("~/.claude/sessions")
pdir = os.path.expanduser("~/.claude/projects")

for fn in os.listdir(sdir):
    if not fn.endswith(".json"):
        continue
    with open(os.path.join(sdir, fn)) as f:
        s = json.load(f)
    sid = s["sessionId"]
    cwd = s["cwd"]
    proj = cwd.replace(":", "").replace("\\", "--").replace(" ", "-").replace("_", "-")
    tpath = os.path.join(pdir, proj, f"{sid}.jsonl")
    if not os.path.exists(tpath):
        for f2 in os.listdir(os.path.join(pdir, proj)):
            if f2.endswith(".jsonl"):
                tpath = os.path.join(pdir, proj, f2)
                break

    if not os.path.exists(tpath):
        print(f"{sid[:8]}: NO TRANSCRIPT")
        continue

    # Count ALL assistant lines, accumulate tokens
    count = 0
    total_in = 0
    total_out = 0
    model = "?"
    last_in = 0
    last_sys = None
    with open(tpath, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except:
                continue
            if obj.get("type") == "assistant":
                count += 1
                u = obj.get("message", {}).get("usage", {})
                last_in = u.get("input_tokens", 0)
                total_out += u.get("output_tokens", 0)
                m = obj.get("message", {}).get("model", "")
                if m:
                    model = m
            # Check for system messages with cumulative data
            if obj.get("type") == "system":
                last_sys = obj

    print(f"{sid[:8]} [{model}] assistant_lines={count} last_input={last_in} total_output={total_out}")
    if last_sys:
        print(f"  last system msg: {json.dumps(last_sys, indent=2)[:200]}")

    print()
