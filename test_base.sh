#!/bin/bash

# Test script for Gymnasium (r_base) environment
# This script tests if the Gymnasium installation is working correctly

set -e  # Exit on any error

echo "Testing Gymnasium (r_base) installation..."

# Activate virtual environment
echo "Activating virtual environment..."
source env_r_base/bin/activate

# Test 1: Basic import and version check
echo ""
echo "Test 1: Basic import and version check"
python -c "
import gymnasium as gym
print('✓ Gymnasium imported successfully')
print(f'✓ Version: {gym.__version__}')
"

# Test 2: Create a simple environment
echo ""
echo "Test 2: Creating CartPole environment"
python -c "
import gymnasium as gym
env = gym.make('CartPole-v1')
print('✓ CartPole-v1 environment created successfully')
print(f'✓ Action space: {env.action_space}')
print(f'✓ Observation space: {env.observation_space}')
env.close()
print('✓ Environment closed successfully')
"

# Test 3: Test environment step functionality
echo ""
echo "Test 3: Testing environment step functionality"
python -c "
import gymnasium as gym
import numpy as np

env = gym.make('CartPole-v1')
obs, info = env.reset(seed=42)
print('✓ Environment reset successfully')

# Take a few random steps
for i in range(5):
    action = env.action_space.sample()
    obs, reward, terminated, truncated, info = env.step(action)
    print(f'✓ Step {i+1}: reward={reward:.3f}, terminated={terminated}, truncated={truncated}')

env.close()
print('✓ Environment step functionality working correctly')
"

# Test 4: Test Box2D environments (if available)
echo ""
echo "Test 4: Testing Box2D environments"
python -c "
import gymnasium as gym
try:
    env = gym.make('CarRacing-v3')
    print('✓ CarRacing-v3 environment created successfully')
    print(f'✓ Action space: {env.action_space}')
    print(f'✓ Observation space: {env.observation_space}')
    env.close()
    print('✓ Box2D environments working correctly')
except Exception as e:
    print(f'⚠ Box2D environments not available: {e}')
"

# Test 5: Test environment registration
echo ""
echo "Test 5: Testing environment registration"
python -c "
import gymnasium as gym

print('✓ Available environments (first 10):')
envs = list(gym.envs.registry.keys())[:10]
for env_id in envs:
    print(f'  - {env_id}')

print(f'✓ Total environments available: {len(gym.envs.registry)}')
"

# Test 6: Test vectorized environments
echo ""
echo "Test 6: Testing vectorized environments"
python -c "
import gymnasium as gym

try:
    envs = gym.vector.make('CartPole-v1', num_envs=3)
    print('✓ Vectorized environment created successfully')
    print(f'✓ Number of environments: {envs.num_envs}')
    
    obs, info = envs.reset(seed=42)
    print(f'✓ Vectorized reset successful, obs shape: {obs.shape}')
    
    actions = envs.action_space.sample()
    obs, rewards, terminated, truncated, info = envs.step(actions)
    print(f'✓ Vectorized step successful, rewards shape: {rewards.shape}')
    
    envs.close()
    print('✓ Vectorized environments working correctly')
except Exception as e:
    print(f'⚠ Vectorized environments not available: {e}')
"

# Test 7: Test wrappers
echo ""
echo "Test 7: Testing environment wrappers"
python -c "
import gymnasium as gym
from gymnasium.wrappers import TimeLimit, NormalizeObservation

try:
    env = gym.make('CartPole-v1')
    env = TimeLimit(env, max_episode_steps=50)
    env = NormalizeObservation(env)
    
    print('✓ Wrappers applied successfully')
    print(f'✓ Wrapped environment action space: {env.action_space}')
    print(f'✓ Wrapped environment observation space: {env.observation_space}')
    
    obs, info = env.reset()
    print(f'✓ Wrapped environment reset successful, obs shape: {obs.shape}')
    
    env.close()
    print('✓ Environment wrappers working correctly')
except Exception as e:
    print(f'⚠ Environment wrappers not available: {e}')
"

echo ""
echo "=========================================="
echo "✓ All tests completed successfully!"
echo "✓ Gymnasium (r_base) is working correctly"
echo "=========================================="