"""GRPO Training Script for Jarvis Protocol.

Trains Qwen-2.5-7B-Coder to patch vulnerable Express.js code
using Group Relative Policy Optimization (GRPO) via TRL + Unsloth.

Usage:
    python train.py --model_name Qwen/Qwen2.5-7B-Coder --num_episodes 1000
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def parse_args():
    parser = argparse.ArgumentParser(description="Jarvis Protocol GRPO Training")
    parser.add_argument("--model_name", type=str, default="Qwen/Qwen2.5-7B-Coder",
                        help="HuggingFace model name")
    parser.add_argument("--lr", type=float, default=5e-6, help="Learning rate")
    parser.add_argument("--batch_size", type=int, default=4, help="Batch size")
    parser.add_argument("--num_episodes", type=int, default=1000, help="Number of training episodes")
    parser.add_argument("--max_new_tokens", type=int, default=512, help="Max tokens for generation")
    parser.add_argument("--wandb_project", type=str, default=None, help="W&B project name")
    parser.add_argument("--env_url", type=str, default=None,
                        help="Remote env URL. If None, uses local JarvisEnv")
    return parser.parse_args()


def create_env(env_url=None):
    """Create environment — local or remote."""
    if env_url:
        # Remote environment via HTTP
        import requests
        class RemoteEnv:
            def __init__(self, url):
                self.url = url.rstrip('/')
            def reset(self):
                return requests.post(f"{self.url}/reset").json()
            def step(self, agent_output):
                resp = requests.post(f"{self.url}/step",
                                     json={"agent_output": agent_output}).json()
                return resp["reward"], resp["done"], resp["info"]
        return RemoteEnv(env_url)
    else:
        from env import JarvisEnv
        return JarvisEnv(
            app_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), "express_app")
        )


def build_prompt(observation):
    """Build the prompt for the LLM from an observation."""
    if isinstance(observation, dict):
        vuln_type = observation.get("vuln_type", "Unknown")
        route_path = observation.get("route_path", "Unknown")
        code = observation.get("vulnerable_code", "")
        description = observation.get("description", "")
    else:
        vuln_type = observation.vuln_type
        route_path = observation.route_path
        code = observation.vulnerable_code
        description = observation.description

    return f"""You are a security engineer. The following Express.js route handler has a {vuln_type} vulnerability.

Route: {route_path}
Description: {description}

Vulnerable Code:
{code}

Your task: Rewrite the handler function to fix the vulnerability while preserving all legitimate functionality.

Output your response in this exact format:
<reasoning>
Explain the vulnerability and your fix strategy here.
</reasoning>
<patch>
// Your fixed handler code here
module.exports = function(req, res) {{
    // ... fixed implementation
}};
</patch>"""


def reward_function(prompts, completions, **kwargs):
    """GRPO reward function that evaluates patches via the environment.

    This function is called by TRL's GRPOTrainer during training.
    Each completion is evaluated against the environment's 4-gate waterfall.
    """
    env = kwargs.get("env")
    rewards = []

    for prompt, completion in zip(prompts, completions):
        # Reset environment for each evaluation
        obs = env.reset()

        # Step with the agent's completion
        reward, done, info = env.step(completion)
        rewards.append(reward)

        # Log gate-level details
        gate_reached = info.get("gate_reached", 0)
        print(f"  Gate reached: {gate_reached}, Reward: {reward:.2f}")

    return rewards


def main():
    args = parse_args()

    # Optional W&B logging
    if args.wandb_project:
        try:
            import wandb
            wandb.init(project=args.wandb_project, config=vars(args))
        except ImportError:
            print("[Warning] wandb not installed, skipping logging")

    print(f"[Jarvis Training] Model: {args.model_name}")
    print(f"[Jarvis Training] LR: {args.lr}, Batch: {args.batch_size}, Episodes: {args.num_episodes}")

    # Load model with Unsloth for efficiency
    try:
        from unsloth import FastLanguageModel

        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=args.model_name,
            max_seq_length=2048,
            dtype=None,  # auto-detect
            load_in_4bit=True,
        )

        model = FastLanguageModel.get_peft_model(
            model,
            r=16,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                            "gate_proj", "up_proj", "down_proj"],
            lora_alpha=16,
            lora_dropout=0,
            bias="none",
            use_gradient_checkpointing="unsloth",
        )

        print("[Jarvis Training] Model loaded with Unsloth 4-bit quantization")
    except ImportError:
        print("[Warning] Unsloth not available. Install with: pip install unsloth")
        print("[Warning] Falling back to transformers...")
        from transformers import AutoModelForCausalLM, AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(args.model_name)
        model = AutoModelForCausalLM.from_pretrained(args.model_name)

    # Create environment
    env = create_env(args.env_url)
    print("[Jarvis Training] Environment ready")

    # Build training dataset from environment observations
    # Each prompt is generated from a fresh environment reset
    train_prompts = []
    for i in range(min(args.num_episodes, 100)):  # Pre-generate prompts
        obs = env.reset()
        prompt = build_prompt(obs)
        train_prompts.append(prompt)

    print(f"[Jarvis Training] Generated {len(train_prompts)} training prompts")

    # Configure GRPO training
    try:
        from trl import GRPOConfig, GRPOTrainer

        training_args = GRPOConfig(
            output_dir="./jarvis-grpo-output",
            num_train_epochs=1,
            per_device_train_batch_size=args.batch_size,
            learning_rate=args.lr,
            max_completion_length=args.max_new_tokens,
            num_generations=4,  # Number of completions per prompt for GRPO
            logging_steps=1,
            report_to="wandb" if args.wandb_project else "none",
        )

        trainer = GRPOTrainer(
            model=model,
            args=training_args,
            tokenizer=tokenizer,
            train_dataset=train_prompts,
            reward_funcs=[lambda prompts, completions: reward_function(prompts, completions, env=env)],
        )

        print("[Jarvis Training] Starting GRPO training...")
        trainer.train()

        # Save the trained model
        model.save_pretrained("./jarvis-trained")
        tokenizer.save_pretrained("./jarvis-trained")
        print("[Jarvis Training] Model saved to ./jarvis-trained")

    except ImportError:
        print("[Warning] TRL not available. Install with: pip install trl")
        print("[Warning] Running manual evaluation loop instead...")

        # Fallback: manual evaluation loop for testing
        for i in range(min(args.num_episodes, 10)):
            obs = env.reset()
            prompt = build_prompt(obs)
            print(f"\n--- Episode {i+1} ---")
            print(f"Vulnerability: {obs.vuln_type if hasattr(obs, 'vuln_type') else obs.get('vuln_type')}")

            # Dummy agent output for testing
            dummy_output = "<reasoning>Testing the pipeline</reasoning>\n<patch>module.exports = function(req, res) { res.status(200).json({ok: true}); };</patch>"
            reward, done, info = env.step(dummy_output)

            print(f"Reward: {reward:.2f}")
            print(f"Gate reached: {info.get('gate_reached', 'N/A')}")

            if args.wandb_project:
                try:
                    import wandb
                    wandb.log({
                        "episode": i,
                        "reward": reward,
                        "gate_reached": info.get("gate_reached", 0),
                    })
                except Exception:
                    pass

    print("[Jarvis Training] Done!")


if __name__ == "__main__":
    main()
