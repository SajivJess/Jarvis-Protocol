"""Groq Dry-Run Script — Zero-Shot Baseline for Jarvis Protocol Arena.

Tests the full OpenEnv pipeline end-to-end using Groq's fast inference
to validate the OutputParser, reward waterfall, and Express hot-reload
before committing to hours of GRPO training.

Usage:
    pip install groq
    python test_groq.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from groq import Groq
from env import JarvisEnv

# ── API Key Rotation ──────────────────────────────────────────────────

GROQ_API_KEYS = [
    os.environ.get("GROQ_API_KEY_1", ""),
    os.environ.get("GROQ_API_KEY_2", ""),
    os.environ.get("GROQ_API_KEY_3", ""),
    os.environ.get("GROQ_API_KEY_4", ""),
    os.environ.get("GROQ_API_KEY_5", ""),
]

current_key_index = 0


def get_groq_client():
    """Get a Groq client with the current API key."""
    global current_key_index
    return Groq(api_key=GROQ_API_KEYS[current_key_index])


def rotate_key():
    """Rotate to the next API key. Returns False if all keys exhausted."""
    global current_key_index
    current_key_index += 1
    if current_key_index >= len(GROQ_API_KEYS):
        return False
    print(f"[SYSTEM] Rotating to API key {current_key_index + 1}/{len(GROQ_API_KEYS)}")
    return True


def call_groq(system_prompt, user_prompt, model="llama-3.1-8b-instant"):
    """Call Groq API with automatic key rotation on rate limit or exhaustion."""
    while True:
        try:
            client = get_groq_client()
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=1024,
            )
            return completion.choices[0].message.content
        except Exception as e:
            error_str = str(e).lower()
            if "rate_limit" in error_str or "429" in error_str or "exhausted" in error_str:
                print(f"[SYSTEM] Key {current_key_index + 1} rate limited: {e}")
                if not rotate_key():
                    print("[SYSTEM] All API keys exhausted!")
                    raise
                time.sleep(1)
            else:
                raise


# ── System Prompt ─────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Jarvis, an autonomous security remediation agent.
You will receive a vulnerable Express.js route handler. Your job is to rewrite
the handler function to fix the vulnerability while preserving all legitimate
functionality.

You MUST output your response in this EXACT format:

<reasoning>
Explain the vulnerability and your fix strategy here.
</reasoning>
<patch>
// Your fixed handler code here — just the module.exports function
module.exports = function(req, res) {
    // ... fixed implementation
};
</patch>

CRITICAL RULES:
- Output ONLY the <reasoning> and <patch> tags. No other text.
- The <patch> must contain ONLY valid JavaScript code.
- Do NOT wrap the code in markdown code blocks inside the <patch> tags.
- The patch must export a single function via module.exports.
- The function must preserve the original route's legitimate behavior.
"""


def build_user_prompt(observation):
    """Build the user prompt from an Observation."""
    return f"""SYSTEM ALERT: Fix the following vulnerability.

Vulnerability Type: {observation.vuln_type}
Route: {observation.route_path}
Description: {observation.description}

Vulnerable Code:
{observation.vulnerable_code}

Rewrite the handler to fix this vulnerability. Preserve all legitimate functionality."""


# ── Main Test Loop ────────────────────────────────────────────────────

def test_jarvis_loop(num_episodes=3):
    """Run the full Jarvis Arena loop with Groq inference."""
    print("=" * 60)
    print("  JARVIS PROTOCOL — GROQ DRY RUN (Zero-Shot Baseline)")
    print("=" * 60)

    env = JarvisEnv(
        app_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), "express_app")
    )

    results = []

    for episode in range(num_episodes):
        print(f"\n{'─' * 60}")
        print(f"  EPISODE {episode + 1}/{num_episodes}")
        print(f"{'─' * 60}")

        # Reset environment
        observation = env.reset()
        print(f"[ARENA] Vulnerability: {observation.vuln_type}")
        print(f"[ARENA] Route: {observation.route_path}")

        # Build prompt
        user_prompt = build_user_prompt(observation)

        # Call Groq
        print(f"[GROQ] Calling Llama-3-8b (key {current_key_index + 1})...")
        start_time = time.time()
        agent_output = call_groq(SYSTEM_PROMPT, user_prompt)
        inference_time = time.time() - start_time
        print(f"[GROQ] Response received in {inference_time:.2f}s")

        # Show the raw output
        print(f"\n--- GROQ OUTPUT ({len(agent_output)} chars) ---")
        # Truncate for display if very long
        if len(agent_output) > 800:
            print(agent_output[:400])
            print("... [truncated] ...")
            print(agent_output[-400:])
        else:
            print(agent_output)
        print("-------------------\n")

        # Step the environment
        print("[ARENA] Pushing patch to OpenEnv...")
        reward, done, info = env.step(agent_output)

        # Display results
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
            "inference_time": inference_time,
        })

        # Brief pause between episodes to avoid rate limits
        if episode < num_episodes - 1:
            time.sleep(2)

    # Summary
    print(f"\n{'=' * 60}")
    print("  DRY RUN SUMMARY")
    print(f"{'=' * 60}")
    for r in results:
        emoji = "🟢" if r["reward"] >= 1.0 else "🟡" if r["reward"] > 0 else "🔴"
        print(f"  {emoji} Episode {r['episode']}: {r['vuln_type']} → Reward: {r['reward']:.2f} "
              f"(Gate {r['gate_reached']}, {r['inference_time']:.1f}s)")

    avg_reward = sum(r["reward"] for r in results) / len(results)
    print(f"\n  Average Reward: {avg_reward:.2f}")
    print(f"  Perfect Patches: {sum(1 for r in results if r['reward'] >= 1.0)}/{len(results)}")

    # Cleanup
    env._stop_server()
    print("\n[SYSTEM] Arena shutdown. Dry run complete.")


if __name__ == "__main__":
    test_jarvis_loop(num_episodes=3)
