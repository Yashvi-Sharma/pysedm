#! /usr/bin/env python
# -*- coding: utf-8 -*-

""" Module containing the part that are directly SEDM oriented. """

import numpy              as np
import warnings

from pyifu.spectroscopy   import Cube, Spectrum, get_spectrum, load_spectrum
from .utils.tools         import kwargs_update, is_arraylike

from .io import PROD_CUBEROOT

__all__ = ["get_sedmcube", "build_sedmcube","kpy_to_e3d"]

# PROD_CUBEROOT e3d
# --- DB Structure
CALIBFILES = ["Hg.fits","Cd.fits","Xe.fits","dome.fits"]

# --- CCD
SEDM_CCD_SIZE = [2048, 2048]
DOME_TRACEBOUNDS = [70,230]
TRACE_DISPERSION = 1.2*2 # PSF (sigma assuming gaussian) of the traces on the CCD.

SEDM_INVERT = False #  Shall the x and y axis extracted in the hexagrid be inverted ?
SEDM_ROT    = 103
SEDM_MLA_RADIUS = 25

_rot = SEDM_ROT*np.pi/  180
SEDMSPAXELS = np.dot( np.asarray([[np.cos(_rot), -np.sin(_rot)],[np.sin(_rot),np.cos(_rot)]]) ,
                    np.asarray([[ np.sqrt(3.)/2., 1./2],[0, 1],[-np.sqrt(3.)/2., 1./2],
                            [-np.sqrt(3.)/2.,-1./2],[0,-1],[ np.sqrt(3.)/2.,-1./2]]).T*2/3.).T

#_EDGES_Y = 40
#_EDGES_X = [180,50]
#INDEX_CCD_CONTOURS = [[_EDGES_X[0],_EDGES_Y],[_EDGES_X[0],1700],
#                      [300, SEDM_CCD_SIZE[1]-_EDGES_Y],[SEDM_CCD_SIZE[0]-_EDGES_X[1],SEDM_CCD_SIZE[1]-_EDGES_Y],
#                        [SEDM_CCD_SIZE[0]-_EDGES_X[1],_EDGES_Y]]

# = Could be improved Maybe.
INDEX_CCD_CONTOURS = [[20, 300], [300,40], 
                      [1600, 40], [SEDM_CCD_SIZE[0]-20, 300],
                      [SEDM_CCD_SIZE[0]-20, 1600], 
                      [1600, SEDM_CCD_SIZE[1]-30],
                      [1500, SEDM_CCD_SIZE[1]-30], 
                      [480, SEDM_CCD_SIZE[1]-30],
                      [20, 1675]
                     ]

from shapely import geometry
MLA_CIRCLE = geometry.Point(950,950).buffer(1090)
MLA_GRID   = geometry.Polygon([[40,40],[40,2000], [2000,2000], [2000,40]])
INDEX_CCD_CONTOURS = MLA_CIRCLE.intersection(MLA_GRID)
    
# --- LBDA
SEDM_LBDA = np.linspace(3700, 9300, 220)
LBDA_PIXEL_CUT = 3


# --- ADR
MLA_ROTATION_DEG= 263
MLA_ROTATION_RAD= MLA_ROTATION_DEG * np.pi / 180.  # degree -> to rad
MLA_ROTMATRIX   = np.asarray([[ np.cos(MLA_ROTATION_RAD),-np.sin(MLA_ROTATION_RAD)], 
                              [ np.sin(MLA_ROTATION_RAD), np.cos(MLA_ROTATION_RAD)]] )
DEFAULT_REFLBDA = 6000 # In Angstrom
IFU_SCALE_UNIT  = 0.75

# ----- WCS
SEDM_ASTROM_PARAM  = [ 7.28968990e-01,  6.89009309e-02, -6.57804812e-03, -7.94252856e-01,
                           1.02682050e+03 , 1.01659890e+03]
    
SEDM_ASTROM_PARAM_since_20180928 = [ 6.63023938e-01,  6.57283519e-02, -1.97868377e-02, -7.71650238e-01,
                                         1.01768812e+03,  1.01237730e+03]

SEDM_ASTROM_PARAM_since_20190201 = [ 6.20197410e-01,  1.02551606e-01,  3.84158750e-02, -8.63030378e-01,
                                         1.03498483e+03,  1.01326973e+03]

SEDM_ASTROM_PARAM_since_20190417 = [ 6.60117539e-01,  1.90076806e-02, -5.86653828e-03, -5.99786189e-01,
                                         1.02190229e+03,  1.02202838e+03]
    
def get_sedm_astrom_param(cube_date=None):
    """ """
    if cube_date is None:
        return SEDM_ASTROM_PARAM
    

    _sedm_version_ = get_sedm_version(cube_date)
    # Old Rainbow CCD
    if _sedm_version_ == "v1":
        return SEDM_ASTROM_PARAM
    elif _sedm_version_ == "v2":
        return SEDM_ASTROM_PARAM_since_20180928
    elif  _sedm_version_ == "v3":
        return SEDM_ASTROM_PARAM_since_20190201
    else:
        return SEDM_ASTROM_PARAM_since_20190417
def get_sedm_version(cube_date):
    """ """
    from astropy.time import Time 
    if Time(cube_date) < Time("2018-09-27"):
        return "v1"
    if Time(cube_date) < Time("2019-01-30"):
        return "v2"
    if Time(cube_date) < Time("2019-04-17"):
        return "v3"
    
    return "v4"

