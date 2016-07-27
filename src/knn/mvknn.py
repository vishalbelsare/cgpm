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

from collections import OrderedDict

import numpy as np

from sklearn.neighbors import KDTree

from cgpm.cgpm import CGpm
from cgpm.utils import data as du
from cgpm.utils import general as gu


class MultivariateKnn(CGpm):
    """Multivariate K-Nearest-Neighbors builds ML models on a per-query basis.

    TODO: Migrate description from Github Issue #128.

    TODO:
    [x] Implement the nearest neighbor search for a datapoint given Q,E.
        [x] Euclidean embedding of the categoricals.
    [] Implement simulate by chaining regression models.
    """

    def __init__(self, outputs, inputs, K=None, distargs=None, params=None,
            rng=None):
        # Default arguments.
        if params is None:
            params = {}
        if rng is None:
            rng = gu.gen_rng(1)
        # No inputs allowed.
        if inputs:
            raise ValueError('KNN rejects inputs: %s.' % inputs)
        # At least one output.
        if len(outputs) < 1:
            raise ValueError('KNN needs >= 1 outputs: %s.' % outputs)
        # Unique outputs.
        if len(set(outputs)) != len(outputs):
            raise ValueError('Duplicate outputs: %s.' % outputs)
        # Ensure outputs in distargs.
        if not distargs or 'outputs' not in distargs:
            raise ValueError('Missing distargs: %s.' % distargs)
        # Ensure K is positive.
        if K is None or K < 1:
            raise ValueError('Invalid K for nearest neighbors: %s.' % K)
        # Ensure stattypes and statargs in distargs['outputs]'
        if 'stattypes' not in distargs['outputs']\
                or 'statargs' not in distargs['outputs']:
            raise ValueError('Missing output stattypes: %s.' % distargs)
        # Ensure stattypes correct length.
        if len(distargs['outputs']['stattypes']) != len(outputs):
            raise ValueError('Wrong number of stattypes: %s.' % distargs)
        # Ensure statargs correct length.
        if len(distargs['outputs']['statargs']) != len(outputs):
            raise ValueError('Wrong number of statargs: %s.' % distargs)
        # Ensure number of categories provided as k.
        if any('k' not in distargs['outputs']['statargs'][i]
                for i in xrange(len(outputs))
                if distargs['outputs']['stattypes'][i] != 'numerical'):
            raise ValueError('Missing number of categories k: %s' % distargs)
        # Build the object.
        self.rng = rng
        # Varible indexes.
        self.outputs = outputs
        self.inputs = []
        # Distargs.
        self.stattypes = distargs['outputs']['stattypes']
        self.statargs = distargs['outputs']['statargs']
        self.levels = {
            o: self.statargs[i]['k']
            for i, o in enumerate(outputs) if self.stattypes[i] != 'numerical'
        }
        # Dataset.
        self.data = OrderedDict()
        self.N = 0
        # Ordering of the chain.
        self.ordering = list(self.rng.permutation(self.outputs))
        # Number of nearest neighbors.
        self.K = K

    def incorporate(self, rowid, query, evidence=None):
        # No duplicate observation.
        if rowid in self.data:
            raise ValueError('Already observed: %d.' % rowid)
        # No evidence.
        if evidence:
            raise ValueError('No evidence allowed: %s.' % evidence)
        # Missing query.
        if not query:
            raise ValueError('No query specified: %s.' % query)
        # No unknown variables.
        if any(q not in self.outputs for q in query):
            raise ValueError('Unknown variables: (%s,%s).'
                % (query, self.outputs))
        # Incorporate observed variables.
        x = [query.get(q, np.nan) for q in self.outputs]
        # Update dataset and counts.
        self.data[rowid] = x
        self.N += 1

    def unincorporate(self, rowid):
        try:
            del self.data[rowid]
        except KeyError:
            raise ValueError('No such observation: %d.' % rowid)
        self.N -= 1

    def logpdf(self, rowid, query, evidence=None):
        return 0

    def simulate(self, rowid, query, evidence=None, N=None):
        if self.N < self.K:
            raise ValueError('Knn requires at least K observations.')
        evidence = self.populate_evidence(rowid, query, evidence)
        if not query: raise ValueError('No query: %s.' % query)
        if any(q not in self.outputs for q in query):
            raise ValueError('Unknown variables: (%s,%s).'
                % (query, self.outputs))
        if any(q in evidence for q in query):
            raise ValueError('Duplicate variable: (%s,%s).' % (query, evidence))
        # XXX Disable queries without evidence for now.
        if not evidence:
            raise ValueError('KNN requires at least 1 evidence: %s.' % evidence)

    def logpdf_score(self):
        pass


    def transition(self, N=None):
        pass


    # --------------------------------------------------------------------------
    # Internal.

    def _find_nearest_neighbors(self, query, evidence, K=None):
        if not evidence:
            raise ValueError('No evidence in neighbor search: %s.' % evidence)
        if any(np.isnan(v) for v in evidence.values()):
            raise ValueError('Nan evidence in neighbor search: %s.' % evidence)
        # Extract the query, evidence variables from the dataset.
        lookup = list(query) + list(evidence)
        D = self._dataset(lookup)
        # By default return entire dataset sorted by distances.
        if K is None:
            K = len(D)
        if K <= 0:
            raise ValueError('Non-positive K in neighbor search: %s' % K)
        # Not enough neighbors: crash for now. Workarounds include:
        # (i) reduce  K, (ii) randomly drop evidences, or (iii) impute dataset.
        if len(D) < K:
            raise ValueError('Not enough neighbors: %s.' % ((query, evidence),))
        # Code the dataset.
        D_qr_code = self._dummy_code(D[:,:len(query)], lookup[:len(query)])
        D_ev_code = self._dummy_code(D[:,len(query):], lookup[len(query):])
        D_code = np.column_stack((D_qr_code, D_ev_code))
        # Run nearest neighbor search on the evidence only.
        evidence_code = self._dummy_code([evidence.values()], evidence.keys())
        dist, neighbors = KDTree(D_ev_code).query(evidence_code, k=len(D))
        # import ipdb; ipdb.set_trace()
        # Check for duplicate distances, in which case extend the search.
        valid = [i for i, d in enumerate(dist[0]) if d <= dist[0][K-1]]
        neighbors_v = self.rng.choice(
            neighbors[0][valid], replace=False, size=K)
        # For each neighbor find its nearest five on the full dataset.
        K_resample = min(5, K)
        exemplars = KDTree(D_code).query(D_code[neighbors_v], k=K_resample)
        # Return dataset.
        return D[neighbors[0][:K]]

    def _dummy_code(self, D, variables):
        levels = {variables.index(l): self.levels[l]
            for l in variables if l in self.levels}
        return D if not levels\
            else np.asarray([du.dummy_code(r, levels) for r in D])

    def _find_exemplars(self, query, evidence):
        # Find all the nearest neighbors based on evidence.
        pass

    def _dataset(self, query):
        indexes = [self.outputs.index(q) for q in query]
        X = np.asarray(self.data.values())[:,indexes]
        return X[~np.any(np.isnan(X), axis=1)]

    def _stattypes(self, query):
        indexes = [self.outputs.index(q) for q in query]
        return [self.stattypes[i] for i in indexes]

    def populate_evidence(self, rowid, query, evidence):
        if evidence is None:
            evidence = {}
        if rowid in self.data:
            values = self.data[rowid]
            assert len(values) == len(self.outputs)
            evidence_obs = {e:v for e,v in zip(self.outputs, values)
                if not np.isnan(v) and e not in query and e not in evidence
            }
            evidence = gu.merged(evidence, evidence_obs)
        return evidence

    def get_params(self):
        return {
            'ordering': self.ordering,
        }

    def get_distargs(self):
        return {
            'outputs': {
                'stattypes': self.stattypes,
                'statargs': self.statargs,
            },
        }

    @staticmethod
    def name():
        return 'multivariate_knn'

    # --------------------------------------------------------------------------
    # Serialization.

    def to_metadata(self):
        metadata = dict()
        metadata['outputs'] = self.outputs
        metadata['inputs'] = self.inputs
        metadata['distargs'] = self.get_distargs()
        metadata['N'] = self.N
        metadata['data'] = self.data.items()

        metadata['params'] = dict()
        metadata['params']['ordering'] = self.ordering

        metadata['factory'] = ('cgpm.knn.mvknn', 'MultivariateKnn')
        return metadata

    @classmethod
    def from_metadata(cls, metadata, rng=None):
        if rng is None:
            rng = gu.gen_rng(0)
        knn = cls(
            outputs=metadata['outputs'],
            inputs=metadata['inputs'],
            distargs=metadata['distargs'],
            params=metadata['params'],
            rng=rng)
        knn.data = OrderedDict(metadata['data'])
        knn.N = metadata['N']
        return knn