
#import sys
#print(sys.path)
#sys.path.append('/home/crombez/Documents/PhD/python/openspyrit/spyrit/') 

import torch
import torch.nn as nn
import torch.nn.functional as F
#import torch.optim as optim
import numpy as np
#import torchvision
#from torchvision import datasets, models, transforms
#import matplotlib.pyplot as plt
#import time
#import os
#import copy
from spyrit.misc.pattern_choice import Hadamard, matrix2conv, split
from collections import OrderedDict
#import cv2
from scipy.stats import rankdata
#from itertools import cycle;
#from pathlib import Path
from spyrit.learning.model_Had_DCAN import *
from spyrit.misc.disp import *
from spyrit.misc.data_visualisation import plot_im2D    
#import spyrit.misc.walsh_hadamard as wh
#from spyrit.misc.statistics import * #J'ai du enlever mais je ne car Errer : No module named 
import math
import scipy

def Pinv_reg(Pmat,n,alpha):
    motifs = (Pmat[:n,:n])
    Pinv = np.zeros((n*n,n*n))
    pinv = scipy.linalg.pinv(motifs,rtol = alpha)
    for i in range(0,n*n,n):
        Pinv[i:i+n,i:i+n]=pinv
    return(Pinv)





#    
class compNet_1D(compNet):
    def __init__(self, n, M, Mean, Cov, variant=0, H=None, alpha=0, Ord=None):
        super().__init__(n, M, Mean, Cov, variant, H, Ord)
        self.alpha = alpha
        self.even_index = range(0,2*M*n,2);
        self.uneven_index = range(1,2*M*n,2);
        self.n = n;
        self.M = M;
        Pmat = H
        Pconv = matrix2conv(Pmat);
        
        self.Patt = Pconv;
        P, T = split(Pconv, 1);
        self.P = P;
        self.T = T;
        self.P.bias.requires_grad = False;
        self.P.weight.requires_grad = False;
        self.Patt.bias.requires_grad = False;
        self.Patt.weight.requires_grad = False;
        self.T.weight.requires_grad=False;
        self.T.weight.requires_grad=False;
        
        #-- Pseudo-inverse to determine levels of noise.
        Pinv = Pinv_reg(Pmat,n,alpha)#(1/n**2)*np.transpose(Pmat);#Pinv = Pinv_reg(Pmat,n,alpha)
        self.Pinv = nn.Linear(M,n**2, False)
        self.Pinv.weight.data=torch.from_numpy(Pinv);
        self.Pinv.weight.data=self.Pinv.weight.data.float();
        self.Pinv.weight.requires_grad=False;
        
        
        #-- Measurement to image domain
        if variant==0:
            #--- Statistical Matrix completion (no mean)
            print("Measurement to image domain: statistical completion (no mean)")
            
            self.fc1 = nn.Linear(M,n**2, False)
            
            W, b, mu1 = stat_completion_matrices(Perm, H, Cov, Mean, M)
            W = (1/n**2)*W; 

            self.fc1.weight.data=torch.from_numpy(W);
            self.fc1.weight.data=self.fc1.weight.data.float();
            self.fc1.weight.requires_grad=False;
        
        if variant==1:
            #--- Statistical Matrix completion  
            print("Measurement to image domain: statistical completion")
            
            self.fc1 = nn.Linear(M,n**2)
            
            W, b, mu1 = stat_completion_matrices(Perm, H, Cov, Mean, M)
            W = (1/n**2)*W; 
            b = (1/n**2)*b;
            b = b - np.dot(W,mu1);
            self.fc1.bias.data=torch.from_numpy(b[:,0]);
            self.fc1.bias.data=self.fc1.bias.data.float();
            self.fc1.bias.requires_grad = False;
            self.fc1.weight.data=torch.from_numpy(W);
            self.fc1.weight.data=self.fc1.weight.data.float();
            self.fc1.weight.requires_grad=False;
        
        elif variant==2:
            #--- Pseudo-inverse
            print("Measurement to image domain: pseudo inverse")
            
            self.fc1 = self.Pinv;
       
        elif variant==3:
            #--- FC is learnt
            print("Measurement to image domain: free")
            
            self.fc1 = nn.Linear(M,n**2)
            
        #-- Image correction
        self.recon = nn.Sequential(OrderedDict([
          ('conv1', nn.Conv2d(1,64,kernel_size=9, stride=1, padding=4)),
          ('relu1', nn.ReLU()),
          ('conv2', nn.Conv2d(64,32,kernel_size=1, stride=1, padding=0)),
          ('relu2', nn.ReLU()),
          ('conv3', nn.Conv2d(32,1,kernel_size=5, stride=1, padding=2))
        ]));
        
    def forward_acquire(self, x, b, c, h, w):
        #--Scale input image
        x = (x+1)/2; 
        #--Acquisition
        x = x.view(b*c, 1, h, w);

        x = self.P(x);
        #x = F.relu(x); ## x[:,:,1] = -1/N0 ???? #Modifié
        print("No noise")
        x = x.view(b*c,1, 2*self.M*self.n);#x.view(b, c, 2*self.M)#; #Modifié
        return x
    
    def forward_preprocess(self, x, b, c, h, w):
        #- Pre-processing (use batch norm to avoid division by N0 ?)
        x = x[:,:,self.even_index] - x[:,:,self.uneven_index];
        #x = 2*x-torch.reshape(self.Patt(torch.ones(b*c,1,h,w).to(x.device)),(b,c,self.M*self.n)); #Modifier
        return x
   


    