# --- Palomar Atmosphere
# Palomar Extinction Data from Hayes & Latham 1975
# (Wavelength in Angstroms, Magnitudes per airmass)
PALOMAR_EXTINCTION = np.asarray([ (3200, 1.058),
 (3250, 0.911), (3300, 0.826), (3350, 0.757), (3390, 0.719), (3448, 0.663), (3509, 0.617),
 (3571, 0.575), (3636, 0.537), (3704, 0.500), (3862, 0.428), (4036, 0.364), (4167, 0.325),
 (4255, 0.302), (4464, 0.256), (4566, 0.238), (4785, 0.206), (5000, 0.183), (5263, 0.164),
 (5556, 0.151), (5840, 0.140), (6055, 0.133), (6435, 0.104), (6790, 0.084), (7100, 0.071),
 (7550, 0.061), (7780, 0.055), (8090, 0.051), (8370, 0.048), (8708, 0.044), (9832, 0.036),
 (10255, 0.034), (10610, 0.032), (10795, 0.032), (10870, 0.031)])


PALOMAR_COORDS = {"latitude":   33.3563, # North
                  "longitude":-116.8648, # West
                  "altitude":1712,       #meter
                      }

    
def get_palomar_extinction():
    """ The ExtinctionSpectrum object of the Palomar Extinction 
    To correct for atmosphere extinction, see the get_atm_extinction() method

    Return 
    ------
    ExtinctionSpectrum
    """
    from .utils.atmosphere import ExtinctionSpectrum
    spec = ExtinctionSpectrum(None)
    spec.create(lbda=PALOMAR_EXTINCTION.T[0],data=PALOMAR_EXTINCTION.T[1],
                                variance=None, header=None)
    spec._source = "Hayes & Latham 1975"
    return spec


from scipy.stats import linregress
SEDM_XRED_EXTENTION = [5.972e-03, 56]# 54.4443
SEDM_XBLUE_EXTENTION = [7.232e-03,-238] #236.4647


def domexy_to_tracesize(x_,y_,theta_):
    """ """
    delta_x = np.asarray([x_*SEDM_XRED_EXTENTION[0] + SEDM_XRED_EXTENTION[1], x_*SEDM_XBLUE_EXTENTION[0] + SEDM_XBLUE_EXTENTION[1]])
    return x_-delta_x,  y_-np.sin(theta_)*delta_x



def load_sedmspec(filename):
    """ Load SEDM .fits or .txt """
    if filename.endswith(".txt"):
        return get_sedmspec( open(filename).read().splitlines() )
    
    return load_spectrum(filename)
        
def get_sedmspec(ascii_data):
    """ """
    from pyifu import get_spectrum
    from astropy.io import fits
    header = fits.Header()
    for d in ascii_data:
        if not d.startswith("#"): continue
        if "SNID" in d: continue
        header.set(*d.replace("# ","").split(": "))
        
    spec_data = np.asarray([d.split() for d in ascii_data if not d.startswith("#")], dtype="float").T
    return get_spectrum(*spec_data, header=header)


