# -*- coding: utf-8 -*-
"""
Created on Mon May 05 17:29:56 2014

Author: Josef Perktold
"""

import os
import numpy as np
import pandas as pd
from scipy import stats

from numpy.testing import assert_allclose, assert_equal, assert_warns

from statsmodels.regression.linear_model import OLS, WLS, GLS
from statsmodels.tools.tools import add_constant
from statsmodels.tools.sm_exceptions import InvalidTestWarning

from statsmodels.sandbox.regression.penalized import TheilGLS


class TestTheilTextile(object):

    @classmethod
    def setup_class(cls):

        cur_dir = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(cur_dir, "results",
                                "theil_textile_predict.csv")
        cls.res_predict = pd.read_csv(filepath, sep=",")

        names = "year	lconsump	lincome	lprice".split()

        data = np.array('''\
        1923	1.99651	1.98543	2.00432
        1924	1.99564	1.99167	2.00043
        1925	2	2	2
        1926	2.04766	2.02078	1.95713
        1927	2.08707	2.02078	1.93702
        1928	2.07041	2.03941	1.95279
        1929	2.08314	2.04454	1.95713
        1930	2.13354	2.05038	1.91803
        1931	2.18808	2.03862	1.84572
        1932	2.18639	2.02243	1.81558
        1933	2.20003	2.00732	1.78746
        1934	2.14799	1.97955	1.79588
        1935	2.13418	1.98408	1.80346
        1936	2.22531	1.98945	1.72099
        1937	2.18837	2.0103	1.77597
        1938	2.17319	2.00689	1.77452
        1939	2.2188	2.0162	1.78746'''.split(), float).reshape(-1, 4)


        endog = data[:, 1]
        # constant at the end to match Stata
        exog = np.column_stack((data[:, 2:], np.ones(endog.shape[0])))

        #prior(lprice -0.7 0.15 lincome 1 0.15) cov(lprice lincome -0.01)
        r_matrix = np.array([[1, 0, 0], [0, 1, 0]])
        r_mean = [1, -0.7]

        cov_r = np.array([[0.15**2, -0.01], [-0.01, 0.15**2]])
        mod = TheilGLS(endog, exog, r_matrix, q_matrix=r_mean, sigma_prior=cov_r)
        cls.res1 = mod.fit(cov_type='data-prior')
        #cls.res1._cache['scale'] = 0.0001852252884817586 # from tg_mixed
        cls.res1._cache['scale'] = 0.00018334123641580062 # from OLS
        from .results import results_theil_textile as resmodule
        cls.res2 = resmodule.results_theil_textile


    def test_basic(self):
        pt = self.res2.params_table[:,:6].T
        params2, bse2, tvalues2, pvalues2, ci_low, ci_upp = pt
        assert_allclose(self.res1.params, params2, rtol=2e-6)

        #TODO tgmixed seems to use scale from initial OLS, not from final res
        # np.sqrt(res.scale / res_ols.scale)
        # see below mse_resid which is equal to scale
        corr_fact = 0.9836026210570028
        corr_fact = 0.97376865041463734
        corr_fact = 1
        assert_allclose(self.res1.bse / corr_fact, bse2, rtol=2e-6)
        assert_allclose(self.res1.tvalues  * corr_fact, tvalues2, rtol=2e-6)
        # pvalues are very small
        #assert_allclose(self.res1.pvalues, pvalues2, atol=2e-6)
        #assert_allclose(self.res1.pvalues, pvalues2, rtol=0.7)
        ci = self.res1.conf_int()
        # not scale corrected
        assert_allclose(ci[:,0], ci_low, rtol=0.01)
        assert_allclose(ci[:,1], ci_upp, rtol=0.01)
        assert_allclose(self.res1.rsquared, self.res2.r2, rtol=2e-6)

        # Note: tgmixed is using k_exog for df_resid
        corr_fact = self.res1.df_resid / self.res2.df_r
        assert_allclose(np.sqrt(self.res1.mse_resid * corr_fact),
                        self.res2.rmse, rtol=2e-6)

        assert_allclose(self.res1.fittedvalues,
                        self.res_predict['fittedvalues'], atol=5e7)

    def test_other(self):
        tc = self.res1.test_compatibility()
        assert_allclose(np.squeeze(tc[0]), self.res2.compat, rtol=2e-6)
        assert_allclose(np.squeeze(tc[1]), self.res2.pvalue, rtol=2e-6)

        frac = self.res1.share_data()
        # TODO check again, I guess tgmixed uses final scale in hatmatrix
        # but I'm not sure, it passed in previous version, but now we override
        # scale with OLS scale
        # assert_allclose(frac, self.res2.frac_sample, rtol=2e-6)
        # regression tests:
        assert_allclose(frac, 0.6946116246864239, rtol=2e-6)


    def test_no_penalization(self):
        res_ols = OLS(self.res1.model.endog, self.res1.model.exog).fit()
        res_theil = self.res1.model.fit(pen_weight=0, cov_type='data-prior')
        assert_allclose(res_theil.params, res_ols.params, rtol=1e-10)
        assert_allclose(res_theil.bse, res_ols.bse, rtol=1e-10)

    def test_smoke(self):
        self.res1.summary()


