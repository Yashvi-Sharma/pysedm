#! /usr/bin/env python
# -*- coding: utf-8 -*-

import pysedm
import datetime
import os
from astropy.io import fits

    

import numpy as np
import pysedm
from pysedm import io
import datetime
    
from astropy.io import fits

    
def build_image_report(specfile):
    """ """
    from pysedm.utils import pil
    now = datetime.datetime.now()
    timestring = "made the %d-%02d-%02d at %02d:%02d:%02d"%(now.year,now.month,now.day, now.hour, now.minute, now.second)
        
    footer = pil.get_buffer([20,1], "pysedm version %s"%pysedm.__version__+ "  |  " + timestring,
                                fontsize=15, textprop=dict(color="0.5"), barcolor="k")

    header  = fits.getheader(specfile)
    date    = pysedm.io.header_to_date(header)
    spec_id = pysedm.io.filename_to_id(specfile)
    filesourcename = specfile.split("spec_")[-1].split(".")[0]
    object_name = header['OBJECT'].split()[0] # remove the [A] in 'TARGET [A]'
    
    # Extraction Mode    
    extraction_mode = header["EXTRTYPE"] if "EXTRTYPE" in header else "auto"
    
    # Missing plot format
    prop_missing = dict(fontsize=30, textprop=dict(color="C1"))


    
    # Flexure Images
    try:
        img_flexj= pil.Image.open(pysedm.io.get_night_files(date, "re:flexuretrace",spec_id, extention=".png")[0])
    except:
        img_flexj= pil.get_buffer([7, 4], "j-flexure image missing" , **prop_missing)
        
    try:
        img_flexi= pil.Image.open(pysedm.io.get_night_files(date, "re:flex_sodium",spec_id, extention=".png")[0])
    except:
        img_flexi= pil.get_buffer([7, 4], "i-flexure image missing" , **prop_missing)

    
    # Spaxels used:
    try:
        img_spax = pil.Image.open(pysedm.io.get_night_files(date, "re:ifu_spaxels",filesourcename, extention=".png")[0])
    except:
        img_spax = pil.get_buffer([7, 7], "Spaxel IFU image missing" , **prop_missing)


    # Output Spectra
    all_spectra_files = pysedm.io.get_night_files(date, "re:spec", filesourcename, extention=".png")
    pysedm_spec_file  = pysedm.io.get_night_files(date, "re:spec", filesourcename, extention="%s.png"%object_name)
    typed_spectra     = [f for f in all_spectra_files if not f.endswith("%s.png"%object_name)]
    used_spec_file = pysedm_spec_file if len(typed_spectra) ==0 else typed_spectra
    try:
        img_spec = pil.Image.open( used_spec_file[-1] )
    except:
        img_spec = pil.get_buffer([13, 7], "Spectra image missing" , **prop_missing)

    # ---------
    # PSF Extraction Specials
    # ---------
    # PSF
    try:
        img_psf  = pil.Image.open(pysedm.io.get_night_files(date, "re:psfprofile", filesourcename, extention=".png")[0])
    except:
        img_psf = pil.get_buffer([15, 4], "PSF Profile image missing" , **prop_missing)
        
        
    # ADR
    try:
        img_adr  = pil.Image.open(pysedm.io.get_night_files(date, "re:adr", filesourcename, extention=".png")[0])
    except:
        img_adr= pil.get_buffer([9, 4], "ADR image missing" , **prop_missing)
        
        
    # ============== #
    #  Combination   #
    # ============== #    

    # title
    title = "%s"%object_name
    title+= " | exposure time: %.1f s"%header["EXPTIME"]
    title+= " | file ID: %s "%spec_id


    # Aperture Extract
    if extraction_mode in ["aperture"]:
        title_img = pil.get_buffer([7,1], title , fontsize=16, hline=[0.3,0.7], barprop=dict(lw=1))
        img_lowerright = pil.get_image_column([img_flexi, img_flexj])
        img_right      = pil.get_image_column([title_img, pil.get_image_row([img_spax,img_lowerright])])
        # Combined
        img_combined   = pil.get_image_row([img_spec, img_right])
                
    # Auto (PSF extraction)
    else: 
        title_img = pil.get_buffer([8,1], title , fontsize=16, hline=[0.3,0.7], barprop=dict(lw=1))

        # Info 
        width = 3
        flexheader = pil.get_buffer([width,0.8], "Flexure" , fontsize=10, hline=None, textprop=dict(color="0.5"))
    
        img_upperright = pil.get_image_column([title_img,  img_psf])
        img_upperleft  = pil.get_image_row([img_spax, img_adr])
        img_upper      = pil.get_image_row([img_upperleft, img_upperright])
        
        bar = pil.get_buffer([0.5,8], vline=0.5, barprop=dict(lw=0.2))
        img_lowerright = pil.get_image_column([flexheader,img_flexi, img_flexj])
        img_lower      = pil.get_image_row([img_spec,bar, img_lowerright])
        # Combined
        img_combined  = pil.get_image_column([img_upper, img_lower, 
                                            footer])
    # Returned
    return img_combined
        
            


#################################
#
#   MAIN 
#
#################################
if  __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description=""" run the interactive plotting of a given cube
            """, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('infile', type=str, default=None,
                        help='cube filepath')


    parser.add_argument('--contains',  type=str, default="*",
                        help='Provide here part of the filename. This will build the guider images of all crr images of the given night having `contains` in there name')

    parser.add_argument('--slack',  action="store_true", default=False,
                        help='Submit the report to slack')

    # ================ #
    # END of Option    #
    # ================ #
    args = parser.parse_args()

    if args.slack:
        try:
            from pysedmpush import slack
        except ImportError:
            raise ImportError("you need to install pysedmpush to be able to push on slack")
        
    # Matplotlib
    # ================= #
    #   The Scripts     #
    # ================= #
    SLACK_CHANNEL = "pysedm-report"
    # --------- #
    #  Date     #
    # --------- #
    date = args.infile
    
    # Loads all the spectra 
    specfiles = pysedm.io.get_night_files(date, "spec.basic", args.contains)
    print(specfiles)
    for specfile in specfiles:
            
        img_report = build_image_report(specfile)
        report_filename = specfile.replace("spec_","pysedm_report_").replace(".fits",".png")
        img_report.save(report_filename, dpi=(1000,1000))

        # Slack push report
        if args.slack:
            if not os.path.isfile( report_filename ):
                warnings.warn("No file-image created by the pysedm_report.build_image_report(). Nothing to push on slack")
            else:
                print("pushing the report to %s"%SLACK_CHANNEL)
                header  = fits.getheader(specfile)
                file_id = pysedm.io.filename_to_id(specfile)
                # Title & caption
                title = "pysedm-report: %s | %s (%s)"%(header["OBJECT"], file_id, date)
                caption = ""
                # Push
                slack.push_image(report_filename, caption=caption, title=title,
                                 channel=SLACK_CHANNEL)
        