#%%
#===========================================
# Test d'un autre type de produit plus adapater pour le cas 1D
#===========================================
        

#def Stat_had_expe(dataloader, root):
#    """ 
#        Computes Mean Hadamard Image over the whole dataset + 
#        Covariance Matrix Amongst the coefficients
#    """
#
#    inputs, classes = next(iter(dataloader))
#    inputs = inputs.cpu().detach().numpy();
#    (batch_size, channels, nx, ny) = inputs.shape;
#    tot_num = len(dataloader)*batch_size;
#
#    Mean_had = np.zeros((nx, ny));
#    for inputs,labels in dataloader:
#        inputs = inputs.cpu().detach().numpy();
#        for i in range(inputs.shape[0]):
#            img = inputs[i,0,:,:];
#            H = walsh_matrix(len(img))
#            h_img = wh.walsh2(img,H)/len(img)
#            Mean_had += h_img;
#    Mean_had = Mean_had/tot_num;
#
#    Cov_had = np.zeros((nx*ny, nx*ny));
#    for inputs,labels in dataloader:
#        inputs = inputs.cpu().detach().numpy();
#        for i in range(inputs.shape[0]):
#            img = inputs[i,0,:,:];
#            H = walsh_matrix(len(img))
#            h_img = wh.walsh2(img,H)/len(img)
#            Norm_Variable = np.reshape(h_img-Mean_had, (nx*ny,1));
#            Cov_had += Norm_Variable*np.transpose(Norm_Variable);
#    Cov_had = Cov_had/(tot_num-1);
#
#    np.save(root+'Cov_{}x{}'.format(nx,ny)+'.npy', Cov_had)
#    np.savetxt(root+'Cov_{}x{}'.format(nx,ny)+'.txt', Cov_had)
#    
#    np.save(root+'Average_{}x{}'.format(nx,ny)+'.npy', Mean_had)
#    np.savetxt(root+'Average_{}x{}'.format(nx,ny)+'.txt', Mean_had)
#    cv2.imwrite(root+'Average_{}x{}'.format(nx,ny)+'.png', Mean_had) #Needs conversion to Uint8!
#    return Mean_had, Cov_had
    
        
class compNet_1D_test_product(nn.Module):
    def __init__(self, n, M, H, variant=2,alpha = 1e-1):
        super(compNet_1D_test_product, self).__init__()
        
        self.n = n;
        self.M = M;
        self.H = H[0][0][:M]
        #print(self.H.device)
        self.even_index = range(0,2*M*n,2);
        self.uneven_index = range(1,2*M*n,2);
        
