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

"""
Find the math for these tests in
https://docs.google.com/document/d/15_JGb39TuuSup_0gIBJTuMHYs8HS4m_TzjJ-AOXnh9M/edit
"""

import numpy as np
from itertools import product
from collections import OrderedDict

from cgpm.mixtures.view import View
from cgpm.utils.general import logsumexp, merged


dpmm_data = [[1]]
 
def initialize_view():
    data = np.array(dpmm_data)
    D = data.shape[1]
    outputs = range(D)
    X = {c: data[:, i].tolist() for i, c in enumerate(outputs)}
    Zr = [0 for i in range(data.shape[1])]
    view = View(
        X,
        outputs=[1000] + outputs,
        alpha=1.,
        cctypes=['bernoulli']*D,
        hypers={
            i: {'alpha': 1., 'beta': 1.} for i in outputs},
        Zr=Zr)
    return view

def test_score_of_first_row_with_itself():
    """
    score(row 0; row 0) = score({1: {0: [1]}} ; {0: {0: [1]}}) = log(4./3)
    """

    view = initialize_view()
    logp_H1 = np.log(1./6)
    logp_H2 = np.log(1./8)
    math_out = logp_H1 - logp_H2

    test_out = view.relevance_score(target={0: {}}, query={0: {}}, debug=True)

    assert np.allclose(math_out, test_out)

def test_score_of_first_row_with_hypothetical_same_row():
    """
    score({1: {0: [1]}} ; {0: {0: [1]}}) = log(4./3)
    """

    view = initialize_view()
    logp_H1 = np.log(1./6)
    logp_H2 = np.log(1./8)
    math_out = logp_H1 - logp_H2

    test_out = view.relevance_score(target={1: {0: 1}}, query={0: {}}, debug=True)

    assert np.allclose(math_out, test_out)

def test_score_of_first_row_with_different_hypothetical_row():
    """
    score({1: {0: [0]}} ; {0: {0: [1]}}) = log(2./3)
    """

    view = initialize_view()
    logp_H1 = np.log(1./12)
    logp_H2 = np.log(1./8)
    math_out = logp_H1 - logp_H2

    test_out = view.relevance_score(
        target={1: {0: 0}}, query={0: {}}, debug=True)
    assert np.allclose(math_out, test_out)

def test_score_of_hypothetical_row_with_another_hypothetical_row():
    """
    score({2: {0: 1}} ; {1: {0: 1}}) = l1 - l2

    l1 = p({2: {0: 1, z:0}} ; {1: {0: 1, z: 0}}) + 
         p({2: {0: 1, z:1}} ; {1: {0: 1, z: 1}})
       = 3./4 * 2./3 * 2./3 * 1./2 + 
         2./3 * 1./3 * 1./2 * 1./2

    l2 = p({2: {0: 1, z:0}} ; {1: {0: 1, z: 1}}) + 
         p({2: {0: 1, z:1}} ; {1: {0: 1, z: 0}}) +
         p({2: {0: 1, z:2}} ; {1: {0: 1, z: 1}})
       = 2./3 * 1./3 * 1./2 * 1./2 +
         1./2 * 1./3 * 2./3 * 1./2 +
         1./2 * 1./3 * 1./2 * 1./2
    """
    view = initialize_view()
    
    p_11 = np.log(3./4 * 2./3 * 2./3 * 1./2)
    p_12 = np.log(2./3 * 1./3 * 1./2 * 1./2)
    l1 = logsumexp((p_11, p_12))

    p_21 = np.log(2./3 * 1./3 * 1./2 * 1./2)
    p_22 = np.log(1./2 * 1./3 * 2./3 * 1./2)
    p_23 = np.log(1./2 * 1./3 * 1./2 * 1./2)
    l2 = logsumexp((p_21, p_22, p_23))

    math_out = l1 - l2
    test_out = view.relevance_score(target={2: {0: 1}}, query={1: {0: 1}}, debug=True)

    assert np.allclose(math_out, test_out)