# ------------------ #
#  Builder           #
# ------------------ #
def build_sedmcube(ccd, date, lbda=None, flatfield=None,
                   wavesolution=None, hexagrid=None,
                   # - ignore all twicking
                   fileindex="",
                   # Flexure
                   flexure_corrected=True,
                   pixel_shift=0,
                   # Flat and Atm
                   flatfielded=True, atmcorrected=True,
                   # Flux Calibration
                   calibration_ref=None,
                   build_calibrated_cube=False,
                   # Output
                   savefig=True,verbose=False,
                   return_cube=False):
    """ Build a cube from the an IFU ccd image. This image 
    should be bias corrected and cosmic ray corrected.

    The standard created cube will be 3Dflat field correct 
    (see flatfielded) and corrected for atmosphere extinction 
    (see atmcorrected). A second cube will be flux calibrated 
    if possible (see build_calibrated_cube).
    
    = Remark, any TraceFlexure correction on ccd.tracematch should be 
      made prior calling build_sedmcube =

    Parameters
    ----------
    ccd: [CCD]
        A ccd object from which the cube will be extracted.
        
    date: [string]
        date in usual YYYYMMDD format
    
    lbda: [None/array] -optional-
        wavelength array used to build the cube. 
        If not given the default sedm wavelength range will be used. 
        See pysedm.sedm.SEDM_LBDA.
        
    return_cube: [bool] -optional-
        Shall this function return the cube (True) or save it (False)?

    // Cube Calibrator //
    
    wavesolution: [WaveSolution] -optional-
        The wavelength solution containing the pixel<->wavelength conversion.
        If None, this will be loaded using `date`.

    hexagrid: [HexaGrid] -optional-
        The Hexagonal Grid tools containing the index<->qr<->xy conversions.
        If None, this will be loaded using `date`.

    flatfield: [Slice] -optional-
        Object containing the relative transmission of the IFU spaxels.
        If None, this will be loaded using `date`.

    pixel_shift: [float] -optional-
        number of i-ccd pixel shift (usually a fraction of pixel) caused by flexure.
        
    // Action Selection //
    
    flatfielded: [bool] -optional-
        Shall the cube be flatfielded?
        - This information will be saved in the header-
    
    atmcorrected: [bool] -optional-
        Shall the cube the corrected for atmosphere extinction?
        - This information will be saved in the header-

    // Additional outcome: Flux calibrated cube //

    build_calibrated_cube: [bool] -optional-
        Shall this method build an additionnal flux calibrated cube?
        
    calibration_ref: [None/string] -optional-
        If you want to build a calibrated cube, you can provide the filename
        of the spectrum containing the inverse-sensitivity (fluxcal*)
        If None, this will load the latest fluxcal object of the night.
        If Nothing found, no flux calibrated cube will be created. 

    Returns
    -------
    Void (or Cube if return_cube set to True)
    """
    from . import io
    # - IO information
    if np.any([calibkey_ in ccd.filename for calibkey_ in CALIBFILES]):
        fileout_ = "%s"%(ccd.filename.split("/")[-1].split(".fits")[0])
    else:
        fileout_ = "%s_%s"%(ccd.filename.split("/")[-1].split(".fits")[0], ccd.objname)
        
    
    fileindex = "_%s"%fileindex if fileindex is not None and fileindex.replace(" ","") != "" else ""
    
    fileout     = io.get_datapath(date)+"%s%s_%s.fits"%(PROD_CUBEROOT,fileindex,fileout_)

        
        
    # - INPUT [optional]
    if hexagrid is None:
        hexagrid     = io.load_nightly_hexagonalgrid(date)
    
    if wavesolution is None:
        wavesolution = io.load_nightly_wavesolution(date)
        wavesolution._load_full_solutions_()
    
    if lbda is None:
        lbda = SEDM_LBDA

    if flatfielded and flatfield is None:
        flatfield = io.load_nightly_flat(date)
        
    # - Build the Cube
    cube = ccd.extract_cube(wavesolution, lbda, hexagrid=hexagrid, show_progress=True,
                            pixel_shift=pixel_shift)

    # - passing the header inforation
    for k,v in ccd.header.items():
        if k not in cube.header:
            cube.header[k] = v

    cube.header['ORIGIN'] = (ccd.filename.split('/')[-1], "CCD filename used to build the cube")

    # - Flat Field the cube
    if flatfielded:
        cube.scale_by(flatfield.data, onraw=False)
        cube.header['FLAT3D'] = (True, "Is the Cube FlatFielded")
        cube.header['FLATSRC'] = (flatfield.filename.split('/')[-1], "Object use to FlatField the cube")
    else:
        cube.header['FLAT3D'] = (False, "Is the Cube FlatFielded")
        
    # - Amtphore correction
    if atmcorrected:
        atmspec = get_palomar_extinction()
        if 'AIRMASS' not in cube.header:
            extinction = atmspec.get_atm_extinction(cube.lbda, 1.1)
            print("WARNING: AIRMASS keyword missing from header, assuming 1.1")
        else:
            extinction = atmspec.get_atm_extinction(cube.lbda, cube.header['AIRMASS'])
        # scale_by devided by
        cube.scale_by(1./extinction, onraw=False)
        cube.header['ATMCORR']  = (True, "Has the Atmosphere extinction been corrected?")
        cube.header['ATMSRC']   = (atmspec._source if hasattr(atmspec,"_source") else "unknown", "Reference of the atmosphere extinction")
        cube.header['ATMSCALE'] = (np.nanmean(extinction), "Mean atm correction over the entire wavelength range")
    else:
        cube.header['ATMCORR']  = (False, "Has the Atmosphere extinction been corrected?")
        
    # - Flexure Correction
    if flexure_corrected:
        print("Flexure Correction ongoing ")
        from .wavesolution import Flexure
        from .mapping      import Mapper
        mapper = Mapper(tracematch= ccd.tracematch, wavesolution = wavesolution, hexagrid=hexagrid)
        mapper.derive_spaxel_mapping( list(wavesolution.wavesolutions.keys()) )
        
        flexure = Flexure(cube, mapper=mapper)
        flexure.load_telluric_fit()
        flexure.load_sodium_fit()
        
        if savefig:
            cube._side_properties["filename"] = fileout
            savefile= fileout.replace(PROD_CUBEROOT,"flex_sodiumline_"+PROD_CUBEROOT).replace(".fits",".pdf")
            flexure.show(savefile=savefile,show=False)
            flexure.show(savefile=savefile.replace(".pdf",".png"),show=False)

        FLEXURE_REF  = ["sodium", "telluric"]
        i_shift = flexure.get_i_flexure(FLEXURE_REF)
        
        print("Getting the flexure corrected cube. ")
        cube = build_sedmcube(ccd, date, lbda=lbda, flatfield=flatfield,
                                  wavesolution=wavesolution, hexagrid=hexagrid,
                                  flatfielded=flatfielded, atmcorrected=atmcorrected,
                                  calibration_ref=calibration_ref,
                                  build_calibrated_cube=build_calibrated_cube,
                                  savefig=savefig,
                                  # Flexure Change
                                  flexure_corrected=False,
                                  pixel_shift= i_shift,
                                  return_cube=True)
        
        cube.header['IFLXCORR']  = (True, "Has the Flexure been corrected?")
        cube.header['IFLXREF']   = (",".join(np.atleast_1d(FLEXURE_REF)), "Which line has been used to correct flexure?")
        cube.header['CCDIFLX']   = (i_shift, "Number of i (ccd-x) pixel shifted")
        cube.header['IFLXBKUP']  = ("deprecated", "Was i_shift derived from backup mode ?")
    else:
        cube.header['IFLXCORR']  = (False, "Has the Flexure been corrected?")
        cube.header['IFLXREF']   = (None,  "Which line has been used to correct flexure?")
        cube.header['CCDIFLX']   = (0, "Number of i (ccd-x) pixel shifted")
        cube.header['IFLXBKUP']  = ("deprecated", "Was i_shift derived from backup mode ?")
    # - Return it.
    if return_cube:
        return cube
    
    cube.writeto(fileout)

    # - Build Also a flux calibrated cube?
    if build_calibrated_cube:
        build_calibrated_sedmcube(fileout, date=date, calibration_ref=calibration_ref)
        