#        #-- Hadamard patterns (full basis)
#        if type(H)==type(None):
#            H = Hadamard_Transform_Matrix(self.n)
#        H = n*H; #fht hadamard transform needs to be normalized
#        Pmat = np.zeros((M*n,n*n))
#        P_ind = []
#        for i in range(n):
#            for j in range(M):
#                P_ind.append(i*n+j)
#        for i in range(M*n):
#            Pmat[i] = H[P_ind[i]]
#            
#        Pinv2 = np.zeros((n*n,M*n))
#        P_ind = []
#        for i in range(n):
#            for j in range(M):
#                P_ind.append(i*n+j)
#        for i in range(M*n):
#            Pinv2[:,i] = Pinv[:,P_ind[i]]
#        Pinv = Pinv2
#        #-- Hadamard patterns (undersampled basis)
#        #Var = Cov2Var(Cov)
#        #Perm = Permutation_Matrix(Var)
#        #Pmat = np.dot(Perm,H);
#        #Pmat = H[:M,:];#Pmat[:M,:];
#        Pconv = matrix2conv(Pmat);
        

        #-- Denoising parameters 
        #Sigma = np.dot(Perm,np.dot(Cov,np.transpose(Perm)));
        #diag_index = np.diag_indices(n**2);
        #Sigma = Sigma[diag_index];
        #Sigma = n**2/4*Sigma[:M]; #(H = nH donc Cov = n**2 Cov)!
        ##Sigma = Sigma[:M];
        #Sigma = torch.Tensor(Sigma);
        #self.sigma = Sigma.view(1,1,M);
        

        #P1 = np.zeros((n**2,1));
        #P1[0] = n**2;
        #mean = n*np.reshape(Mean,(self.n**2,1))+P1;
        #mu = (1/2)*np.dot(Perm, mean);
        ##mu = np.dot(Perm, np.reshape(Mean, (n**2,1)))
        #mu1 = torch.Tensor(mu[:M]);
        #self.mu_1 = mu1.view(1,1,M);

        #-- Measurement preprocessing
