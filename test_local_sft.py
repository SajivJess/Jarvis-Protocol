"""Local SFT Inference Test — Validate Harish's adapter against the Jarvis Arena.

Tests whether the SFT-trained model produces correctly formatted output
that passes Gate 1 (format) and Gate 2 (syntax/liveness) of the Arena.

Usage:
    python test_local_sft.py

Requirements:
    - unsloth installed (pip install unsloth)
    - CUDA GPU with ~6GB+ VRAM (4-bit quantized 7B model)
    - qwen_security_model/ folder in the same directory (Harish's adapter)
    - Express app dependencies installed (npm install in express_app/)
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from env import JarvisEnv


def run_local_inference():
    print("=" * 60)
    print("  JARVIS PROTOCOL — LOCAL SFT INFERENCE TEST")
    print("=" * 60)

    # ── Step 1: Load Model ────────────────────────────────────
    print("\n[SYSTEM] Loading Qwen Base + Harish's SFT Adapter...")
    load_start = time.time()

    from unsloth import FastLanguageModel

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="unsloth/Qwen2.5-7B-Coder-Instruct-bnb-4bit",
        peft_model="./qwen_security_model",  # Harish's adapter
        load_in_4bit=True,
    )

    # Enable native 2x faster inference
    FastLanguageModel.for_inference(model)
    load_time = time.time() - load_start
    print(f"[SYSTEM] Model loaded in {load_time:.1f}s")

    # ── Step 2: Boot Arena ────────────────────────────────────
    print("\n[SYSTEM] Booting Jarvis Arena...")
    env = JarvisEnv(
        app_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), "express_app")
    )

    results = []

    for episode in range(3):
        print(f"\n{'─' * 60}")
        print(f"  EPISODE {episode + 1}/3")
        print(f"{'─' * 60}")

        observation = env.reset()
        print(f"[ARENA] Vulnerability: {observation.vuln_type}")
        print(f"[ARENA] Route: {observation.route_path}")

        # ── Step 3: Build Prompt ──────────────────────────────
        system_prompt = (
            "You are Jarvis, an autonomous security remediation agent. "
            "You must output your reasoning inside <reasoning> tags and "
            "the exact Javascript patch inside <patch> tags. "
            "Do not include any other text."
        )

        user_prompt = (
            f"System Alert [High Severity]: Anomalous activity detected. "
            f"Analyze the motive and output a secure patch for this Express controller:\n\n"
            f"{observation.vulnerable_code}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        inputs = tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
        ).to("cuda")

        # ── Step 4: Generate ──────────────────────────────────
        print(f"[MODEL] Generating response...")
        gen_start = time.time()

        outputs = model.generate(
            input_ids=inputs,
            max_new_tokens=512,
            use_cache=True,
        )

        agent_output = tokenizer.batch_decode(
            outputs[:, inputs.shape[1]:],
            skip_special_tokens=True,
        )[0]

        gen_time = time.time() - gen_start
        print(f"[MODEL] Generated in {gen_time:.1f}s ({len(agent_output)} chars)")

        # Show output
        print(f"\n--- JARVIS SFT OUTPUT ---")
        if len(agent_output) > 600:
            print(agent_output[:300])
            print("... [truncated] ...")
            print(agent_output[-300:])
        else:
            print(agent_output)
        print("-------------------------\n")

        # ── Step 5: Evaluate ──────────────────────────────────
        print("[ARENA] Pushing patch to OpenEnv...")
        reward, done, info = env.step(agent_output)

        print(f"\n[ARENA RESULTS]")
        print(f"  Total Reward: {reward}")
        print(f"  Gate Reached: {info['gate_reached']}")
        for gate in info['gates']:
            status = "✓ PASS" if gate['passed'] else "✗ FAIL"
            print(f"  Gate {gate['gate']}: [{status}] (Reward: {gate['reward']}) — {gate['detail']}")

        results.append({
            "episode": episode + 1,
            "vuln_type": observation.vuln_type,
            "reward": reward,
            "gate_reached": info["gate_reached"],
            "gen_time": gen_time,
        })

        time.sleep(1)

    # ── Summary ───────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print("  LOCAL SFT TEST SUMMARY")
    print(f"{'=' * 60}")

    for r in results:
        if r["gate_reached"] >= 2:
            emoji = "🟢" if r["reward"] >= 1.0 else "🟡" if r["reward"] > 0 else "🟠"
        else:
            emoji = "🔴"
        print(f"  {emoji} Episode {r['episode']}: {r['vuln_type']} → "
              f"Reward: {r['reward']:.2f} (Gate {r['gate_reached']}, {r['gen_time']:.1f}s)")

    gate1_pass = sum(1 for r in results if r["gate_reached"] >= 1 and r["reward"] != -0.5)
    gate2_pass = sum(1 for r in results if r["gate_reached"] >= 2 and r["reward"] != -1.0)

    print(f"\n  Format Adherence (Gate 1): {gate1_pass}/{len(results)}")
    print(f"  Syntax Survival (Gate 2):  {gate2_pass}/{len(results)}")
    print(f"  Average Reward: {sum(r['reward'] for r in results) / len(results):.2f}")

    if gate1_pass == len(results) and gate2_pass == len(results):
        print("\n  ✅ SFT PHASE CONFIRMED — Model produces valid format + compilable code")
        print("  → Ready for GRPO reinforcement learning phase")
    elif gate1_pass == len(results):
        print("\n  ⚠️  Format OK but syntax issues — check the generated code for import errors")
    else:
        print("\n  ❌ Format issues detected — Mahaa's dataset may need adjustment")

    env._stop_server()
    print("\n[SYSTEM] Arena shutdown. Test complete.")


if __name__ == "__main__":
    run_local_inference()
