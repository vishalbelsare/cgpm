# -*- coding: utf-8 -*-

# Copyright (c) 2015-2016 MIT Probabilistic Computing Project

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
 
import pytest
import numpy as np

from itertools import product

from cgpm.utils import config as cu
from cgpm.utils import general as gu
from cgpm.utils import test as tu
from cgpm.utils.general import logsumexp

from cgpm.mixtures.view import View

OUT = 'tests/resources/out/'

def initialize_view():
    data = np.array([[1, 1]])
    D = len(data[0])
    outputs = range(D)
    X = {c: data[:, i].tolist() for i, c in enumerate(outputs)}
    view = View(
        X,
        outputs=[1000] + outputs,
        alpha=1.,
        cctypes=['bernoulli']*D,
        hypers={
            i: {'alpha': 1., 'beta': 1.} for i in outputs},
        Zr=[0])
    return view

def test_unidimensional_logpdf_hypothetical():
    view = initialize_view()

    # P(x[1,0] = 1) = 7./12
    # Hypothetical row: rowid=1
    query = {0: 1}
    math_out = np.log(7./12)
    test_out = view.logpdf(rowid=1, query=query)
    assert np.allclose(math_out, test_out)

def test_unidimensional_logpdf_nonhypothetical():
    view = initialize_view()

    # P(x[0,0] = 1) = 2./3
    # Non-hypothetical row: rowid=0
    query = {0: 1}
    math_out = np.log(2./3)
    test_out = view.logpdf(rowid=0, query=query) 
    assert np.allclose(math_out, test_out)

def test_unidimensional_crp_logpdf_hypothetical():
    view = initialize_view()

    # P(z[1] = 0) = 1./2
    # Hypothetical row: rowid=1
    query = {view.exposed_latent: 0}
    math_out = np.log(1./2)
    test_out = view.logpdf(rowid=1, query=query) 
    assert np.allclose(math_out, test_out)

def test_unidimensional_logpdf_crp_nonhypothetical():
    view = initialize_view()    

    # P(z[0] = 0) = 1.
    # Non-hypothetical row: rowid=0
    query = {view.exposed_latent: 0}
    math_out = np.log(1)
    test_out = view.logpdf(rowid=0, query=query) 
    assert np.allclose(math_out, test_out)

def test_unidimensional_logpdf_crp_conditional_hypothetical():
    view = initialize_view()    

    # P(x[1,0] = 1, z[1] = 0) = 1./4
    # Hypothetical row: rowid=1
    query = {0: 1}
    evidence = {view.exposed_latent: 0}
    math_out = np.log(2./3)
    test_out = view.logpdf(rowid=1, query=query, evidence=evidence) 
    assert np.allclose(math_out, test_out)

def test_unidimensional_logpdf_crp_joint_hypothetical():
    view = initialize_view()    

    # P(x[1,0] = 1, z[1] = 0) = 1./4
    # Hypothetical row: rowid=1
    query = {view.exposed_latent: 0, 0: 1}
    math_out = np.log(1./3)
    test_out = view.logpdf(rowid=1, query=query) 
    assert np.allclose(math_out, test_out)

def test_bidimensional_logpdf():
    view = initialize_view()

    # P(x[1,:] = [1,1]) = 25./72
    # Hypothetical row: rowid=1
    query = {0: 1, 1: 1}
    math_out = np.log(25./72)
    test_out = view.logpdf(rowid=1, query=query)
    assert np.allclose(math_out, test_out)

    # P(x[0,0] = 1) = (2./3)**2
    # Non-hypothetical row: rowid=0
    query = {0: 1, 1: 1}
    math_out = 2*np.log(2./3)
    test_out = view.logpdf(rowid=0, query=query) 
    assert np.allclose(math_out, test_out)


# -- Tests from Feras -- #
def retrieve_view():
    data = np.asarray([
        [1.1,   -2.1,    0],  # rowid=0
        [2.,      .1,    0],  # rowid=1
        [1.5,      1,   .5],  # rowid=2
        [4.7,    7.4,   .5],  # rowid=3
        [5.2,    9.6,   .5],  # rowid=4
    ])

    outputs = [0,1,2,]

    return View(
        {c: data[:,i].tolist() for i, c in enumerate(outputs)},
        outputs=[1000] + outputs,
        alpha=2.,
        cctypes=['normal'] * len(outputs),
        Zr=[0,0,0,1,1,]
    )

def test_crp_logpdf():
    view = retrieve_view()

    crp_normalizer = view.alpha() + 5.
    cluster_logps = np.log(np.asarray([
        3 / crp_normalizer,
        2 / crp_normalizer,
        view.alpha() / crp_normalizer
    ]))

    # Test the crp probabilities agree for a hypothetical row.
    for k in [0,1,2]:
        expected_logpdf = cluster_logps[k]
        crp_logpdf = view.crp.clusters[0].logpdf(None, {view.outputs[0]: k})
        assert np.allclose(expected_logpdf, crp_logpdf)
        view_logpdf = view.logpdf(None, {view.outputs[0]: k})
        assert np.allclose(view_logpdf, crp_logpdf)