#        self.Patt = Pconv;
#        P, T = split(Pconv, 1);
#        self.P = P;
#        self.T = T;
#        self.P.bias.requires_grad = False;
#        self.P.weight.requires_grad = False;
#        self.Patt.bias.requires_grad = False;
#        self.Patt.weight.requires_grad = False;
#        self.T.weight.requires_grad=False;
#        self.T.weight.requires_grad=False;

        #-- Pseudo-inverse to determine levels of noise.
        #if np.shape(Pinv)[0]==0:
        #    Pinv = torch.from_numpy(Pinv)
        #else:
        Pinv = torch.pinverse(self.H, rcond=alpha)#(1/n**2)*np.transpose(Pmat);
        
        Pinv = Pinv.float()
        self.Pinv = Pinv


        #-- Measurement to image domain
        if variant==0:
            #--- Statistical Matrix completion (no mean)
            print("Measurement to image domain: statistical completion (no mean)")
            
            self.fc1 = nn.Linear(M*n,n**2, False)
            
            W, b, mu1 = stat_completion_matrices(Perm, H, Cov, Mean, M)
            W = (1/n**2)*W; 

            self.fc1.weight.data=torch.from_numpy(W);
            self.fc1.weight.data=self.fc1.weight.data.float();
            self.fc1.weight.requires_grad=False;
        
        if variant==1:
            #--- Statistical Matrix completion  
            print("Measurement to image domain: statistical completion")
            
            self.fc1 = nn.Linear(M,n**2)
            
            W, b, mu1 = stat_completion_matrices(Perm, H, Cov, Mean, M)
            W = (1/n**2)*W; 
            b = (1/n**2)*b;
            b = b - np.dot(W,mu1);
            self.fc1.bias.data=torch.from_numpy(b[:,0]);
            self.fc1.bias.data=self.fc1.bias.data.float();
            self.fc1.bias.requires_grad = False;
            self.fc1.weight.data=torch.from_numpy(W);
            self.fc1.weight.data=self.fc1.weight.data.float();
            self.fc1.weight.requires_grad=False;
        
        elif variant==2:
            #--- Pseudo-inverse
            print("Measurement to image domain: pseudo inverse")
            
            self.fc1 = self.Pinv;
       
        elif variant==3:
            #--- FC is learnt
            print("Measurement to image domain: free")
            
            self.fc1 = nn.Linear(M,n**2)
            
        #-- Image correction
        self.recon = nn.Sequential(OrderedDict([
          ('conv1', nn.Conv2d(1,64,kernel_size=9, stride=1, padding=4)),
          ('relu1', nn.ReLU()),
          ('conv2', nn.Conv2d(64,32,kernel_size=1, stride=1, padding=0)),
          ('relu2', nn.ReLU()),
          ('conv3', nn.Conv2d(32,1,kernel_size=5, stride=1, padding=2))
        ]));

    def forward(self, x):
        b,c,h,w = x.shape;
        x = self.forward_acquire(x, b, c, h, w);
        x = self.forward_reconstruct(x, b, c, h, w);
        return x
    #--------------------------------------------------------------------------
    # Forward functions (with grad)
    #--------------------------------------------------------------------------
    def forward_acquire(self, x, b, c, h, w):
        #--Scale input image
        #x = (x+1)/2; 
        #--Acquisition
        x = x.view(b*c, 1, h, w);
        x = torch.matmul(self.H,x)
        x = x.float()
        #res_im = x.numpy()
        #plot_im2D(res_im[0][0])
        #x = F.relu(x); ## x[:,:,1] = -1/N0 ????
        #x = x.view(b*c,1, self.M*self.n); 
        return x
    
    def forward_maptoimage(self, x, b, c, h, w):
        #- Pre-processing (use batch norm to avoid division by N0 ?)
        #x = self.T(x);
        #x = 2*x-torch.reshape(self.Patt(torch.ones(b*c,1, h,w).to(x.device)),(b*c,1,self.M));
        #--Projection to the image domain

        x = x.float()
        x = torch.matmul(self.Pinv,x)
        x = x.view(b*c,1,h,w)
        return x
    
    def forward_preprocess(self, x, b, c, h, w):
        #- Pre-processing (use batch norm to avoid division by N0 ?)
        #x = x[:,:,self.even_index] - x[:,:,self.uneven_index];
        #x = 2*x-torch.reshape(self.Patt(torch.ones(b*c,1,h,w).to(x.device)),(b,c,self.M));
        return x
    
    def forward_postprocess(self, x, b, c, h, w):
        x = self.recon(x)
        x = x.view(b, c, h, w)
        return x
    
    def forward_reconstruct(self, x, b, c, h, w):
        x = self.forward_maptoimage(x, b, c, h, w)
        x = self.forward_postprocess(x, b, c, h, w)
        return x
     
    
    #--------------------------------------------------------------------------
    # Evaluation functions (no grad)
    #--------------------------------------------------------------------------
    def acquire(self, x, b, c, h, w):
        with torch.no_grad():
            b,c,h,w = x.shape
            x = self.forward_acquire(x, b, c, h, w)
        return x
    
    def evaluate_fcl(self, x):
        with torch.no_grad():
           b,c,h,w = x.shape
           x = self.forward_acquire(x, b, c, h, w)
           x = self.forward_maptoimage(x, b, c, h, w)
        return x
     
    def evaluate_Pinv(self, x):
        with torch.no_grad():
           b,c,h,w = x.shape
           x = self.forward_Pinv(x, b, c, h, w)
        return x
    
    def evaluate(self, x):
        with torch.no_grad():
           x = self.forward(x)
        return x
    
    def reconstruct(self, x, b, c, h, w):
        with torch.no_grad():
            b,c,h,w = x.shape
            x = self.forward_reconstruct(x, b, c, h, w)
        return x


class compNet_1D_test_product2(nn.Module):
    def __init__(self, n, M, H, variant=2,alpha = 1e-1):
        super(compNet_1D_test_product2, self).__init__()
        
        self.n = n;
        self.M = M;
        H =  H[0,0,:,:M]
        self.H = torch.transpose(H,0,1)
        #print(self.H.device)
        self.even_index = range(0,2*M*n,2);
        self.uneven_index = range(1,2*M*n,2);
        