class CheckEquivalenceMixin(object):

    tol = {'default': (1e-4, 1e-20)}

    @classmethod
    def get_sample(cls):
        np.random.seed(987456)
        nobs, k_vars = 200, 5
        beta = 0.5 * np.array([0.1, 1, 1, 0, 0])
        x = np.random.randn(nobs, k_vars)
        x[:, 0] = 1
        y = np.dot(x, beta) + 2 * np.random.randn(nobs)
        return y, x

    def test_attributes(self):

        attributes_fit = ['params', 'rsquared', 'df_resid', 'df_model',
                          'llf', 'aic', 'bic'
                          #'fittedvalues', 'resid'
                          ]
        attributes_inference = ['bse', 'tvalues', 'pvalues']
        import copy
        attributes = copy.copy(attributes_fit)

        if not getattr(self, 'skip_inference', False):
            attributes.extend(attributes_inference)

        for att in attributes:
            r1 = getattr(self.res1, att)
            r2 = getattr(self.res2, att)
            if not np.size(r1) == 1:
                r1 = r1[:len(r2)]

            # check if we have overwritten tolerance
            rtol, atol = self.tol.get(att, self.tol['default'])
            message = 'attribute: ' + att #+ '\n%r\n\%r' % (r1, r2)
            assert_allclose(r1, r2, rtol=rtol, atol=atol, err_msg=message)

        # models are not close enough for some attributes at high precision
        assert_allclose(self.res1.fittedvalues, self.res1.fittedvalues,
                        rtol=1e-3, atol=1e-4)
        assert_allclose(self.res1.resid, self.res1.resid,
                        rtol=1e-3, atol=1e-4)


class TestTheil1(CheckEquivalenceMixin):
    # penalize last two parameters to zero

    @classmethod
    def setup_class(cls):
        y, x = cls.get_sample()
        mod1 = TheilGLS(y, x, sigma_prior=[0, 0, 1., 1.])
        cls.res1 = mod1.fit(200000)
        cls.res2 = OLS(y, x[:, :3]).fit()

class TestTheil2(CheckEquivalenceMixin):
    # no penalization = same as OLS

    @classmethod
    def setup_class(cls):
        y, x = cls.get_sample()
        mod1 = TheilGLS(y, x, sigma_prior=[0, 0, 1., 1.])
        cls.res1 = mod1.fit(0)
        cls.res2 = OLS(y, x).fit()


