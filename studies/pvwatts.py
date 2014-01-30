﻿#!/usr/bin/env python

import json
import os
import shutil
import solvers
from datetime import datetime

with open('./studies/pvwatts.html','r') as configFile: configHtmlTemplate = configFile.read()

class Pvwatts:
	def __init__(self, jsonDict, new=False):
		pass
		self.analysisName = jsonDict.get('analysisName','')
		self.name = jsonDict.get('name','')
		self.simLength = jsonDict.get('simLength',0)
		self.simLengthUnits = jsonDict.get('simLengthUnits','')
		self.simStartDate = jsonDict.get('simStartDate','')
		self.climate = jsonDict.get('climate','')
		self.sourceFeeder = jsonDict.get('sourceFeeder','')
		self.inputJson = jsonDict.get('inputJson', {})
		self.outputJson = jsonDict.get('outputJson', {})
		self.studyType = 'pvwatts'

	def run(self):
		try:
			# Create a running directory and fill it.
			studyPath = 'running/' + self.analysisName + '---' + self.name + '___' + str(datetime.now()).replace(':','_') + '/'
			os.makedirs(studyPath)
			# Write attachments and glm.
			attachments = self.inputJson['attachments']
			for attach in attachments:
				with open (studyPath + attach,'w') as attachFile:
					attachFile.write(attachments[attach])
			# setup data structures
			ssc = solvers.nrelsam.SSCAPI()
			dat = ssc.ssc_data_create()
			# required inputs
			ssc.ssc_data_set_string(dat, "file_name", studyPath + "/climate.tmy2")
			ssc.ssc_data_set_number(dat, "system_size", float(self.inputJson['systemSize']))
			ssc.ssc_data_set_number(dat, "derate", float(self.inputJson['derate']))
			ssc.ssc_data_set_number(dat, "track_mode", float(self.inputJson['trackingMode']))
			ssc.ssc_data_set_number(dat, "azimuth", float(self.inputJson['azimuth']))
			# default inputs exposed
			ssc.ssc_data_set_number(dat, 'rotlim', float(self.inputJson['rotlim']))
			ssc.ssc_data_set_number(dat, 't_noct', float(self.inputJson['t_noct']))
			ssc.ssc_data_set_number(dat, 't_ref', float(self.inputJson['t_ref']))
			ssc.ssc_data_set_number(dat, 'gamma', float(self.inputJson['gamma']))
			ssc.ssc_data_set_number(dat, 'inv_eff', float(self.inputJson['inv_eff']))
			ssc.ssc_data_set_number(dat, 'fd', float(self.inputJson['fd']))
			ssc.ssc_data_set_number(dat, 'i_ref', float(self.inputJson['i_ref']))
			ssc.ssc_data_set_number(dat, 'poa_cutin', float(self.inputJson['poa_cutin']))
			ssc.ssc_data_set_number(dat, 'w_stow', float(self.inputJson['w_stow']))
			# complicated optional inputs
			ssc.ssc_data_set_number(dat, 'tilt_eq_lat', 1)
			# ssc.ssc_data_set_array(dat, 'shading_hourly', ...) 	# Hourly beam shading factors
			# ssc.ssc_data_set_matrix(dat, 'shading_mxh', ...) 		# Month x Hour beam shading factors
			# ssc.ssc_data_set_matrix(dat, 'shading_azal', ...) 	# Azimuth x altitude beam shading factors
			# ssc.ssc_data_set_number(dat, 'shading_diff', ...) 	# Diffuse shading factor
			# ssc.ssc_data_set_number(dat, 'enable_user_poa', ...)	# Enable user-defined POA irradiance input = 0 or 1
			# ssc.ssc_data_set_array(dat, 'user_poa', ...) 			# User-defined POA irradiance in W/m2
			# ssc.ssc_data_set_number(dat, 'tilt', 999)

			# run PV system simulation
			mod = ssc.ssc_module_create("pvwattsv1")
			ssc.ssc_module_exec(mod, dat)

			# MD calc.
			if self.simLengthUnits == 'days':
				startDateTime = self.simStartDate
			else:
				startDateTime = self.simStartDate + ' 00:00:00 PDT'

			def aggData(key, aggFun):
				u = self.simStartDate
				dt = datetime(int(u[0:4]),int(u[5:7]),int(u[8:10]))
				v = dt.isocalendar()
				initHour = int(8760*(v[1]+v[2]/7)/52.0)
				fullData = ssc.ssc_data_get_array(dat, key)
				if self.simLengthUnits == 'days':
					multiplier = 24
				else:
					multiplier = 1
				hourData = [fullData[(initHour+i)%8760] for i in xrange(self.simLength*multiplier)]
				if self.simLengthUnits == 'minutes':
					pass
				elif self.simLengthUnits == 'hours':
					return hourData
				elif self.simLengthUnits == 'days':
					split = [hourData[x:x+24] for x in xrange(self.simLength)]
					return map(aggFun, split)

			def avg(x):
				return sum(x)/len(x)
			
			# Extract data.
			# Timestamps.
			outData = {}
			outData['timeStamps'] = [startDateTime for x in range(self.simLength)]
			# Geodata.
			outData['city'] = ssc.ssc_data_get_string(dat, 'city')
			outData['state'] = ssc.ssc_data_get_string(dat, 'state')
			outData['lat'] = ssc.ssc_data_get_number(dat, 'lat')
			outData['lon'] = ssc.ssc_data_get_number(dat, 'lon')
			outData['elev'] = ssc.ssc_data_get_number(dat, 'elev')
			# Weather
			outData['climate'] = {}
			outData['climate']['irrad'] = aggData('dn', avg)
			outData['climate']['diffIrrad'] = aggData('df', avg)
			outData['climate']['temp'] = aggData('tamb', avg)
			outData['climate']['cellTemp'] = aggData('tcell', avg)
			outData['climate']['wind'] = aggData('wspd', avg)
			# Power generation.
			outData['Consumption'] = {}
			outData['Consumption']['Power'] = [-1*x for x in aggData('ac', avg)]
			outData['Consumption']['Losses'] = [0 for x in aggData('ac', avg)]
			outData['Consumption']['DG'] = aggData('ac', avg)
			# Stdout/stderr.
			outData['stdout'] = 'Success'
			outData['stderr'] = ''
			# componentNames.
			outData['componentNames'] = []
			shutil.rmtree(studyPath)
			self.outputJson = outData
		except:
			self.outputJson = {'stdout':'Failure'}