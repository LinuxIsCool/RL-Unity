import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

def hidden_init(layer):
    fan_in = layer.weight.data.size()[0]
    lim = 1. / np.sqrt(fan_in)
    return (-lim, lim)

#Actor class: access to local information information only.

class Actor(nn.Module):
    """Estimates the policy deterministically using tanh activation for continuous action space"""
    def __init__(self, state_size=24, action_size=2, seed=2, fc1=128, fc2=128):
        """
        @Param:
        1. state_size: number of observations, i.e. brain.vector_action_space_size
        2. action_size: number of actions, i.e. env_info.vector_observations.shape[1]
        3. fc1: number of hidden units in the first fully connected layer. Default = 400.
        4. fc2: number of hidden units in the second fully connected layer, default = 300.
        """
        super(Actor, self).__init__()
        self.seed = torch.manual_seed(seed)
        #Layer 1
        self.fc1 = nn.Linear(state_size, fc1)
        self.bn1 = nn.BatchNorm1d(fc1)
        #Layer 2
        self.fc2 = nn.Linear(fc1, fc2) 
        self.bn2 = nn.BatchNorm1d(fc2)
        #Output layer
        self.fc3 = nn.Linear(fc2, action_size) # µ(s|θ) {Deterministic policy}
        
        #Initialize Weights
        self.reset_parameters()

    def reset_parameters(self):
        """
        Resets the parameters by setting a noise from distribution following from its respective hidden unit size.
        Format for (-fx,fx) followed from the original paper.
        """
        self.fc1.weight.data.uniform_(*hidden_init(self.fc1))
        self.fc2.weight.data.uniform_(*hidden_init(self.fc2))
        self.fc3.weight.data.uniform_(-3e-3, 3e-3)
        
    def forward(self, state):
        """
        Performs a single forward pass to map (state,action) to policy, pi.
        @Param:
        1. state: current observations, shape: (env.observation_space.shape[0],)
        2. action: immediate action to evaluate against, shape: (env.action_space.shape[0],)
        @Return:
        - µ(s|θ)
        """
        if state.dim() == 1:
            state = torch.unsqueeze(state,0)
        x = state
        #Layer #1
        x = self.fc1(x)
        x = self.bn1(x)
        x = F.relu(x)
        
        #Layer #2
        x = self.fc2(x)
        x = self.bn2(x)
        x = F.relu(x)

        #Output
        x = self.fc3(x)
        mu = torch.tanh(x)
        return mu


#Critic class: 
#Augmented with information about policies of other agents (or able to infer about other agents’ policies).

class Critic(nn.Module):
    """Value approximator V(pi) as Q(s, a|θ)"""
    def __init__(self, state_size=24, action_size=2, seed=2, fc1=128, fc2=128):
        """
        @Param:
        1. state_size: number of observations for 1 agent.
        2. action_size: number of actions for 1 agent.
        3. seed: seed value for reproducibility. default = 0.
        4. fc1: number of hidden units in the first fully connected layer. Default = 256.
        5. fc2: number of hidden units in the second fully connected layer, default = 128.
        """
        super(Critic, self).__init__()
        self.seed = torch.manual_seed(seed)
        #Layer 1
        self.fc1 = nn.Linear(state_size, fc1)
        self.bn1 = nn.BatchNorm1d(fc1)
        #Layer 2
        self.fc2 = nn.Linear(fc1 + action_size, fc2)
        #Output layer
        self.fc3 = nn.Linear(fc2, 1) #Q-value
        
        #Initialize Weights
        self.reset_parameters()

    def reset_parameters(self):
        """
        Resets the parameters by setting a noise from distribution following from its respective hidden unit size.
        Format for (-fx,fx) followed from the original paper.
        """
        self.fc1.weight.data.uniform_(*hidden_init(self.fc1))
        self.fc2.weight.data.uniform_(*hidden_init(self.fc2))
        self.fc3.weight.data.uniform_(-3e-3, 3e-3)
        
    def forward(self, state, action):
        """
        Performs a single forward pass to map (state,action) to Q-value
        @Param:
        1. state: current observations, shape: (env.observation_space.shape[0],)
        2. action: immediate action to evaluate against, shape: (env.action_space.shape[0],)
        @Return:
        - q-value
        """
        if state.dim() == 1:
            state = torch.unsqueeze(state,0)
        #Layer #1
        x = self.fc1(state)
        x = F.relu(x)
        x = self.bn1(x)
        #Layer #2
        x = torch.cat((x, action), dim=1) #Concatenate state with action. Note that the specific way of passing x_state into layer #2.
        x = self.fc2(x) 
        x = F.relu(x)
        #Output
        value = self.fc3(x)
        return value