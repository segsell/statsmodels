"""
Test Results for discrete models from R (mlogit package)
Replicate Greene (2003: Page 729) results.
TODO Cross check with Biogeme: http://biogeme.epfl.ch/

"""
import numpy as np

class Travelmodechoice():

    """
    R code

    library("mlogit", "TravelMode")
    names(TravelMode)<- c("individual", "mode", "choice", "ttme", "invc",
                             "invt", "gc", "hinc", "psize")
    TravelMode$hinc_air <- with(TravelMode, hinc * (mode == "air"))
    res <- mlogit(choice ~ gc + ttme + hinc_air, data = TravelMode,
                shape = "long", alt.var = "mode", reflevel = "car")
    summary(res)
    model$coefficients
    model$hessian       #the hessian of the log-likelihood at convergence

    """
    def __init__(self):
        self.nobs = 210

    def clogit_greene(self):

        """
        R results
        """

        self.params = [-0.01550151, -0.09612462, 5.20743293, 0.013287011,
                       3.86903570, 3.16319033]

        self.hessian = np.array([
                    [-7.54742053e+04,  -1.68416889e+04,   1.92371522e+02,
                    7.78063150e+03,  -7.76604449e+02,  -2.17068300e+01],
                    [ -1.68416889e+04,  -9.14469710e+04,  -1.10997845e+03,
                    -4.34480365e+04,  -3.13751079e+02,  -1.59840260e+02],
                    [  1.92371520e+02,  -1.10997840e+03,  -2.56136270e+01,
                    -9.93264100e+02,   7.71506200e+00,   3.88369600e+00],
                    [  7.78063148e+03,  -4.34480365e+04,  -9.93264146e+02,
                    -4.80541196e+04,   2.84426623e+02,   1.44526736e+02],
                    [ -7.76604450e+02,  -3.13751100e+02,   7.71506200e+00,
                    2.84426600e+02,  -2.87075270e+01,   6.76657400e+00],
                    [ -2.17068300e+01,  -1.59840300e+02,   3.88369600e+00,
                    1.44526700e+02,   6.76657400e+00,  -1.79784270e+01]])