#        #-- Hadamard patterns (full basis)
#        if type(H)==type(None):
#            H = Hadamard_Transform_Matrix(self.n)
#        H = n*H; #fht hadamard transform needs to be normalized
#        Pmat = np.zeros((M*n,n*n))
#        P_ind = []
#        for i in range(n):
#            for j in range(M):
#                P_ind.append(i*n+j)
#        for i in range(M*n):
#            Pmat[i] = H[P_ind[i]]
#            
#        Pinv2 = np.zeros((n*n,M*n))
#        P_ind = []
#        for i in range(n):
#            for j in range(M):
#                P_ind.append(i*n+j)
#        for i in range(M*n):
#            Pinv2[:,i] = Pinv[:,P_ind[i]]
#        Pinv = Pinv2
#        #-- Hadamard patterns (undersampled basis)
#        #Var = Cov2Var(Cov)
#        #Perm = Permutation_Matrix(Var)
#        #Pmat = np.dot(Perm,H);
#        #Pmat = H[:M,:];#Pmat[:M,:];
#        Pconv = matrix2conv(Pmat);
        

        #-- Denoising parameters 
        #Sigma = np.dot(Perm,np.dot(Cov,np.transpose(Perm)));
        #diag_index = np.diag_indices(n**2);
        #Sigma = Sigma[diag_index];
        #Sigma = n**2/4*Sigma[:M]; #(H = nH donc Cov = n**2 Cov)!
        ##Sigma = Sigma[:M];
        #Sigma = torch.Tensor(Sigma);
        #self.sigma = Sigma.view(1,1,M);
        

        #P1 = np.zeros((n**2,1));
        #P1[0] = n**2;
        #mean = n*np.reshape(Mean,(self.n**2,1))+P1;
        #mu = (1/2)*np.dot(Perm, mean);
        ##mu = np.dot(Perm, np.reshape(Mean, (n**2,1)))
        #mu1 = torch.Tensor(mu[:M]);
        #self.mu_1 = mu1.view(1,1,M);

        #-- Measurement preprocessing
