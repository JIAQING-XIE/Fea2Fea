import itertools
import os.path as osp
import pandas as pd
import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import Dataset,DataLoader
import torch.nn as nn
from torch_geometric.datasets import Planetoid
import torch_geometric.transforms as T
from torch_geometric.nn import ARMAConv,AGNNConv
from torch_geometric.nn import GINConv,GATConv,GCNConv
from torch_geometric.nn import SAGEConv,SplineConv

class Net(nn.Module):
    def __init__(self, embedding = 'GIN', hidden_dim = 64, depth = 2, bins = 6, if_BN = 0):
        super(Net, self).__init__()
        self.embedding = embedding
        self.hidden_dim = hidden_dim
        self.depth = depth
        self.graph_embed = 0
        self.linear_embed = 0

        mlp1 = nn.Sequential(
                nn.Linear(1, 256),
                nn.BatchNorm1d(256),
                nn.ReLU(),
                nn.Linear(256,128),
            )
        mlp2 = nn.Sequential(
                nn.Linear(128,64 ),
                nn.BatchNorm1d(64),
                nn.ReLU(),
                nn.Linear(64,64),
            )
        mlp3 = nn.Sequential(
                nn.Linear(self.hidden_dim, self.hidden_dim),
                nn.BatchNorm1d(self.hidden_dim),
                nn.ReLU(),
        )
        self.bn = nn.BatchNorm1d(hidden_dim)
        self.embedding = embedding
        self.conv3 = nn.ModuleList()
        if self.embedding == 'SAGE':
            self.conv1 = SAGEConv(1,256,normalize=True)
            self.conv2 = SAGEConv(256,64 ,normalize=True)
            for i in range(self.depth-2):
                self.conv3.append(SAGEConv(hidden_dim, hidden_dim, normalize=True))
        elif self.embedding == 'GAT':
            self.conv1 = GATConv(1, 16,heads= 16, dropout=0.6)
            self.conv2 = GATConv(16 * 16, 64, heads=1, concat=False,
                           dropout=0.6)
            for i in range(self.depth-2):
                self.conv3.append(GATConv(hidden_dim, hidden_dim, heads = 1, concat= False, dropout= 0.5))
        elif self.embedding == 'GCN':
            self.conv1 = GCNConv(1,256,cached=False)
            self.conv2 = GCNConv(256,64,cached=False)
            for i in range(self.depth-2):
                self.conv3.append(GCNConv(hidden_dim, hidden_dim, cached=False))
        elif self.embedding == 'GIN':
            self.conv1 = GINConv(mlp1)
            self.conv2 = GINConv(mlp2)
            for i in range(self.depth-2):
                self.conv3.append(GINConv(mlp3))
        else:
            pass 
        self.lin1 = nn.Linear(hidden_dim,16)
        self.lin2 = nn.Linear(16,bins)
        self.batch_norm1 = nn.BatchNorm1d(256)
        self.batch_norm2 = nn.BatchNorm1d(64)
                                                                         
    def forward(self, data):
        x, edge_index = data.x, data.edge_index
        for i in range(self.depth):
            if i == 0:
                x = self.conv1(x, edge_index)
                if self.embedding != 'GIN':
                    x = self.batch_norm1(x)
                    x = F.relu(x)
                x = F.dropout(x, training=self.training)
            elif i == 1:
                x = self.conv2(x, edge_index)
                if self.embedding != 'GIN':
                    x = self.batch_norm2(x)
                    x = F.relu(x)
                x = F.dropout(x, training=self.training)
                self.graph_embed = x
            else:
                if self.embedding != 'GIN':
                    x = F.relu(self.conv3[self.depth-i](x, edge_index))
                else:
                    x = self.conv3[self.depth-i-1](x, edge_index)
                x = F.dropout(x, training=self.training)

        x = F.relu(self.lin1(x))

        x = self.lin2(x)
        self.linear_embed = x
        return F.log_softmax(x, dim =1)