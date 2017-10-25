#! /usr/bin/env python
# -*- coding: utf-8 -*-

import warnings
import numpy         as np
from scipy.spatial   import KDTree, distance
from propobject      import BaseObject
from pyifu.spectroscopy import Cube, get_spectrum

from astropy.modeling import models, fitting


""" Module based to extract a point source in a 3D cube """

"""
SO FAR THIS MODULE IS NOT USED FOR THE SEDM PIPELINE. 
"""

__all__ = ["get_extractstar"]



def get_extractstar(cube, psfmodel="MoffatPlane0", fit=True, **kwargs):
    """ loads and returns the extractstar object with the given PSF model.
    
    Parameters
    ----------
    cube: [pyifu's Cube]
        cube with the point source to extract
        
    psfmodel: [string] -optional-
        name of the 3D-PSF model to use to extract the point source:
        list of known model:
           - MoffatPlaneX: Moffat2d + Polynomial2D(degree=X)

    fit: [bool] -optional-
        shall this run the fit?
    
    **kwargs goes to fit()

    Return 
    ------
    ExtractStar
    """
    es = ExtractStar(cube)
    es.set_psfmodel(kind=psfmodel)
    if fit:
        es.fit()
    return es

# ====================== #
#                        #
#   Models               #
#                        #
# ====================== #
class PSF3DMODEL( BaseObject ):
    """ """
    PROPERTIES = ["model"]
    
    def set_model(self, model):
        """ Provide an astropy model to be fitted """
        self._properties["model"] = model

    # - To Be Build
    def fit_cube(self, cube):
        """ """
        # = This method must take a cube as input and set `fitparam`
        raise NotImplementedError("You must define fit_psfmodel")
    
    def evaluate(self, idx, x, y):
        """ """
        # = This method must a cube idx (wavelength index) and coordinates
        # and return the model for the coordinate corresponding to the idx
        raise NotImplementedError("You must define evaluate")

    def get_starflux(self, idx):
        """ """
        # = this method must return the amplitude of the normalised model
        raise NotImplementedError("You must define fit_psfmodel")
    
    # ================= #
    #   Properties      #
    # ================= #
    @property
    def model(self):
        """ """
        return self._properties["model"]

    @property
    def fitparam(self):
        """ """
        return self._derived_properties["fit_param"]

    
class MOFFATPLANE( PSF3DMODEL ):
    """ """
    def fit_cube(self, cube):
        """ """
        x,y = np.asarray(cube.index_to_xy(cube.indexes)).T
        def fit_slice(data_):
            fit_p   = fitting.LevMarLSQFitter()
            flagnan = np.isnan(data_)
            p       = fit_p(self.model, x[~flagnan], y[~flagnan], data_[~flagnan])
            return {pname:[p.parameters[i],np.NaN]
                          for i,pname in enumerate(p.param_names)}
        
        self._derived_properties["fit_param"] = {i:fit_slice(data_) for i, data_ in enumerate(cube.data)}
    
    def evaluate(self, lbda_idx, x, y):
        """ """
        [setattr(self.model,k,v[0]) for k,v in self.fitparam[lbda_idx].items()]
        return self.model(x,y)

    def get_starflux(self, lbda_idx):
        """ get the fitted model flux and its associated error """
        if hasattr(lbda_idx, "__iter__"):
            return np.asarray([self.get_starflux(lbda_idx_) for lbda_idx_ in lbda_idx]).T
        return self.fitparam[lbda_idx]["amplitude_0"]
    


# ========================== #
#                            #
#  Extract Star Classes      #
#                            #
# ========================== #
class ExtractStar( BaseObject ):
    """ """
    PROPERTIES = ["cube","psfmodel"]
    
    # =================== #
    #   MAIN METHODS      #
    # =================== #
    def __init__(self, cube=None):
        """ """
        if cube is not None:
            self.set_cube(cube)
    # ---------- #
    #   SETTER   #
    # ---------- #
    def set_cube(self, cube):
        """ attach a 3D cube to the instance """
        if Cube not in cube.__class__.__mro__:
            raise TypeError("the given cube is not a pyifu Cube (of Child of)")
        
        self._properties["cube"] = cube

    def set_psfmodel(self, kind="MoffatPlane0", **kwargs):
        """ """
        if "MoffatPlane" in kind:
            
            try:
                degree = int(kind.replace("MoffatPlane",""))
            except:
                raise ValueError("Could not parse the Plane Degree. Should be `MoffatPlaneX` where X is any integer")

            # - initial guess
            slice_ = self.cube.get_slice(None,None)
            imax   = np.nanargmax(slice_)
            a0     = slice_[imax]
            x0,y0  = np.asarray(self.cube.index_to_xy(self.cube.indexes))[imax]

            moffatplane = MOFFATPLANE()
            moffatplane.set_model(models.Moffat2D(amplitude=a0, x_0=x0, y_0=y0) + models.Polynomial2D(degree))
            self._properties["psfmodel"] = moffatplane
        else:
            raise TypeError("Only MoffatPlane PSF model define")
                
    # ---------- #
    #   FITTER   #
    # ---------- #
    def fit(self, **kwargs):
        """ extract the spectrum from the cube and return parameters """
        self.psfmodel.fit_cube(self.cube)

    # ---------- #
    #  GETTER    #
    # ---------- #
    def get_modelspectrum(self, lbda=None):
        """ """
        flux,err = self.psfmodel.get_starflux(np.arange(self.cube._l_spix))
        return get_spectrum(self.cube.lbda, flux, variance=err**2)
    
    # ---------- #
    #  PLOTTER   #
    # ---------- #
    def show_psfextraction(self, ref_lbdaidx=215,
                               savefile=None, show=True,
                               **kwargs):
        """ """
        import matplotlib.pyplot as mpl
        from .tools import kwargs_update
        from .mpl   import figout
        fig = mpl.figure(figsize=(10, 3))
        axdata  = fig.add_subplot(141)
        axerr   = fig.add_subplot(142)
        axmodel = fig.add_subplot(143)
        axres   = fig.add_subplot(144)
        
        slice_    = self.cube.data[ref_lbdaidx]
        slice_var = self.cube.variance[ref_lbdaidx]
        x,y       = np.asarray(self.cube.index_to_xy(self.cube.indexes)).T
        model_    = self.psfmodel.evaluate(ref_lbdaidx, x ,y)

        # Plot the data with the best-fit model
        default_prop = dict(marker="h",s=15,
                            vmin=np.percentile(slice_, 5),
                            vmax=np.percentile(slice_, 95))
        
        prop = kwargs_update(default_prop, **kwargs)
        
        # - Data
        axdata.scatter(x,y,c=slice_, **prop)
        axdata.set_title("Data")
        # - Error
        axerr.scatter(x,y,c=np.sqrt(slice_var), **prop)
        axerr.set_title("Error")
        # - Model
        axmodel.scatter(x,y,c=model_,**prop)
        axmodel.set_title("Model")

        sc = axres.scatter(x,y,c=(slice_ - model_)/np.sqrt(slice_var),**prop)
        axres.set_title("Residual")

        fig.figout(savefile=savefile, show=show)
        
    # =================== #
    #   Properties        #
    # =================== #
    @property
    def cube(self):
        """ 3D cube containing the point source """
        return self._properties["cube"] 

    @property
    def psfmodel(self):
        """ PSFMODEL object used to fit the cube """
        return self._properties["psfmodel"] 
