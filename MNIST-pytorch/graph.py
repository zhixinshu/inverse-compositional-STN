import numpy as np
import torch
import time
import data,warp,util

# build classification network
class FullCNN(torch.nn.Module):
	def __init__(self,opt):
		super(FullCNN,self).__init__()
		self.inDim = 1
		def conv2Layer(outDim):
			conv = torch.nn.Conv2d(self.inDim,outDim,kernel_size=[3,3],stride=1,padding=0)
			self.inDim = outDim
			return conv
		def linearLayer(outDim):
			fc = torch.nn.Linear(self.inDim,outDim)
			self.inDim = outDim
			return fc
		def maxpoolLayer(): return torch.nn.MaxPool2d([2,2],stride=2)
		self.conv2Layers = torch.nn.Sequential(
			conv2Layer(3),torch.nn.ReLU(True),
			conv2Layer(6),torch.nn.ReLU(True),maxpoolLayer(),
			conv2Layer(9),torch.nn.ReLU(True),
			conv2Layer(12),torch.nn.ReLU(True)
		)
		self.inDim *= 8**2
		self.linearLayers = torch.nn.Sequential(
			linearLayer(48),torch.nn.ReLU(True),
			linearLayer(opt.labelN)
		)
		initialize(opt,self,opt.stdC)
	def forward(self,opt,image):
		feat = image
		feat = self.conv2Layers(feat).view(opt.batchSize,-1)
		feat = self.linearLayers(feat)
		output = feat
		return output

# build classification network
class CNN(torch.nn.Module):
	def __init__(self,opt):
		super(CNN,self).__init__()
		self.inDim = 1
		def conv2Layer(outDim):
			conv = torch.nn.Conv2d(self.inDim,outDim,kernel_size=[9,9],stride=1,padding=0)
			self.inDim = outDim
			return conv
		def linearLayer(outDim):
			fc = torch.nn.Linear(self.inDim,outDim)
			self.inDim = outDim
			return fc
		def maxpoolLayer(): return torch.nn.MaxPool2d([2,2],stride=2)
		self.conv2Layers = torch.nn.Sequential(
			conv2Layer(3),torch.nn.ReLU(True)
		)
		self.inDim *= 20**2
		self.linearLayers = torch.nn.Sequential(
			linearLayer(opt.labelN)
		)
		initialize(opt,self,opt.stdC)
	def forward(self,opt,image):
		feat = image
		feat = self.conv2Layers(feat).view(opt.batchSize,-1)
		feat = self.linearLayers(feat)
		output = feat
		return output

# an identity class to skip geometric predictors
class Identity(torch.nn.Module):
	def __init__(self): super(Identity,self).__init__()
	def forward(self,opt,feat): return [feat]

# build Spatial Transformer Network
class STN(torch.nn.Module):
	def __init__(self,opt):
		super(STN,self).__init__()
		self.inDim = 1
		def conv2Layer(outDim):
			conv = torch.nn.Conv2d(self.inDim,outDim,kernel_size=[7,7],stride=1,padding=0)
			self.inDim = outDim
			return conv
		def linearLayer(outDim):
			fc = torch.nn.Linear(self.inDim,outDim)
			self.inDim = outDim
			return fc
		def maxpoolLayer(): return torch.nn.MaxPool2d([2,2],stride=2)
		self.conv2Layers = torch.nn.Sequential(
			conv2Layer(4),torch.nn.ReLU(True),
			conv2Layer(8),torch.nn.ReLU(True),maxpoolLayer()
		)
		self.inDim *= 8**2
		self.linearLayers = torch.nn.Sequential(
			linearLayer(48),torch.nn.ReLU(True),
			linearLayer(opt.warpDim)
		)
		initialize(opt,self,opt.stdGP,last0=True)
	def forward(self,opt,image):
		imageWarpAll = [image]
		feat = image
		feat = self.conv2Layers(feat).view(opt.batchSize,-1)
		feat = self.linearLayers(feat)
		p = feat
		pMtrx = warp.vec2mtrx(opt,p)
		imageWarp = warp.transformImage(opt,image,pMtrx)
		imageWarpAll.append(imageWarp)
		return imageWarpAll

# build Inverse Compositional STN
class ICSTN(torch.nn.Module):
	def __init__(self,opt):
		super(ICSTN,self).__init__()
		self.inDim = 1
		def conv2Layer(outDim):
			conv = torch.nn.Conv2d(self.inDim,outDim,kernel_size=[7,7],stride=1,padding=0)
			self.inDim = outDim
			return conv
		def linearLayer(outDim):
			fc = torch.nn.Linear(self.inDim,outDim)
			self.inDim = outDim
			return fc
		def maxpoolLayer(): return torch.nn.MaxPool2d([2,2],stride=2)
		self.conv2Layers = torch.nn.Sequential(
			conv2Layer(4),torch.nn.ReLU(True),
			conv2Layer(8),torch.nn.ReLU(True),maxpoolLayer()
		)
		self.inDim *= 8**2
		self.linearLayers = torch.nn.Sequential(
			linearLayer(48),torch.nn.ReLU(True),
			linearLayer(opt.warpDim)
		)
		initialize(opt,self,opt.stdGP,last0=True)
	def forward(self,opt,image,p):
		imageWarpAll = []
		for l in range(opt.warpN):
			pMtrx = warp.vec2mtrx(opt,p)
			imageWarp = warp.transformImage(opt,image,pMtrx)
			imageWarpAll.append(imageWarp)
			feat = imageWarp
			feat = self.conv2Layers(feat).view(opt.batchSize,-1)
			feat = self.linearLayers(feat)
			dp = feat
			p = warp.compose(opt,p,dp)
		pMtrx = warp.vec2mtrx(opt,p)
		imageWarp = warp.transformImage(opt,image,pMtrx)
		imageWarpAll.append(imageWarp)
		return imageWarpAll

# initialize weights/biases
def initialize(opt,model,stddev,last0=False):
	for m in model.conv2Layers:
		if isinstance(m,torch.nn.Conv2d):
			m.weight.data.normal_(0,stddev)
			m.bias.data.normal_(0,stddev)
	for m in model.linearLayers:
		if isinstance(m,torch.nn.Linear):
			m.weight.data.normal_(0,0.0 if last0 and m is model.linearLayers[-1] else stddev)
			m.bias.data.normal_(0,0.0 if last0 and m is model.linearLayers[-1] else stddev)