#        self.Patt = Pconv;
#        P, T = split(Pconv, 1);
#        self.P = P;
#        self.T = T;
#        self.P.bias.requires_grad = False;
#        self.P.weight.requires_grad = False;
#        self.Patt.bias.requires_grad = False;
#        self.Patt.weight.requires_grad = False;
#        self.T.weight.requires_grad=False;
#        self.T.weight.requires_grad=False;

        #-- Pseudo-inverse to determine levels of noise.
        #if np.shape(Pinv)[0]==0:
        #    Pinv = torch.from_numpy(Pinv)
        #else:
        Pinv = torch.pinverse(self.H, rcond=alpha)#(1/n**2)*np.transpose(Pmat);
        
        Pinv = Pinv.float()
        self.Pinv = Pinv


        #-- Measurement to image domain
        if variant==0:
            #--- Statistical Matrix completion (no mean)
            print("Measurement to image domain: statistical completion (no mean)")
            
            self.fc1 = nn.Linear(M*n,n**2, False)
            
            W, b, mu1 = stat_completion_matrices(Perm, H, Cov, Mean, M)
            W = (1/n**2)*W; 

            self.fc1.weight.data=torch.from_numpy(W);
            self.fc1.weight.data=self.fc1.weight.data.float();
            self.fc1.weight.requires_grad=False;
        
        if variant==1:
            #--- Statistical Matrix completion  
            print("Measurement to image domain: statistical completion")
            
            self.fc1 = nn.Linear(M,n**2)
            
            W, b, mu1 = stat_completion_matrices(Perm, H, Cov, Mean, M)
            W = (1/n**2)*W; 
            b = (1/n**2)*b;
            b = b - np.dot(W,mu1);
            self.fc1.bias.data=torch.from_numpy(b[:,0]);
            self.fc1.bias.data=self.fc1.bias.data.float();
            self.fc1.bias.requires_grad = False;
            self.fc1.weight.data=torch.from_numpy(W);
            self.fc1.weight.data=self.fc1.weight.data.float();
            self.fc1.weight.requires_grad=False;
        
        elif variant==2:
            #--- Pseudo-inverse
            print("Measurement to image domain: pseudo inverse")
            
            self.fc1 = self.Pinv;
       
        elif variant==3:
            #--- FC is learnt
            print("Measurement to image domain: free")
            
            self.fc1 = nn.Linear(M,n**2)
            
        #-- Image correction
        self.recon = nn.Sequential(OrderedDict([
          ('conv1', nn.Conv2d(1,64,kernel_size=9, stride=1, padding=4)),
          ('relu1', nn.ReLU()),
          ('conv2', nn.Conv2d(64,32,kernel_size=1, stride=1, padding=0)),
          ('relu2', nn.ReLU()),
          ('conv3', nn.Conv2d(32,1,kernel_size=5, stride=1, padding=2))
        ]));

    def forward(self, x):
        b,c,h,w = x.shape;
        x = self.forward_acquire(x, b, c, h, w);
        x = self.forward_reconstruct(x, b, c, h, w);
        return x
    #--------------------------------------------------------------------------
    # Forward functions (with grad)
    #--------------------------------------------------------------------------
    def forward_acquire(self, x, b, c, h, w):
        #--Scale input image
        #x = (x+1)/2; 
        #--Acquisition
        x = x.view(b*c, 1, h, w);
        x = torch.matmul(x,self.H)#x = torch.matmul(self.H,x)
        x = x.float()
        #res_im = x.numpy()
        #plot_im2D(res_im[0][0])
        #x = F.relu(x); ## x[:,:,1] = -1/N0 ????
        #x = x.view(b*c,1, self.M*self.n); 
        return x
    
    def forward_maptoimage(self, x, b, c, h, w):
        #- Pre-processing (use batch norm to avoid division by N0 ?)
        #x = self.T(x);
        #x = 2*x-torch.reshape(self.Patt(torch.ones(b*c,1, h,w).to(x.device)),(b*c,1,self.M));
        #--Projection to the image domain

        #x = x.float()
        x = torch.matmul(x,self.Pinv)#x = torch.matmul(self.Pinv,x)
        x = x.view(b*c,1,h,w)
        return x
    
    def forward_preprocess(self, x, b, c, h, w):
        #- Pre-processing (use batch norm to avoid division by N0 ?)
        #x = x[:,:,self.even_index] - x[:,:,self.uneven_index];
        #x = 2*x-torch.reshape(self.Patt(torch.ones(b*c,1,h,w).to(x.device)),(b,c,self.M));
        return x
    
    def forward_postprocess(self, x, b, c, h, w):
        x = self.recon(x)
        x = x.view(b, c, h, w)
        return x
    
    def forward_reconstruct(self, x, b, c, h, w):
        x = self.forward_maptoimage(x, b, c, h, w)
        x = self.forward_postprocess(x, b, c, h, w)
        return x
     
    
    #--------------------------------------------------------------------------
    # Evaluation functions (no grad)
    #--------------------------------------------------------------------------
    def acquire(self, x, b, c, h, w):
        with torch.no_grad():
            b,c,h,w = x.shape
            x = self.forward_acquire(x, b, c, h, w)
        return x
    
    def evaluate_fcl(self, x):
        with torch.no_grad():
           b,c,h,w = x.shape
           x = self.forward_acquire(x, b, c, h, w)
           x = self.forward_maptoimage(x, b, c, h, w)
        return x
     
    def evaluate_Pinv(self, x):
        with torch.no_grad():
           b,c,h,w = x.shape
           x = self.forward_Pinv(x, b, c, h, w)
        return x
    
    def evaluate(self, x):
        with torch.no_grad():
           x = self.forward(x)
        return x
    
    def reconstruct(self, x, b, c, h, w):
        with torch.no_grad():
            b,c,h,w = x.shape
            x = self.forward_reconstruct(x, b, c, h, w)
        return x


## compnet avec image de la bonne taille 
        