def build_calibrated_sedmcube(cubefile, date=None, calibration_ref=None, kindout=None):
    """ """
    
    if calibration_ref is None:
        from .io import fetch_nearest_fluxcal
        try:
            calibration_ref =  fetch_nearest_fluxcal(date, cubefile)
        except IOError:
            warnings.warn("No fluxcalibration file available. No calibrated cube built")
            return
        if kindout is None: kindout="defcal"
        print("using %s as a flux calibration reference"%calibration_ref.split("/")[-1] )
    else:
        if kindout is None: kindout="cal"
        
    # - Inverse Sensitivity
    spec = Spectrum(calibration_ref)
    # - Load it
    cube = get_sedmcube(cubefile)
    # - Do it
    cube.scale_by(1./spec.data)
    cube.header['SOURCE']  = (cubefile.split('/')[-1] , "the original cube")
    cube.header['FCALSRC'] = (calibration_ref.split('/')[-1], "the calibration source reference")
    cube.header['PYSEDMT'] = ("Flux Calibrated Cube")
    # - Save it
    cube.writeto(cubefile.replace("%s"%PROD_CUBEROOT,"%s_%s"%(PROD_CUBEROOT,kindout)))






def get_sedm_flatcube(domecube, s=0.8, loc=4300):
    """ Froma e3d dome cube, This returns a flatfielder cube """
    from scipy import stats
    from scipy.optimize import fmin
    from pyifu import get_slice, get_cube
    # Functions
    def fit_domeshape(spec):
        norm = spec.data.max()*3000
        flagout =  (spec.lbda<6500)# * (spec.lbda<7000)
        flagin = ~flagout
        def chi2(p):
            ampl, scale= p
            return np.sum(np.abs( spec.data[flagin]/norm - ampl*  stats.exponnorm.pdf(spec.lbda, s, 
                                                                        loc=loc, scale=scale)[::-1][flagin] ))
        return fmin(chi2, [1, 950], disp=False), norm
    
    def display_domeshape(spec, ampl, scale, loc_=loc, s_=s):
        """ """
        ax = spec.show()["ax"]
        ax.plot(spec.lbda, ampl*stats.exponnorm.pdf(spec.lbda,s_, loc=loc_, scale=scale)[::-1], color="C1")
    
    # Higher Level
    def fit_ampl(spec, show=False):
        r, norm = fit_domeshape(spec)
        r[0] *= norm
        if show:
            display_domeshape(spec, r[0],r[1])
        return r

    # Functions
    domeindexes = {domecube.indexes[i]:fit_ampl(domecube.get_spectrum(i), False) for i in np.arange(len( domecube.indexes)) }
    prop = dict(spaxel_vertices= domecube.spaxel_vertices, indexes=domecube.indexes)

    ampslice   = get_slice([domeindexes[i][0] for i in domecube.indexes], domecube.index_to_xy(domecube.indexes), **prop)
    scaleslice = get_slice([domeindexes[i][1] for i in domecube.indexes], domecube.index_to_xy(domecube.indexes), **prop)

    datacube = [stats.exponnorm.pdf(domecube.lbda, s, loc=loc, scale=s)[::-1]*ampl 
             for ampl,s in zip(ampslice.data, scaleslice.data)]

    flatcube = get_cube(np.asarray(datacube).T,
                            spaxel_mapping= domecube.spaxel_mapping,
                            spaxel_vertices=domecube.spaxel_vertices,
                            lbda=domecube.lbda)
    
    flatcube.scale_by(np.mean(flatcube.data, axis=1))
    return flatcube
# ------------------ #
#  Main Functions    #
# ------------------ #
def load_sedmcube(filename, **kwargs):
    """Load a Cube from the given filename 
    
    Returns
    -------
    Cube
    """
    # To be split between load and get
    return get_sedmcube(filename, **kwargs)


def get_sedmcube(filename, **kwargs):
    """ Load a Cube from the given filename 
    
    Returns
    -------
    Cube
    """
    return SEDMCube(filename, **kwargs)

def get_aperturespectrum(filename):
    """ Load and return an Aperture Spectrum """
    spec = ApertureSpectrum(None,None)
    spec.load(filename)
    return spec

