# -*- coding: utf-8 -*-

# The MIT License (MIT)

# Copyright (c) 2014 Baxter S. Eaves Jr,
# Copyright (c) 2015-2016 MIT Probabilistic Computing Project

# Lead Developer: Feras Saad <fsaad@mit.edu>

# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the
# following conditions:

# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN
# NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE
# USE OR OTHER DEALINGS IN THE SOFTWARE.

import numpy as np
import math

from scipy.stats import norm
from scipy.stats import geom

from gpmcc import dim
import gpmcc.utils.general as gu
import gpmcc.utils.config as cu

def gen_data_table(n_rows, view_weights, cluster_weights, cctypes, distargs,
        separation):
    """Generates data, partitions, and Dim.

     Parameters
     ----------
     n_rows : int
        Mumber of rows (data points) to generate.
     view_weights : np.ndarray
        An n_views length list of floats that sum to one. The weights indicate
        the proportion of columns in each view.
    cluster_weights : np.ndarray
        An n_views length list of n_cluster length lists that sum to one.
        The weights indicate the proportion of rows in each cluster.
     cctypes : list<str>
        n_columns length list of string specifying the distribution types for
        each column.
     distargs : list
        List of distargs for each column (see documentation for each data type
            for info on distargs).
     separation : list
        An n_cols length list of values between [0,1], where seperation[i] is
        the seperation of clusters in column i. Values closer to 1 imply higher
        seperation.

     Returns
     -------
     T : np.ndarray
        An (n_cols, n_rows) matrix, where each row T[i,:] is the data for
        column i (tranpose of a design matrix).
    Zv : list
        An n_cols length list of integers, where Zv[i] is the view assignment
        of column i.
    Zc : list<list>
        An n_view length list of lists, where Zc[v][r] is the cluster assignment
        of row r in view v.

    Example
    -------
    >>> n_rows = 500
    >>> view_weights = [.2, .8]
    >>> cluster_weights = [[.3, .2, .5], [.4, .6]]
    >>> cctypes = ['lognormal','normal','poisson','categorical',
    ...     'vonmises', 'bernoulli']
    >>> distargs = [None, None, None, {'k':8}, None, None]
    >>> separation = [.8, .7, .9, .6, .7, .85]
    >>> T, Zv, Zc, dims = tu.gen_data_table(n_rows, view_weights,
    ...     cluster_weights, dists, distargs, separation)
    """
    n_cols = len(cctypes)
    Zv, Zc = gen_partition_from_weights(n_rows, n_cols, view_weights,
        cluster_weights)
    T = np.zeros((n_cols, n_rows))

    for col in xrange(n_cols):
        cctype = cctypes[col]
        args = distargs[col]
        view = Zv[col]
        Tc = _gen_data[cctype](Zc[view], separation[col], distargs=args)
        T[col] = Tc

    return T, Zv, Zc

def gen_dims_from_structure(T, Zv, Zc, cctypes, distargs):
    n_cols = len(Zv)
    dims = []
    for col in xrange(n_cols):
        v = Zv[col]
        cctype = cctypes[col]
        dim_c = dim.Dim(T[col], cctype, col, Zr=Zc[v],
            distargs=distargs[col])
        dims.append(dim_c)
    return dims

def _gen_beta_data_column(Z, separation=.9, distargs=None):
    n_rows = len(Z)
    K = np.max(Z)+1
    alphas = np.linspace(.5 -.5*separation*.85, .5 + .5*separation*.85, K)
    Tc = np.zeros(n_rows)
    for r in range(n_rows):
        cluster = Z[r]
        alpha = alphas[cluster]
        beta = (1.0-alpha)*20.0*(norm.pdf(alpha,.5,.25))
        alpha *= 20.0*norm.pdf(alpha,.5,.25)
        # beta *= 10.0
        Tc[r] = np.random.beta(alpha, beta)

    return Tc

def _gen_normal_data_column(Z, separation=.9, distargs=None):
    n_rows = len(Z)

    Tc = np.zeros(n_rows)
    for r in range(n_rows):
        cluster = Z[r]
        mu = cluster*(5.0*separation)
        sigma = 1.0
        Tc[r] = np.random.normal(loc=mu, scale=sigma)

    return Tc

def _gen_vonmises_data_column(Z, separation=.9, distargs=None):
    n_rows = len(Z)

    num_clusters =  max(Z)+1
    sep = (2*math.pi/num_clusters)

    mus = [c*sep for c in range(num_clusters)]
    std = sep/(5.0*separation**.75)
    k = 1/(std*std)

    Tc = np.zeros(n_rows)
    for r in range(n_rows):
        cluster = Z[r]
        mu = mus[cluster]
        Tc[r] = np.random.vonmises(mu, k) + math.pi

    return Tc

def _gen_poisson_data_column(Z, separation=.9, distargs=None):
    n_rows = len(Z)
    Tc = np.zeros(n_rows)

    for r in range(n_rows):
        cluster = Z[r]
        lam = (cluster)*(4.0*separation)+1
        Tc[r] = np.random.poisson(lam)

    return Tc

def _gen_exponential_data_column(Z, separation=.9, distargs=None):
    n_rows = len(Z)
    Tc = np.zeros(n_rows)

    for r in range(n_rows):
        cluster = Z[r]
        mu = (cluster)*(4.0*separation)+1
        Tc[r] = np.random.exponential(mu)

    return Tc