class compNet_1D_size_im(nn.Module):
    def __init__(self, M, H, variant=2,alpha = 1e-1):
        super(compNet_1D_size_im, self).__init__()
        
        #self.Nl = Nl;
        #self.Nc = Nc;
        #self.Nh = Nh;
        self.M = M;
        #H =  H[0,0,:,:M]
        self.H = H[0][0][:,:M]
        print(H.size())
        #print(self.H.device)
        #self.even_index = range(0,2*M*n,2);
        #self.uneven_index = range(1,2*M*n,2);
        
#        #-- Hadamard patterns (full basis)
#        if type(H)==type(None):
#            H = Hadamard_Transform_Matrix(self.n)
#        H = n*H; #fht hadamard transform needs to be normalized
#        Pmat = np.zeros((M*n,n*n))
#        P_ind = []
#        for i in range(n):
#            for j in range(M):
#                P_ind.append(i*n+j)
#        for i in range(M*n):
#            Pmat[i] = H[P_ind[i]]
#            
#        Pinv2 = np.zeros((n*n,M*n))
#        P_ind = []
#        for i in range(n):
#            for j in range(M):
#                P_ind.append(i*n+j)
#        for i in range(M*n):
#            Pinv2[:,i] = Pinv[:,P_ind[i]]
#        Pinv = Pinv2
#        #-- Hadamard patterns (undersampled basis)
#        #Var = Cov2Var(Cov)
#        #Perm = Permutation_Matrix(Var)
#        #Pmat = np.dot(Perm,H);
#        #Pmat = H[:M,:];#Pmat[:M,:];
#        Pconv = matrix2conv(Pmat);
        

        #-- Denoising parameters 
        #Sigma = np.dot(Perm,np.dot(Cov,np.transpose(Perm)));
        #diag_index = np.diag_indices(n**2);
        #Sigma = Sigma[diag_index];
        #Sigma = n**2/4*Sigma[:M]; #(H = nH donc Cov = n**2 Cov)!
        ##Sigma = Sigma[:M];
        #Sigma = torch.Tensor(Sigma);
        #self.sigma = Sigma.view(1,1,M);
        

        #P1 = np.zeros((n**2,1));
        #P1[0] = n**2;
        #mean = n*np.reshape(Mean,(self.n**2,1))+P1;
        #mu = (1/2)*np.dot(Perm, mean);
        ##mu = np.dot(Perm, np.reshape(Mean, (n**2,1)))
        #mu1 = torch.Tensor(mu[:M]);
        #self.mu_1 = mu1.view(1,1,M);

        #-- Measurement preprocessing
