from typing import Any

import numpy as np
from gymnasium import ObservationWrapper, Wrapper
from gymnasium.spaces import Box
from gymnasium.core import Env
import cv2
import torch


class FireResetEnv(Wrapper):
    def __init__(self, env=None):
        """For environments where the user need to press FIRE for the game to start."""
        super().__init__(env)
        assert env.unwrapped.get_action_meanings()[1] == 'FIRE'
        assert len(env.unwrapped.get_action_meanings()) >= 3

    def step(self, action):
        return self.env.step(action)

    def reset(self, *args, **kwargs):
        _, info = self.env.reset(*args, **kwargs)
        obs, _, terminated, truncated, info = self.env.step(1)
        done = terminated or truncated
        if done:
            _, info = self.env.reset(*args, **kwargs)
        obs, _, terminated, truncated, info = self.env.step(2)
        done = terminated or truncated
        if done:
            _, info = self.env.reset(*args, **kwargs)
        return obs, info


class Reshape(ObservationWrapper):

    def __init__(self, env: Env, resize_height, resize_width):
        super().__init__(env)

        self.resize_height = resize_height
        self.resize_width = resize_width
        self.observation_space = Box(
            np.zeros((resize_width, resize_width)),
            255 * np.ones((resize_width, resize_width)),
            dtype=np.uint8
        )

    def observation(self, observation: Any) -> Any:

        resized_obs = cv2.resize(observation, (self.resize_width, self.resize_height))
        resize_diff = (self.resize_height - self.resize_width) // 2
        obs = resized_obs[resize_diff:-resize_diff, :]
        return obs
    
class Normalize(ObservationWrapper):

    def __init__(self, env: Env):
        super().__init__(env)

    def observation(self, observation: Any) -> Any:

        return observation / 255.

class Stack(ObservationWrapper):

    def __init__(self, env: Env, n_frames: int):

        super().__init__(env)

        stacked_space_shape = (n_frames, ) + self.observation_space.shape
        self.observation_space = Box(
            np.zeros(stacked_space_shape),
            np.ones(stacked_space_shape))
        
    def reset(self, *args, **kwargs):

        self.cur_state = np.zeros(
            self.observation_space.shape)
        
        observation, info = self.env.reset(*args, **kwargs)
        return self.observation(observation), info

    def observation(self, observation: Any) -> Any:

        self.cur_state[:-1, :, :] = self.cur_state[1:, :, :]
        self.cur_state[-1, :, :] = observation

        return self.cur_state
    
class Numpy2Torch(ObservationWrapper):

    def __init__(self, env: Env):
        super().__init__(env)

    def observation(self, observation: Any) -> Any:
        return torch.tensor(observation).float()
        

def wrap(env):
    #env = FireResetEnv(env)
    env = Reshape(env, 110, 84)
    env = Normalize(env)
    env = Stack(env, 4)
    env = Numpy2Torch(env)
    return env