class TestTheil3(CheckEquivalenceMixin):
    # perfect multicollinearity = same as OLS in terms of fit
    # inference: bse, ... is different

    @classmethod
    def setup_class(cls):
        cls.skip_inference = True
        y, x = cls.get_sample()
        xd = np.column_stack((x, x))
        #sp = np.zeros(5), np.ones(5)
        r_matrix = np.eye(5, 10, 5)
        mod1 = TheilGLS(y, xd, r_matrix=r_matrix) #sigma_prior=[0, 0, 1., 1.])
        cls.res1 = mod1.fit(0.001, cov_type='data-prior')
        cls.res2 = OLS(y, x).fit()


class TestTheilGLS(CheckEquivalenceMixin):
    # penalize last two parameters to zero

    @classmethod
    def setup_class(cls):
        y, x = cls.get_sample()
        nobs = len(y)
        weights = (np.arange(nobs) < (nobs // 2)) + 0.5
        mod1 = TheilGLS(y, x, sigma=weights, sigma_prior=[0, 0, 1., 1.])
        cls.res1 = mod1.fit(200000)
        cls.res2 = GLS(y, x[:, :3], sigma=weights).fit()


class TestTheilLinRestriction(CheckEquivalenceMixin):
    # impose linear restriction with small uncertainty - close to OLS

    @classmethod
    def setup_class(cls):
        y, x = cls.get_sample()
        #merge var1 and var2
        x2 = x[:, :2].copy()
        x2[:, 1] += x[:, 2]
        #mod1 = TheilGLS(y, x, r_matrix =[[0, 1, -1, 0, 0]])
        mod1 = TheilGLS(y, x[:, :3], r_matrix =[[0, 1, -1]])
        cls.res1 = mod1.fit(200000)
        cls.res2 = OLS(y, x2).fit()

        # adjust precision, careful: cls.tol is mutable
        tol = {'pvalues': (1e-4, 2e-7),
               'tvalues': (5e-4, 0)}
        tol.update(cls.tol)
        cls.tol = tol


class TestTheilLinRestrictionApprox(CheckEquivalenceMixin):
    # impose linear restriction with some uncertainty

    @classmethod
    def setup_class(cls):
        y, x = cls.get_sample()
        #merge var1 and var2
        x2 = x[:, :2].copy()
        x2[:, 1] += x[:, 2]
        #mod1 = TheilGLS(y, x, r_matrix =[[0, 1, -1, 0, 0]])
        mod1 = TheilGLS(y, x[:, :3], r_matrix =[[0, 1, -1]])
        cls.res1 = mod1.fit(100)
        cls.res2 = OLS(y, x2).fit()

        # adjust precision, careful: cls.tol is mutable
        import copy
        tol = copy.copy(cls.tol)
        tol2 = {'default': (0.15,  0),
                'params':  (0.05, 0),
                'pvalues': (0.02, 0.001),
                }
        tol.update(tol2)
        cls.tol = tol


class TestTheilPanel(object):

    @classmethod
    def setup_class(cls):
        #example 3
        nobs = 300
        nobs_i = 5
        n_groups = nobs // nobs_i
        k_vars = 3

        from statsmodels.sandbox.panel.random_panel import PanelSample
        dgp = PanelSample(nobs, k_vars, n_groups)
        dgp.group_means = 2 + np.random.randn(n_groups) #add random intercept
        print('seed', dgp.seed)
        y = dgp.generate_panel()
        x = np.column_stack((dgp.exog[:,1:],
                             dgp.groups[:,None] == np.arange(n_groups)))
        cls.dgp = dgp
        cls.endog = y
        cls.exog = x
        cls.res_ols = OLS(y, x).fit()

    def test_regression(self):
        y = self.endog
        x = self.exog
        n_groups, k_vars = self.dgp.n_groups, self.dgp.k_vars

        R = np.c_[np.zeros((n_groups, k_vars-1)), np.eye(n_groups)]
        r = np.zeros(n_groups)
        R = np.c_[np.zeros((n_groups-1, k_vars)),
                  np.eye(n_groups-1)-1./n_groups * np.ones((n_groups-1, n_groups-1))]
        r = np.zeros(n_groups-1)
        R[:, k_vars-1] = -1

        lambd = 1 #1e-4
        mod = TheilGLS(y, x, r_matrix=R, q_matrix=r, sigma_prior=lambd)
        res = mod.fit()

        # regression test
        params1 = np.array([
            0.96518694,  1.06152005,  0.31844136,  3.02747485,  3.25308031,
            3.76229199,  1.99795797,  3.9831158 ,  3.1055317 ,  1.91599103,
            4.5354633 ,  4.14332517,  3.69462963,  3.79567255,  2.18633118,
            2.02848738,  3.74269763,  3.60041509,  3.27734962,  2.47771329,
            3.23858674,  4.2973348 ,  3.98013994,  3.73415254,  2.88870379,
            3.91311563,  3.71043309,  1.80506601,  3.78067131,  1.77164485,
            3.88247   ,  3.28328127,  3.1313951 ,  3.03006754,  3.31012921,
            3.08761618,  2.96735903,  1.54005178,  1.27778498,  1.47949121,
            4.87184321,  3.03812406,  3.43574332,  2.16983158,  4.45339409,
            2.64502381,  4.04767553,  4.42282326,  2.40153298,  3.55409206,
            2.71256315,  3.32197196,  3.56054788,  2.58639318,  0.96230275,
            1.8382348 ,  2.30788361,  2.49415769,  0.74777288,  3.04014659,
            1.82256153,  4.89165865])
        assert_allclose(res.params, params1)

        pen_weight_aicc = mod.select_pen_weight(method='aicc')
        pen_weight_gcv = mod.select_pen_weight(method='gcv')
        pen_weight_cv = mod.select_pen_weight(method='cv')
        pen_weight_bic = mod.select_pen_weight(method='bic')
        assert_allclose(pen_weight_gcv, pen_weight_aicc, rtol=0.1)
        # regression tests:
        assert_allclose(pen_weight_aicc, 2.98779297, rtol=1e-4)
        assert_allclose(pen_weight_gcv,  2.69970703, rtol=1e-4)
        assert_allclose(pen_weight_bic, 5.76005859, rtol=1e-4)
        assert_allclose(pen_weight_cv, 1.3, rtol=1e-4)


    def test_combine_subset_regression(self):
        # split sample into two, use first sample as prior for second
        endog = self.endog
        exog = self.exog
        nobs = len(endog)

        n05 = nobs // 2
        np.random.seed(987125)
        # shuffle to get random subsamples
        shuffle_idx = np.random.permutation(np.arange(nobs))
        ys = endog[shuffle_idx]
        xs = exog[shuffle_idx]
        k = 10
        res_ols0 = OLS(ys[:n05], xs[:n05, :k]).fit()
        res_ols1 = OLS(ys[n05:], xs[n05:, :k]).fit()

        w = res_ols1.scale / res_ols0.scale   #1.01
        mod_1 = TheilGLS(ys[n05:], xs[n05:, :k], r_matrix=np.eye(k), q_matrix=res_ols0.params, sigma_prior=w * res_ols0.cov_params())
        res_1p = mod_1.fit(cov_type='data-prior')
        res_1s = mod_1.fit(cov_type='sandwich')
        res_olsf = OLS(ys, xs[:, :k]).fit()

        assert_allclose(res_1p.params, res_olsf.params, rtol=1e-9)
        corr_fact = 0.96156318 # corrct for differences in scale computation
        assert_allclose(res_1p.bse, res_olsf.bse * corr_fact, rtol=1e-3)

        # regression test, does not verify numbers
        # especially why are these smaller than OLS on full sample
        # in larger sample, nobs=600, those were close to full OLS
        bse1 = np.array([
            0.27609914,  0.15808869,  0.39880789,  0.78583194,  0.68619331,
            0.56252314,  0.55757562,  0.68538523,  0.39695081,  0.55988991])
        assert_allclose(res_1s.bse, bse1, rtol=1e-7)
