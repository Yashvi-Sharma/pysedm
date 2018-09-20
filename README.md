# pysedm
Data Reduction Pipeline for the SEDmachine (no ready yet)

*This module is under development and is not yet ready to be used*

# Installation

```bash
git pull https://github.com/MickaelRigault/pysedm.git
cd pysedm
python setup.py install
```


# Dependencies

works in python 2.7+ and 3.x, but the 2.7+ might not be supported in the future. 

### Basics

- numpy, scipy, matpotlib, astropy
- propobject (pip install propobject) _for the structure of the classes_
- pyifu (pip install pyifu or see https://github.com/MickaelRigault/pyifu) _cube and spectra object library_

### If you want to reproduce the spectral extraction:

- psfcube (pip install psfcube or see https://github.com/MickaelRigault/psfcube) 
  _psfcube depends on Minuit (fitter) and modefit (structure), which are automatically installed if needed_

### If you need to reproduce the cube creation:

- shapely (pip install shapely) _for the polygon matching in CCD to Spectrum_  
- astrobject (pip install astrobject) _for the basic Image objects as well as low level tools_
- pynverse (pip install pynverse) _for a faster lbda<->pixels conversion in the wavelength solutio_

# Running a manual spectral extraction

...doc ongoing...

# Modules

## CCD

## wavelength solution