def kpy_to_e3d(filename, lbda, savefile=None):
    """ Converts SEDmachine kpy .npy data into pyifu e3d cubes. 
    (rotation information missing)
    
    Parameters
    ----------
    filename: [string]
        .npy data created using the kpy software

    lbda: [array]
        wavelength array of the cube.

    savefile: [string/None] -optional-
        if you want to save the cube, provide here its fullpath
    
    Returns
    -------
    pyifu Cube 
    """
    from scipy.interpolate import interp1d
    # 
    #  get the data
    data, header = np.load(filename)
    # 
    # empty the cube
    cube = Cube(None)
    cubeflux     = []
    spaxel_map   = {}
    for i, ext in enumerate(data):
        try:
            lbda_nm, flux_ = ext.get_flambda("spec")
            cubeflux.append(interp1d(lbda_nm*10, flux_, kind="cubic")(lbda))
            spaxel_map[i] = np.asarray([ext.X_as,ext.Y_as]*np.sqrt(3))
        except:
            # will crash if given lbda is outside the Extraction wavelength
            continue
        
    # create it
    cube.create(np.asarray(cubeflux).T,lbda=lbda, spaxel_mapping=spaxel_map, variance=None)
    cube.set_spaxel_vertices(SEDMSPAXELS/ np.sqrt(3))
    for k,v in header["header"].items():
        cube.header[k] = v

    # returns it.
    if savefile is not None:
        cube.writeto(savefile)
        
    return cube


# --------------- #
#   PLOTTER       #
# --------------- #
def display_on_hexagrid(value, traceindexes,
                        hexagrid=None, xy=None, 
                        outlier_highlight=None,
                        ax = None, savefile=None, show=True,
                        vmin=None, vmax=None, show_colorbar=True,
                        clabel="",cfontsize="large",
                            **kwargs):
    """ display on the IFU hexagonal grid the given values

    Parameters
    ----------        
    value: [list]
        value defining the color of the hexagones
    
    traceindexes: [list]
        indexes corresponding to the values

    hexagrid: [HexaGrid] -optional if xy given-
        object containing the traceindex<->qr<->xy transformation
    
    xy: [array, array] -optional if hexagrid given-
        x,y, position of the spaxels in the MLA.

    outlier_highlight: [None / positive-float] -optional-
        if a value is `outlier_highlight` sigma away from the core of the
        distribution, it will be highlighted.
        if None, nothing will be done.

    """
    from matplotlib                import patches
    import matplotlib.pyplot           as mpl
    from astrobject.utils.mpladdon import colorbar, insert_ax
    from pyifu.tools import figout

    # - Check input
    if len(value) != len(traceindexes):
        raise ValueError("value and traceindexes do not have the same size (%d vs. %s)"%(len(value),len(traceindexes)))
    else:
        nspaxes = len(value)
        value        = np.asarray(value)

    traceindexes = np.asarray(traceindexes)
    
    # -- Let's go
    if ax is None:
        fig = mpl.figure(figsize=[6,5])
        axim  = fig.add_subplot(111)
    else:
        fig = ax.figure
        axim = ax
    
    # - which colors
    if vmin is None:
        vmin = np.percentile(value,0)
    elif type(vmin) == str:
        vmin = np.percentile(value,float(vmin))
    if vmax is None:
        vmax = np.percentile(value,100)
    elif type(vmax) == str:
        vmax = np.percentile(value,float(vmax))
                
    colors = mpl.cm.viridis((value-vmin)/(vmax-vmin))
    # - where
    if xy is None:
        hexagrid.set_rot_degree(SEDM_ROT)
        x,y = np.asarray(hexagrid.index_to_xy(hexagrid.ids_to_index(traceindexes),
                                            invert_rotation=False,
                                            switch_axis=SEDM_INVERT))
    else:
        x,y = xy

    #invert_rotation=False, rot_degree= SEDM_ROT,
    """            
    cube.create(cubeflux.T,lbda=lbda, spaxel_mapping=spaxel_map, variance=cubevar.T)
    cube.set_spaxel_vertices(np.dot(hexagrid.grid_rotmatrix,SEDMSPAXELS.T).T)
    """
    
    # - The Patchs
    ps = [patches.Polygon(SEDMSPAXELS+np.asarray([x[i],y[i]]),
                            facecolor=colors[i], alpha=0.8,**kwargs)
              for i  in range(nspaxes)]
    ip = [axim.add_patch(p_) for p_ in ps]
    axim.autoscale(True, tight=True)

    # - Outlier highlight
    if outlier_highlight is not None:
        outlier_highlight = np.abs(outlier_highlight)
        flagout = np.asarray((np.abs(value) > np.nanmean(value)+np.nanstd(value)*outlier_highlight), dtype="bool")
        if np.any(flagout):
            color = mpl.cm.inferno(0.5,1.)
            for j in np.argwhere(flagout):
                axim.plot(x[j],y[j], marker="x", mfc=color, mew=0, ms=10, zorder=9)
                axim.text(x[j], y[j], "trace %d: %.3f"%(traceindexes[j], value[j]),
                          rotation=45, ha="left", va="bottom", color=color,
                        bbox=dict(facecolor=mpl.cm.binary(0.1,0.5), edgecolor="k", lw=0.5), zorder=9)
            
    if show_colorbar:
        axcbar = axim.insert_ax("right", shrunk=0.88)
        axcbar.colorbar(mpl.cm.viridis,vmin=vmin,vmax=vmax,label=clabel,
                fontsize=cfontsize)
    
    fig.figout(savefile=savefile, show=show)
    return {"ax":axim,"fig":fig}

