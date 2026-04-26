"""HF Spaces Flask wrapper for Jarvis Protocol OpenEnv environment."""
import os
import sys
from flask import Flask, request, jsonify

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from env import JarvisEnv, Observation
from dataclasses import asdict

app = Flask(__name__)

# Singleton environment instance
env = None

def get_env():
    global env
    if env is None:
        env = JarvisEnv(
            app_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), "express_app")
        )
    return env

@app.route('/reset', methods=['POST'])
def reset():
    observation = get_env().reset()
    return jsonify(asdict(observation))

@app.route('/step', methods=['POST'])
def step():
    data = request.get_json()
    agent_output = data.get('agent_output', '')
    reward, done, info = get_env().step(agent_output)
    return jsonify({'reward': reward, 'done': done, 'info': info})

@app.route('/state', methods=['GET'])
def state():
    observation = get_env().state()
    return jsonify(asdict(observation))

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 7860))
    app.run(host='0.0.0.0', port=port)