#        self.Patt = Pconv;
#        P, T = split(Pconv, 1);
#        self.P = P;
#        self.T = T;
#        self.P.bias.requires_grad = False;
#        self.P.weight.requires_grad = False;
#        self.Patt.bias.requires_grad = False;
#        self.Patt.weight.requires_grad = False;
#        self.T.weight.requires_grad=False;
#        self.T.weight.requires_grad=False;

        #-- Pseudo-inverse to determine levels of noise.
        #if np.shape(Pinv)[0]==0:
        #    Pinv = torch.from_numpy(Pinv)
        #else:
        Pinv = torch.pinverse(self.H, rcond=alpha)#(1/n**2)*np.transpose(Pmat);
        
        Pinv = Pinv.float()
        self.Pinv = Pinv


        #-- Measurement to image domain
        if variant==0:
            #--- Statistical Matrix completion (no mean)
            print("Measurement to image domain: statistical completion (no mean)")
            
            self.fc1 = nn.Linear(M*n,n**2, False)
            
            W, b, mu1 = stat_completion_matrices(Perm, H, Cov, Mean, M)
            W = (1/n**2)*W; 

            self.fc1.weight.data=torch.from_numpy(W);
            self.fc1.weight.data=self.fc1.weight.data.float();
            self.fc1.weight.requires_grad=False;
        
        if variant==1:
            #--- Statistical Matrix completion  
            print("Measurement to image domain: statistical completion")
            
            self.fc1 = nn.Linear(M,n**2)
            
            W, b, mu1 = stat_completion_matrices(Perm, H, Cov, Mean, M)
            W = (1/n**2)*W; 
            b = (1/n**2)*b;
            b = b - np.dot(W,mu1);
            self.fc1.bias.data=torch.from_numpy(b[:,0]);
            self.fc1.bias.data=self.fc1.bias.data.float();
            self.fc1.bias.requires_grad = False;
            self.fc1.weight.data=torch.from_numpy(W);
            self.fc1.weight.data=self.fc1.weight.data.float();
            self.fc1.weight.requires_grad=False;
        
        elif variant==2:
            #--- Pseudo-inverse
            print("Measurement to image domain: pseudo inverse")
            
            self.fc1 = self.Pinv;
       
        elif variant==3:
            #--- FC is learnt
            print("Measurement to image domain: free")
            
            self.fc1 = nn.Linear(M,n**2)
            
        #-- Image correction
        self.recon = nn.Sequential(OrderedDict([
          ('conv1', nn.Conv2d(1,64,kernel_size=9, stride=1, padding=4)),
          ('relu1', nn.ReLU()),
          ('conv2', nn.Conv2d(64,32,kernel_size=1, stride=1, padding=0)),
          ('relu2', nn.ReLU()),
          ('conv3', nn.Conv2d(32,1,kernel_size=5, stride=1, padding=2))
        ]));

    def forward(self, x):
        b,c,h,w = x.shape;
        x = self.forward_acquire(x, b, c, h, w);
        x = self.forward_reconstruct(x, b, c, h, w);
        return x
    #--------------------------------------------------------------------------
    # Forward functions (with grad)
    #--------------------------------------------------------------------------
    def forward_acquire(self, x, b, c, h, w):
        #--Scale input image
        #x = (x+1)/2; 
        #--Acquisition
        x = x.view(b*c, 1, h, w);
        x = torch.matmul(x,self.H)#x = torch.matmul(self.H,x)
        x = x.float()
        #res_im = x.numpy()
        #plot_im2D(res_im[0][0])
        #x = F.relu(x); ## x[:,:,1] = -1/N0 ????
        #x = x.view(b*c,1, self.M*self.n); 
        return x
    
    def forward_maptoimage(self, x, b, c, h, w):
        #- Pre-processing (use batch norm to avoid division by N0 ?)
        #x = self.T(x);
        #x = 2*x-torch.reshape(self.Patt(torch.ones(b*c,1, h,w).to(x.device)),(b*c,1,self.M));
        #--Projection to the image domain

        #x = x.float()
        x = torch.matmul(x,self.Pinv)#x = torch.matmul(self.Pinv,x)
        x = x.view(b*c,1,h,w)
        return x
    
    def forward_preprocess(self, x, b, c, h, w):
        #- Pre-processing (use batch norm to avoid division by N0 ?)
        #x = x[:,:,self.even_index] - x[:,:,self.uneven_index];
        #x = 2*x-torch.reshape(self.Patt(torch.ones(b*c,1,h,w).to(x.device)),(b,c,self.M));
        return x
    
    def forward_postprocess(self, x, b, c, h, w):
        x = self.recon(x)
        x = x.view(b, c, h, w)
        return x
    
    def forward_reconstruct(self, x, b, c, h, w):
        x = self.forward_maptoimage(x, b, c, h, w)
        x = self.forward_postprocess(x, b, c, h, w)
        return x
     
    
    #--------------------------------------------------------------------------
    # Evaluation functions (no grad)
    #--------------------------------------------------------------------------
    def acquire(self, x, b, c, h, w):
        with torch.no_grad():
            b,c,h,w = x.shape
            x = self.forward_acquire(x, b, c, h, w)
        return x
    
    def evaluate_fcl(self, x):
        with torch.no_grad():
           b,c,h,w = x.shape
           x = self.forward_acquire(x, b, c, h, w)
           x = self.forward_maptoimage(x, b, c, h, w)
        return x
     
    def evaluate_Pinv(self, x):
        with torch.no_grad():
           b,c,h,w = x.shape
           x = self.forward_Pinv(x, b, c, h, w)
        return x
    
    def evaluate(self, x):
        with torch.no_grad():
           x = self.forward(x)
        return x
    
    def reconstruct(self, x, b, c, h, w):
        with torch.no_grad():
            b,c,h,w = x.shape
            x = self.forward_reconstruct(x, b, c, h, w)
        return x