#################################
#                               #
#    SEDMachine Cube            #
#                               #
#################################
class SEDMCube( Cube ):
    """ SEDM Cube """
    DERIVED_PROPERTIES = ["sky"]

    def get_aperture_spec(self, xref, yref, radius, bkgd_annulus=None,
                              refindex=None, adr=True, **kwargs):
        """ 
        bkgd_annulus: [float, float ] -optional-
            coefficient (in radius) defining the background annulus.
            e.g. if the radius is 5 and bkgd_annulus=[1,1.5], the resulting
            annulus will have an inner radius of 5 and an outter radius of 5*1.5= 7.5
        
        """
        if adr:
            sourcex, sourcey = self.get_source_position(self.lbda, xref=xref, yref=yref, refindex=refindex)
        else:
            sourcex, sourcey = np.ones( len(self.lbda) )*xref,np.ones( len(self.lbda) )*yref

        # - Radius 
        if not is_arraylike(radius):
            radius = np.ones(len(self.lbda))*radius
        elif len(radius)!= len(self.lbda):
            raise TypeError("The radius size must be a constant or have the same lenth as self.lbda")
        
        apert = []
        if bkgd_annulus is not None:
            apert_bkgd = []
            
        for i, x, y, r in zip(range(self.nspaxels), sourcex, sourcey, radius):
            sl_ = self.get_slice(index=i, slice_object=True)
            apert.append(sl_.get_aperture(x,y,r, **kwargs))
            if bkgd_annulus is not None:
                apert_bkgd.append(sl_.get_aperture(x,y,r*bkgd_annulus[1],
                                                radius_min=r*bkgd_annulus[0],
                                                **kwargs))
        apert = np.asarray(apert)
        
        # - Setting the background
        
        spec  = ApertureSpectrum(self.lbda, apert.T[0]/apert.T[2], variance=apert.T[1]/apert.T[2]**2 if self.has_variance() else None,
                                    apweight=apert.T[2], header=None)
        if bkgd_annulus is not None:
            apert_bkgd = np.asarray(apert_bkgd)
            bspec = ApertureSpectrum(self.lbda, apert_bkgd.T[0]/apert_bkgd.T[2], variance=apert_bkgd.T[1]/apert_bkgd.T[2]**2 if self.has_variance() else None,
                                    apweight=apert_bkgd.T[2], header=None)
            spec.set_background(bspec)

        for k,v in self.header.items():
            if np.any([entry in k for entry in ["TEL","RA","DEC","DOME","OBJ","OUT","IN_","TEMP","INST",
                                                    "FLAT","ATM","AIR"]]):
                spec.header[k] = v
        if self.filename is not None:
            spec.header["SOURCE"] = self.filename.split("/")[-1]
            
        return spec
        
    def get_source_position(self, lbda, xref=0, yref=0, refindex=None):
        """ The position in the IFU of a spacial element as a function of wavelength.
        Shift caused by the ADR.
        
        Parameters
        ----------
        lbda: [float/array]
            wavelength in angstrom
        
        xref, yref: [float, float]
            x and y position of the spacial element in the IFU at the reference index wavelength
        
        refindex: [int] -optional-
            index of the wavelength slice used as reference. 
        
        Returns
        -------
        [array, array]
        (x and y positions as a function of lbda)
        """
        if self.adr is None or refindex is not None:
            if refindex is None:
                refindex = np.argmin(np.abs(self.lbda-DEFAULT_REFLBDA))
            self.load_adr(lbdaref=self.lbda[refindex])

        x_default, y_default = self.adr.refract(0, 0, lbda, unit=IFU_SCALE_UNIT)
        x, y = np.dot(MLA_ROTMATRIX,np.asarray([x_default,y_default]))
        
        return x+xref, y+yref
    
    
    def load_adr(self, pressure=630, lbdaref=DEFAULT_REFLBDA,
                     **kwargs):
        """ 
        This method will load the ADR based on data from the header.
        You can overwrite these parameter using kwargs:

        Parameters
        ----------
        pressure: [float] -optional-
            Air pressure in mbar
                
        lbdaref: [float] -optional-
            Reference wavelength, the position shift will be given as a function 
            of this wavelength.

        kwargs parameters:
            airmass: [float]
                Airmass of the target

            parangle: [float]
                Parralactic angle in degree

            temperature: [float]
                temperature in Celcius
            
            relathumidity: [float <100]
                Relative Humidity in %
            
        Returns
        ------- 
        Void (loads the self.adr)
        """
        adr_prop = kwargs_update( dict(pressure=pressure,
                                       lbdaref=lbdaref,
                                       temperature=self.header["IN_AIR"], 
                                       relathumidity=self.header["IN_HUM"], 
                                       airmass=self.header.get('AIRMASS', 1.1),
                                       parangle=self.header['TEL_PA']),
                                **kwargs)
        return super(SEDMCube, self).load_adr(**adr_prop)
    
    def remove_sky(self, nspaxels=50, usemean=False,
                       estimate_from="rawdata", lbda_range=[5000,8000],
                      **kwargs):
        """ Pick the `nspaxels` spaxels and average them out to build a skyspectrum.
        The flux of this skyspectrum is then removed from the cube.

        Parameters
        ----------
        nspaxels: [int]
            the number of spaxels used to estimate the sky.
            These will be the faintest spaxels. 
            (NB: **kwargs are options of the spaxels selection)

        usemean: [bool] -optional-
            If the variance is available, the weighted (1/variance) average will be used
            to combine spectra except if `usemean` is True. In that case, the simple mean 
            will be used.
        
        estimate_from: [string] -optional-
            Attribute that will be used to estimate the `data` of the sky spectrum
 
        lbda_range: [float, float] -optional-
            Which wavelength range is check.

        **kwargs goes to get_faintest_spaxels(): 
                  e.g: lbda_range, avoid_area, avoid_indexes etc.

        Returns
        -------
        Void (affects `data`)
        """
        self._sky = self.get_spectrum(self.get_faintest_spaxels(nspaxels, lbda_range=lbda_range,**kwargs),
                                          usemean=usemean, data=estimate_from)
        self.remove_flux( self._sky.data)


    # - Improved version allowing to add CCD
    def show(self, toshow="data",
                 interactive=False, ccd=None,
                 savefile=None, ax=None, show=True,
                 show_meanspectrum=True, cmap=None,
                 vmin=None, vmax=None, notebook=None,
                 **kwargs):
        """ Display the cube.
        
        Parameters
        ----------
        toshow: [string] -optional-
            Variable you want to display. anything accessible as self.`toshow` that 
            has the same size as the wavelength. 
            If toshow is data or rawdata (or anything containing 'data'), 
            the variance will automatically be added if it exists.
            Do not change this is you have a doubt.
            
        interactive: [bool] -optional- 
           Enable to interact with the plot to navigate through the cube.
           (this might depend on your matplotlib setup.)

        ccd: [bool] -optional-
           Add the CCD image to the interactive plot to enable direct vizualisation of the Traces on the CCD.

        cmap: [matplotlib colormap] -optional-
            Colormap used for the wavelength integrated cube (imshow).

        vmin, vmax: [float /string / None] -optional-
            Lower and upper value for the colormap
            => If the ccd has been given this will affect the ccd image.
            => If not this will affect the projected cube.
            
            3 Formats are available:
            - float: Value in data unit
            - string: percentile. Give a float (between 0 and 100) in string format.
                      This will be converted in float and passed to numpy.percentile
            - None: The default will be used (percentile 0.5 and 99.5 percent respectively).
            (NB: vmin and vmax are independent, i.e. one can be None and the other '98' for instance)

        show_meanspectrum: [bool] -optional-
            If True both a wavelength integrated cube (imshow) and the average spectrum 
            will be displayed. If not, only the wavelength integrated cube (imshow) will.

        ax: [matplotlib.Axes] -optional-
            Provide the axes where the spectrum and/or the wavelength integrated 
            cube  will be drawn. 
            See show_meanspectrum:
               - If True, 2 axes are requested so axspec, aximshow=ax
               - If False, 1 axes is needed, aximshow=ax 
            If None this will create a new axes inside a new figure
            
        savefile: [string/None] -optional-
            Would you like to save the data? If so give the name of this
            file where the plot will be saved.
            You can provide an extention (.pdf or .png) if you don't both the
            .pdf and .png will be created.

        show: [bool] -optional-
            If you do not save the data (see savefile), shall the plot be shown?
        
        notebook: [bool or None] -optional-
            Is this running from a notebook? 
            If True, the plot will be made using fig.show() if not with mpl.show()
            If None, this will try to guess.


        **kwargs goes to matplotlib's imshow 

        Returns
        -------
        Void
        """
        if not interactive or ccd is None:
            return super(SEDMCube, self).show(toshow=toshow, interactive=interactive,
                                           savefile=savefile, ax=ax, show=show,
                                           show_meanspectrum=show_meanspectrum, cmap=cmap,
                                           vmin=vmin, vmax=vmax, notebook=notebook, **kwargs)
        else:
            from .utils.mpl import InteractiveCubeandCCD
            iplot = InteractiveCubeandCCD(self, fig=None, axes=ax, toshow=toshow)
            iplot._nofancy = True
            iplot.set_ccd(ccd)
            iplot.launch(vmin=vmin, vmax=vmax, notebook=notebook)
            return iplot