def _gen_geometric_data_column(Z, separation=.9, distargs=None):
    n_rows = len(Z)
    Tc = np.zeros(n_rows)
    K = np.max(Z)+1

    ps = np.linspace(.5 -.5*separation*.85, .5 + .5*separation*.85, K)
    Tc = np.zeros(n_rows)
    for r in range(n_rows):
        cluster = Z[r]
        Tc[r] = geom.rvs(ps[cluster], loc=-1)

    return Tc

def _gen_lognormal_data_column(Z, separation=.9, distargs=None):
    n_rows = len(Z)

    if separation > .9:
        separation = .9

    Tc = np.zeros(n_rows)
    for r in range(n_rows):
        cluster = Z[r]
        mu = cluster*(.9*separation**2)
        Tc[r] = np.random.lognormal(mean=mu,
            sigma=(1.0-separation)/(cluster+1.0))

    return Tc

def _gen_bernoulli_data_column(Z, separation=.9, distargs=None):
    n_rows = len(Z)

    Tc = np.zeros(n_rows)
    K = max(Z)+1
    thetas = np.linspace(0.0,separation,K)
    for r in range(n_rows):
        cluster = Z[r]
        theta = thetas[cluster]
        x = 0.0
        if np.random.random() < theta:
            x = 1.0
        Tc[r] = x

    return Tc

def _gen_categorical_data_column(Z, separation=.9, distargs=None):
    n_rows = len(Z)
    k = distargs['k']
    if separation > .95:
        separation = .95
    Tc = np.zeros(n_rows, dtype=int)
    C = max(Z)+1
    theta_arrays = [np.random.dirichlet(np.ones(k)*(1.0-separation), 1)
        for _ in range(C)]
    for r in range(n_rows):
        cluster = Z[r]
        thetas = theta_arrays[cluster][0]
        x = int(gu.pflip(thetas))
        Tc[r] = x
    return Tc

def gen_partition_from_weights(n_rows, n_cols, view_weights, clusters_weights):
    n_views = len(view_weights)
    Zv = [v for v in range(n_views)]
    for _ in xrange(n_cols - n_views):
        v = gu.pflip(view_weights)
        Zv.append(v)

    np.random.shuffle(Zv)
    assert len(Zv) == n_cols

    Zc = []
    for v in xrange(n_views):
        n_clusters = len(clusters_weights[v])
        Z = [c for c in xrange(n_clusters)]
        for _ in range(n_rows-n_clusters):
            c_weights = np.copy(clusters_weights[v])
            c = gu.pflip(c_weights)
            Z.append(c)
        np.random.shuffle(Z)
        Zc.append(Z)

    assert len(Zc) == n_views
    assert len(Zc[0]) == n_rows

    return Zv, Zc

def gen_partition_crp(n_rows, n_cols, n_views, alphas):
    Zv = [v for v in range(n_views)]
    for _ in range(n_cols-n_views):
        Zv.append(np.random.randrange(n_views))
    np.random.shuffle(Zv)
    Zc = []
    for v in range(n_views):
        Zc.append(gu.simulate_crp(n_rows, alphas[v]))

    return Zv, Zc

def column_average_ari(Zv, Zc, cc_state_object):
    from sklearn.metrics import adjusted_rand_score
    ari = 0
    n_cols = len(Zv)
    for col in range(n_cols):
        view_t = Zv[col]
        Zc_true = Zc[view_t]

        view_i = cc_state_object.Zv[col]
        Zc_inferred = cc_state_object.views[view_i].Z.tolist()
        ari += adjusted_rand_score(Zc_true, Zc_inferred)

    return ari/float(n_cols)

def gen_sine_wave(N, noise=.5):
    x_range = [-3.0*math.pi/2.0, 3.0*math.pi/2.0]
    X = np.zeros( (N,2) )
    for i in range(N):
        x = np.random.uniform(x_range[0], x_range[1])
        y = math.cos(x)+np.random.random()*(-np.random.uniform(-noise, noise))
        X[i,0] = x
        X[i,1] = y

    T = [X[:,0],X[:,1]]
    return T

def gen_x(N, rho=.95):
    X = np.zeros( (N,2) )
    for i in range(N):
        if np.random.random() < .5:
            sigma = np.array([[1,rho],[rho,1]])
        else:
            sigma = np.array([[1,-rho],[-rho,1]])
        x = np.random.multivariate_normal(np.zeros(2), sigma)
        X[i,:] = x

    T = [X[:,0],X[:,1]]
    return T

def gen_ring(N, width=.2):
    X = np.zeros((N,2))
    for i in range(N):
        angle = np.random.uniform(0.0, 2.0*math.pi)
        distance = np.random.uniform(1.0-width, 1.0)
        X[i,0] = math.cos(angle)*distance
        X[i,1] = math.sin(angle)*distance

    T = [X[:,0],X[:,1]]
    return T

def gen_four_dots(N=200, stddev=.25):
    X = np.zeros((N,2))
    mx = [ -1, 1, -1, 1]
    my = [ -1, -1, 1, 1]
    for i in range(N):
        n = np.random.randint(4)
        x = np.random.normal(loc=mx[n], scale=stddev)
        y = np.random.normal(loc=my[n], scale=stddev)
        X[i,0] = x
        X[i,1] = y

    T = [X[:,0],X[:,1]]
    return T

_gen_data = {
    'beta_uc'           : _gen_beta_data_column,
    'normal'            : _gen_normal_data_column,
    'bernoulli'         : _gen_bernoulli_data_column,
    'categorical'       : _gen_categorical_data_column,
    'poisson'           : _gen_poisson_data_column,
    'exponential'       : _gen_exponential_data_column,
    'geometric'         : _gen_geometric_data_column,
    'lognormal'         : _gen_lognormal_data_column,
    'vonmises'          : _gen_vonmises_data_column,
}