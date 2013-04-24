﻿#!/usr/bin/env python

import json
import os
import shutil
import solvers

with open('./studies/pvwatts.html','r') as configFile: configHtmlTemplate = configFile.read()

def create(analysisName, simLength, simLengthUnits, simStartDate, studyConfig):
	studyPath = 'analyses/' + analysisName + '/studies/' + studyConfig['studyName']
	# make the study folder:
	os.mkdir(studyPath)
	# copy over tmy2 and replace the dummy climate.tmy2.
	shutil.copyfile('tmy2s/' + studyConfig['tmy2name'], studyPath + '/climate.tmy2')
	# write all the other variables:
	with open(studyPath + '/samInput.json','w') as samInputFile:
		json.dump(studyConfig, samInputFile, indent=4)
	# add the metadata:
	md = {'climate':str(studyConfig['tmy2name']), 'studyType':str(studyConfig['studyType']), 'sourceFeeder':'N/A'}
	with open(studyPath + '/metadata.json','w') as mdFile:
		json.dump(md, mdFile)
	return

def run(analysisName, studyName):
	studyPath = 'analyses/' + analysisName + '/studies/' + studyName
	# gather input.
	with open(studyPath + '/samInput.json','r') as inputFile:
		inputs = json.load(inputFile)
	# setup data structures
	ssc = solvers.nrelsam.SSCAPI()
	dat = ssc.ssc_data_create()
	# required inputs
	ssc.ssc_data_set_string(dat, "file_name", studyPath + "/climate.tmy2")
	ssc.ssc_data_set_number(dat, "system_size", float(inputs['systemSize']))
	ssc.ssc_data_set_number(dat, "derate", float(inputs['derate']))
	ssc.ssc_data_set_number(dat, "track_mode", float(inputs['trackingMode']))
	ssc.ssc_data_set_number(dat, "azimuth", float(inputs['azimuth']))
	# default inputs exposed
	ssc.ssc_data_set_number(dat, 'rotlim', float(inputs['rotlim']))
	ssc.ssc_data_set_number(dat, 't_noct', float(inputs['t_noct']))
	ssc.ssc_data_set_number(dat, 't_ref', float(inputs['t_ref']))
	ssc.ssc_data_set_number(dat, 'gamma', float(inputs['gamma']))
	ssc.ssc_data_set_number(dat, 'inv_eff', float(inputs['inv_eff']))
	ssc.ssc_data_set_number(dat, 'fd', float(inputs['fd']))
	ssc.ssc_data_set_number(dat, 'i_ref', float(inputs['i_ref']))
	ssc.ssc_data_set_number(dat, 'poa_cutin', float(inputs['poa_cutin']))
	ssc.ssc_data_set_number(dat, 'w_stow', float(inputs['w_stow']))
	# complicated optional inputs
	ssc.ssc_data_set_number(dat, 'tilt_eq_lat', 1)
	# ssc.ssc_data_set_array(dat, 'shading_hourly', ...) 	# Hourly beam shading factors
	# ssc.ssc_data_set_matrix(dat, 'shading_mxh', ...) 		# Month x Hour beam shading factors
	# ssc.ssc_data_set_matrix(dat, 'shading_azal', ...) 	# Azimuth x altitude beam shading factors
	# ssc.ssc_data_set_number(dat, 'shading_diff', ...) 	# Diffuse shading factor
	# ssc.ssc_data_set_number(dat, 'enable_user_poa', ...)	# Enable user-defined POA irradiance input = 0 or 1
	# ssc.ssc_data_set_array(dat, 'user_poa', ...) 			# User-defined POA irradiance in W/m2
	# ssc.ssc_data_set_number(dat, "tilt", 999)

	# run PV system simulation
	mod = ssc.ssc_module_create("pvwattsv1")
	ssc.ssc_module_exec(mod, dat)

	# Extract data.
	# Timestamps.
	outData = {}
	outData['timeStamps'] = ['2012-01-04']
	# Geodata.
	outData['city'] = ssc.ssc_data_get_string(dat, 'city')
	outData['state'] = ssc.ssc_data_get_string(dat, 'state')
	outData['lat'] = ssc.ssc_data_get_number(dat, 'lat')
	outData['lon'] = ssc.ssc_data_get_number(dat, 'lon')
	outData['elev'] = ssc.ssc_data_get_number(dat, 'elev')
	# Weather
	outData['climate'] = {}
	outData['climate']['irrad'] = ssc.ssc_data_get_array(dat, 'dn')
	outData['climate']['diffIrrad'] = ssc.ssc_data_get_array(dat, 'df')
	outData['climate']['temp'] = ssc.ssc_data_get_array(dat, 'tamb')
	outData['climate']['cellTemp'] = ssc.ssc_data_get_array(dat, 'tcell')
	outData['climate']['wind'] = ssc.ssc_data_get_array(dat, 'wspd')
	# Power generation.
	outData['Consumption'] = {}
	outData['Consumption']['Power'] = ssc.ssc_data_get_array(dat, 'ac')
	outData['Consumption']['Losses'] = [0 for x in range(8760)]
	outData['Consumption']['DG'] = ssc.ssc_data_get_array(dat, 'ac')
	# outData['acOut'] = ssc.ssc_data_get_array(dat, 'ac')
	# Stdout/stderr.
	outData['stdout'] = 'Success'
	outData['stderr'] = ''
	# componentNames.
	outData['componentNames'] = []

	# Write some results.
	with open(studyPath + '/cleanOutput.json','w') as outFile:
		json.dump(outData, outFile, indent=4)