class ApertureSpectrum( Spectrum ):
    """ Spectrum created with apperture spectroscopy """
    PROPERTIES         = ["apweight", "background"]
    SIDE_PROPERTIES    = []
    DERIVED_PROPERTIES = []

    def __init__(self, lbda, flux, variance=None, apweight=None, header=None):
        """ """
        self.__build__()
        self.set_data(flux, variance=variance, lbda=lbda, logwave=None)
        self._properties['apweight'] = apweight

    # ================ #
    #  Methods         #
    # ================ #
    # ------- #
    # SETTER  #
    # ------- #
    def set_background(self, background):
        """ """
        if type(background) == np.array:
            self._properties['background'] = get_spectrum(self.lbda, background)
        else:
            self._properties['background'] = background
            
    # ------- #
    # GETTER  #
    # ------- #
    
    # ------- #
    # PLOTTER #
    # ------- #
    def show(self, toshow="data", ax=None, savefile=None, show=True,
                 show_background=True,
                 bcolor="0.7", **kwargs):
        """ Display the spectrum.
        
        Parameters
        ----------
        toshow: [string] -optional-
            Variable you want to display. anything accessible as self.`toshow` that 
            has the same size as the wavelength. 
            If toshow is data or rawdata, the variance will automatically be added
            if it exists.
            Do not change this is you have a doubt.

        ax: [matplotlib.Axes] -optional-
            Provide the axes where the spectrum will be drawn.
            If None this will create a new one inside a new figure
            
        savefile: [string/None] -optional-
            Would you like to save the data? If so give the name of this
            file where the plot will be saved.
            You can provide an extention (.pdf or .png) if you don't both the
            .pdf and .png will be created.

        show: [bool] -optional-
            If you do not save the data (see savefile), shall the plot be shown?

        **kwargs goes to specplot (any matplotlib axes.plot entry will work)

        Returns
        -------
        Void
        """
        from pyifu.tools import figout, specplot
        pl = super(ApertureSpectrum, self).show(toshow=toshow, ax=ax, savefile=None, show=False, lw=2, **kwargs)
        fig = pl["fig"]
        ax  = pl["ax"]
        if show_background and self.has_background():
            alpha = kwargs.pop("alpha",1.)/5.
            super(ApertureSpectrum, self).show(toshow="rawdata", ax=ax,
                                                   savefile=None, show=False, alpha=alpha, **kwargs)
            self.background.show(ax=ax, savefile=None, show=False, alpha=alpha, color=bcolor, **kwargs)
            
        fig.figout(savefile=savefile, show=show)

    def scale_by(self, coef):
        """ divide the data by the given scaling factor 
        If this object has a variance attached, the variance will be divided by the square of `coef`.
        Parameters
        ----------
        coef: [float or array of]
            scaling factor for the data 

        Returns
        -------
        Void, affect the object (data, variance)
        """
        if not is_arraylike(coef) or len(coef)==1 or np.shape(coef)==self.data.shape:
            
            self._properties["rawdata"]  = self.rawdata / coef
            if self.has_variance():
                self._properties["variance"]  = self.variance / coef**2
                
        elif len(coef) == self.data.shape[0]:
            self._properties["rawdata"]  = np.asarray(self.rawdata.T / coef).T
            if self.has_variance():
                self._properties["variance"]  = np.asarray(self.variance.T / coef**2).T
        else:
            raise ValueError("scale_by is not able to parse the shape of coef.", np.shape(coef), self.data.shape)


        if self.has_background():
            self.background.scale_by(coef)

            
    # -------- #
    #  I/O     #
    # -------- #
    def _build_hdulist_(self, saveerror=False, savebackground=True):
        """ The fits hdulist that should be saved.

        Parameters
        ----------
        saveerror:  [bool] -optional- 
            Set this to True if you wish to record the error and not the variance
            in you first hdu-table. if False, the table will be called
            VARIANCE and have self.v; if True, the table will be called
            ERROR and have sqrt(self.v)

        savebackground: [bool] -optional-
            Shall the background be saved ?

        Returns
        -------
        Void
        """
        from astropy.io.fits import ImageHDU
        self.header['PYSEDMT']  = ("ApertureSpectrum","Pysedm object Type")
        hdul = super(ApertureSpectrum, self)._build_hdulist_(saveerror=saveerror)

        hduAp  = ImageHDU(self.apweight, name='APWEIGHT')
        hdul.append(hduAp)
        # -- Variance saving
        if self.has_background():
            hduBkgd     = ImageHDU(self.background.data, name='BKGD')
            hdul.append(hduBkgd)
            hduBkgdVar  = ImageHDU(self.background.data, name='BKGDVAR')
            hdul.append(hduBkgdVar)
            hduApBkgd   = ImageHDU(self.background.apweight, name='BKGDAPW')
            hdul.append(hduApBkgd)
            
        return hdul


    def load(self, filename, dataindex=0, varianceindex=1, headerindex=None):
        """ 

        lbda - If an hdu column of the fits file is name:
               "LBDA" or "LAMBDA" or "WAVE" or "WAVELENGTH" or "WAVELENGTHS",
               the column will the used as lbda
        
        """
        super(ApertureSpectrum, self).load(filename, dataindex=dataindex, varianceindex=varianceindex,
                                               headerindex=headerindex)
        
        # Get the LBDA if any
        apweight_ = [f.data for f in self.fits if f.name.upper() in ["APWEIGHT"]]
        self._properties["apweight"] = None if len(apweight_)==0 else apweight_[0]
        
        # Get the LBDA if any
        background_ = [f.data for f in self.fits if f.name.upper() in ["BKGD","BACKGROUND"]]
        bapweight_ = [f.data for f in self.fits if f.name.upper() in ["APWBKGD","BKGDAPW"]]
        bvar_ = [f.data for f in self.fits if f.name.upper() in ["BKGDVAR"]]
        if len(background_)==1:
            
            bck = ApertureSpectrum(self.lbda, background_[0],
                                       variance=None if len(bvar_)==0 else bvar_[0],
                                       apweight=None if len(bapweight_)==0 else bapweight_[0],
                                       header=None)
            self._properties['rawdata'] = self.rawdata + bck.data
            self.set_background(bck)
        
    # ================ #
    #  Properties      #
    # ================ #
    @property
    def data(self):
        """ """
        return self.rawdata - self._backgrounddata
    
    @property
    def apweight(self):
        """ """
        return self._properties['apweight']

    # ----------
    # Background
    @property
    def background(self):
        """ """
        return self._properties['background']
    
    def has_background(self):
        return self._properties['background'] is not None
    
    @property
    def _backgrounddata(self):
        """ """
        return 0 if not self.has_background() else self.background.data
