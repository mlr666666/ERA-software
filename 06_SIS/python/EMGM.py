import numpy as np
import scipy as sp
from scipy import cluster
"""
---------------------------------------------------------------------------
Perform soft EM algorithm for fitting the Gaussian mixture model
---------------------------------------------------------------------------
Created by:
Sebastian Geyer (s.geyer@tum.de)
implemented in Python by:
Matthias Willer (matthias.willer@tum.de)
Engineering Risk Analysis Group
Technische Universitat Munchen
www.era.bgu.tum.de
---------------------------------------------------------------------------
Version 2018-03
---------------------------------------------------------------------------
Input:
* X       :
* W       :
* nGM     :
---------------------------------------------------------------------------
Output:
* mu    : 
* Sigma :
* pi    :
---------------------------------------------------------------------------
"""
def EMGM(X, W, nGM):
    # reshaping just to be sure
    W = W.reshape(-1,1)

    ## initialization
    R = initialization(X, nGM)

    tol       = 1e-5
    maxiter   = 500
    llh       = np.full([maxiter],-np.inf)
    converged = False
    t         = 0

    ## soft EM algorithm
    while (not converged) and t < maxiter:
        t = t+1   
        
        # [~,label(:)] = max(R,[],2)
        # u = unique(label)   # non-empty components
        # if size(R,2) ~= size(u,2):
        #     R = R[:,u]   # remove empty components
        if t > 1:
            diff = llh[t-1]-llh[t-2]
            eps = abs(diff)
            converged = ( eps < tol*abs(llh[t-1]) )
        
        [mu, si, pi] = maximization(X,W,R)
        [R, llh[t]] = expectation(X, W, mu, si, pi)
    

    if converged:
        print('Converged in', t-1,'steps.')
    else:
        print('Not converged in ', maxiter, ' steps.')

    return [mu, si, pi]
## END EMGM ----------------------------------------------------------------

# --------------------------------------------------------------------------
# Initialization with k-means algorithm 
# --------------------------------------------------------------------------
def initialization(X, nGM):

    [_,idx] = sp.cluster.vq.kmeans2(X.T, nGM, iter=10) # idx = kmeans(X.T,nGM,'Replicates',10)
    R   = dummyvar(idx)
    return R

# --------------------------------------------------------------------------
# ...
# --------------------------------------------------------------------------
def expectation(X, W, mu, si, pi):
    n = np.size(X, axis=1)
    k = np.size(mu, axis=1)

    logpdf = np.zeros([n,k])
    for i in range(k):
        logpdf[:,i] = loggausspdf(X, mu[:,i], si[:,:,i])


    logpdf = logpdf + np.log(pi)     # logpdf = bsxfun(@plus,logpdf,log(pi))
    T      = logsumexp(logpdf,1)
    llh    = np.sum(W*T)/np.sum(W)
    logR   = logpdf - T              # logR = bsxfun(@minus,logpdf,T)
    R      = np.exp(logR)
    return [R, llh]


# --------------------------------------------------------------------------
# ...
# --------------------------------------------------------------------------
def maximization(X, W, R):
    R = W*R
    d = np.size(X, axis=0)
    k = np.size(R, axis=1)

    nk = np.sum(R,axis=0)
    w  = nk/np.sum(W)
    mu = np.matmul(X,R)/nk.reshape(-1,1)   # TODO: maybe change to reshape(1,-1)?

    Sigma = np.zeros((d,d,k))
    sqrtR = np.sqrt(R)
    for i in range(k):
        Xo = X-mu[:,i].reshape(-1,1)        # Xo = bsxfun(@minus,X,mu(:,i))
        Xo = Xo*sqrtR[:,i].reshape(1,-1)    # Xo = bsxfun(@times,Xo,sqrtR(:,i)')
        Sigma[:,:,i] = np.matmul(Xo,Xo.T)/nk[i]
        Sigma[:,:,i] = Sigma[:,:,i]+np.eye(d)*(1e-6) # add a prior for numerical stability

    return [mu, Sigma, w]

# --------------------------------------------------------------------------
# ...
# --------------------------------------------------------------------------
def loggausspdf(X, mu, Sigma):
    d = np.size(X, axis=0)
    X = X-mu.reshape(-1,1)                   # X = bsxfun(@minus,X,mu)
    U = np.linalg.cholesky(Sigma).T.conj()
    Q = np.linalg.solve(U.T, X)
    # q = np.dot(Q[0,:],Q[0,:])  # quadratic term (M distance)
    q = np.sum(Q*Q, axis=0)      # quadratic term (M distance)
    c = d*np.log(2*np.pi)+2*np.sum(np.log(np.diag(U)))   # normalization constant
    y = -(c+q)/2
    return y

# --------------------------------------------------------------------------
# Compute log(sum(exp(x),dim)) while avoiding numerical underflow.
#   By default dim = 0 (columns).
# Written by Michael Chen (sth4nth@gmail.com).
# --------------------------------------------------------------------------
def logsumexp(x, dim=0):
    # subtract the largest in each column
    y = np.max(x, axis=dim).reshape(-1,1)
    x = x - y                  #x = bsxfun(@minus,x,y)
    tmp1 = np.exp(x)
    tmp2 = np.sum(tmp1, axis=dim)
    tmp3 = np.log(tmp2)
    # s = y + np.log(np.sum(np.exp(x),axis=dim))
    s = y + tmp3.reshape(-1,1)
    # if a bug occurs here, maybe find a better translation from matlab
    i = np.where(np.invert(np.isfinite(y).squeeze()))
    s[i] = y[i] 
    
    return s

# --------------------------------------------------------------------------
# Translation of the Matlab-function "dummyvar()" to Python
# --------------------------------------------------------------------------
def dummyvar(idx):
    n = np.max(idx)+1
    d = np.zeros([len(idx),n],int)
    for i in range(len(idx)):
        d[i,idx[i]] = 1
    return d
## END FILE