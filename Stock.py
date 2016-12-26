import sys, configparser, json


importError = False;

try:
	import requests
except ImportError:
	print("Please install requests: 'pip install requests'");
	importError = True;

#MatPlotLib for visualizations
try:
	import matplotlib.pyplot as plt;
	import matplotlib.ticker as mticker
	from matplotlib.finance import candlestick_ohlc
except ImportError:
	print("Please install matplotlib: 'pip install matplotlib'");
	importError = True;

#Pandas is for datetimes
try:
	import pandas as pd
except ImportError:
	print("Please install Pandas");
	importError = True;

#Numpy for line of best fit
try:
	import numpy as np
except ImportError:
	print("Please install Numpy");
	importError = True;

if (importError):
	sys.exit();



class Stock:
	"""
	The object where we store all of our stock information

	Process:
	 -Initialize stock object
	 -Retrieve stock information (retrieve methods)
	 -Perform calculations (calculate methods)
	 -PROFIT (hopefully)
	"""

	#Retrieve information needed to access Intrinio API
	config = configparser.ConfigParser();
	config.read("config.ini");
	username = config["INTRINIO"]["username"];
	password = config["INTRINIO"]["password"];

	shortTermPeriod1 = 12;
	shortTermPeriod2 = 26;
	longTermPeriod1 = 50;
	longTermPeriod2 = 200;

	def __init__(self, ticker, startDate, endDate, limit, outlier=1):
		self.ticker = ticker;				#Ticker of this stock
		self.information = None;			#Information on the stock
		self.ratio = None;					#The ratio indicator with all data
		self.ratioWithoutOutliers = None;	#The ratio indicator sans outliers
		self.decision = None;				#Is this stock a good or bad pick
		
		if (startDate is None):
			self.startDate = pd.to_datetime('1800-01-01');
		else: 
			self.startDate = startDate;			#The start of the timeframe for our analysis
		
		if (endDate is None):
			self.endDate = pd.to_datetime('today');
		else:
			self.endDate = endDate;				#The end of the timeframe for our analysis
		
		self.limit = limit;					#The PE*PBV limit (less means a better stock, but is harder to find)
		self.outlier = outlier;				#Number of standard deviations to be considered an outlier
		self.retrieveRatios();
		#self.makeDecisionInTimeframe(startDate, endDate, outlier);

		#		
		self.earliestDate = None;	#Earliest date seen in our dataset
		self.latestDate = None;		#Latest date seen in our dataset

		#Dictionary is for easy analysis at certain time periods, list is for easy plotting over time periods
		self.opens = {};		#Holds date to open price
		self.openList = [];		#(Date, open)
		self.retrieveOpens();
		
		self.closes = {};		#Holds date to close price
		self.closeList = [];	#(Date, close)
		self.retrieveCloses();
		
		self.highs = {};		#Holds date to high price
		self.highList = [];		#(Date, high)
		self.retrieveHighs();
		
		self.lows = {};			#Holds date to low price
		self.lowList = [];		#(Date, low)
		self.retrieveLows();

		self.volumes = {};		#Holds volumes for the stock
		self.volumeList = [];	#(Date, volume)
		self.retrieveVolumes();

		self.stochastics = {};		#Holds stochastic information about the stock
		self.stochasticList = [];	#(Date, K, D)
		self.calculateStochastics();

		self.ad = {};			#Holds Accumulation/Distribution information
		self.adList = [];		#(Date, AD)
		self.calculateAD();

		self.aroon = {};		#Holds Aroon Indicator Data
		self.aroonList = [];	#(Date, Aroon Up, Aroon Down);
		self.calculateAroon(Stock.shortTermPeriod1);



#------------------------------------Data Retrieval Methods---------------------------------------

	def retrieveOpens(self):
		url = "https://api.intrinio.com/historical_data?identifier={0}&item=adj_open_price".format(self.ticker);
		r = requests.get(url, auth=(Stock.username, Stock.password));
		d = r.json();

		for item in d["data"]:
			if (item["value"] == "nm"):
				continue;

			date = item["date"];
			datetime = pd.to_datetime(date);

			if (datetime < self.startDate or datetime > self.endDate):
				continue;

			value = item["value"];
			self.opens[date] = value;

			if (self.earliestDate is None or datetime < self.earliestDate):
				self.earliestDate = datetime;
			if (self.latestDate is None or datetime > self.latestDate):
				self.latestDate = datetime;

			self.openList.append( [datetime, value] );


	def retrieveCloses(self):
		url = "https://api.intrinio.com/historical_data?identifier={0}&item=adj_close_price".format(self.ticker);
		r = requests.get(url, auth=(Stock.username, Stock.password));
		d = r.json();

		for item in d["data"]:
			if (item["value"] == "nm"):
				continue;

			date = item["date"];
			datetime = pd.to_datetime(date);

			if (datetime < self.startDate or datetime > self.endDate):
				continue;

			value = item["value"];
			self.closes[date] = value;

			if (self.earliestDate is None or datetime < self.earliestDate):
				self.earliestDate = datetime;
			if (self.latestDate is None or datetime > self.latestDate):
				self.latestDate = datetime;

			self.closeList.append( [datetime, value] );



	def retrieveHighs(self):
		url = "https://api.intrinio.com/historical_data?identifier={0}&item=adj_high_price".format(self.ticker);
		r = requests.get(url, auth=(Stock.username, Stock.password));
		d = r.json();

		for item in d["data"]:
			if (item["value"] == "nm"):
				continue;

			date = item["date"];
			datetime = pd.to_datetime(date);
			
			if (datetime < self.startDate or datetime > self.endDate):
				continue;

			value = item["value"];
			self.highs[date] = value;

			if (self.earliestDate is None or datetime < self.earliestDate):
				self.earliestDate = datetime;
			if (self.latestDate is None or datetime > self.latestDate):
				self.latestDate = datetime;

			self.highList.append( [datetime, value] );



	def retrieveLows(self):
		url = "https://api.intrinio.com/historical_data?identifier={0}&item=adj_low_price".format(self.ticker);
		r = requests.get(url, auth=(Stock.username, Stock.password));
		d = r.json();

		for item in d["data"]:
			if (item["value"] == "nm"):
				continue;

			date = item["date"];
			datetime = pd.to_datetime(date);
			
			if (datetime < self.startDate or datetime > self.endDate):
				continue;

			value = item["value"];
			self.lows[date] = value;

			if (self.earliestDate is None or datetime < self.earliestDate):
				self.earliestDate = datetime;
			if (self.latestDate is None or datetime > self.latestDate):
				self.latestDate = datetime;

			self.lowList.append( [datetime, value] );



	def retrieveVolumes(self):
		url = "https://api.intrinio.com/historical_data?identifier={0}&item=adj_volume".format(self.ticker);
		r = requests.get(url, auth=(Stock.username, Stock.password));
		d = r.json();

		for item in d["data"]:
			if (item["value"] == "nm"):
				continue;

			date = item["date"];
			datetime = pd.to_datetime(date);

			if (datetime < self.startDate or datetime > self.endDate):
				continue;

			year = int(date[0:4]);
			month = int(date[5:7]);
			day = int(date[8:10]);

			if (year not in self.volumes.keys()):
				self.volumes[year] = {};
			if (month not in self.volumes[year].keys()):
				self.volumes[year][month] = {};

			value = item["value"];
			self.volumes[year][month][day] = value;

			if (self.earliestDate is None or datetime < self.earliestDate):
				self.earliestDate = datetime;
			if (self.latestDate is None or datetime > self.latestDate):
				self.latestDate = datetime;

			self.volumeList.append( [datetime, value] );




	def retrieveRatios(self):
		#Set up our data holder
		historicData = {};
		historicData["PE"] = {};
		historicData["PBV"] = {};

		url = "https://api.intrinio.com/historical_data?identifier={0}&item={1}";

		keys = [
			("PE", "pricetoearnings"),
			("PBV", "pricetobook")
		];

		#Get information from API
		for keyset in keys:
			apiUrl = url.format(self.ticker, keyset[1]);
			r = requests.get(apiUrl, auth=(Stock.username, Stock.password));
			d = r.json();

			if (d["data"] == None):
				print("No data for " + self.ticker);
				break;

			for item in d["data"]:
				if (item["value"] == "nm"):
					continue;

				date = item["date"];
				datetime = pd.to_datetime(date);
				
				if (datetime < self.startDate or datetime > self.endDate):
					continue;

				historicData[keyset[0]][date] = item["value"];

		self.information = historicData;



#-----------------------------------Calculation Methods-----------------------------------------
#Should probably break these up by type (trend/momentum prediction, overlap studies, etc)
	
	def calculateStochastics(self):
		"""
		'K': 100 * [(C - L5) / (H5 - L5)]
		'D': Average of last three K's

		C: most recent closing price
		L5Close: lowest of the five previous closing prices
		HX: highest of the X previous sessions
		LX: lowest of the X previous sessions

		Starting at the earliest date, calculate the above and store
		Each date in stochastics is a dictionary holding 'K' and 'D'
		"""
		lastFiveCloses = [];
		lastFiveHighs = [];
		lastFiveLows = [];
		date = self.earliestDate;
		currentDate = self.latestDate;

		lastThreeKs = [];

		#Calculate stochastics for every date we have
		while(date != currentDate):
			dateStr = str(date).split(' ')[0]
			
			try:
				#Retrieve closing value for this date
				closeValue = self.closes[dateStr];
				lastFiveCloses.append(closeValue);
				if (len(lastFiveCloses) > 5):
					lastFiveCloses.pop(0);

				#Retrieve highest value for this date
				highValue = self.highs[dateStr];
				lastFiveHighs.append(highValue);
				if (len(lastFiveHighs) > 5):
					lastFiveHighs.pop(0);

				#Retrieve lowest value for this date
				lowValue = self.lows[dateStr];
				lastFiveLows.append(lowValue);
				if (len(lastFiveLows) > 5):
					lastFiveLows.pop(0);
			except KeyError:	#odds are this is caused by this date being a non-trading day, or not having today's close
				date += pd.Timedelta("1 day");
				continue;

			#Calculate 'k' point and 'd' point
			try:
				k = 100 * ( (lastFiveCloses[-1] - min(lastFiveLows)) / (max(lastFiveHighs) - min(lastFiveLows)) )
				d = ( sum(lastThreeKs) / 3);
			except ZeroDivisionError as zde:
				date += pd.Timedelta("1 day");
				continue;

			lastThreeKs.append(k);
			if (len(lastThreeKs) > 3):
				lastThreeKs.pop(0);

			#Store values
			self.stochastics[dateStr] = {};
			self.stochastics[dateStr]['K'] = k;
			self.stochastics[dateStr]['D'] = d;

			self.stochasticList.append( [date, k, d] );

			date += pd.Timedelta("1 day");



	def calculateAD(self):
		"""
		Money Flow Multiplier = [(Close - Low) - (High - Close)] / (High - Low)  |  Should be -1 <= x <= 1
		Money Flow Volume = MFM * (Volume for Period)
		AD = (Previous AD) + MFV

		Period is 'day', 'month', 'year'
		"""
		ad = 0;

		#Do the calculations for yearly so we can do yearly AD later
		for year in sorted(list(self.volumes.keys())):

			#Do the calculations for monthly so we can do monthly AD later
			for month in sorted(list(self.volumes[year].keys())):

				#Do the calculations for daily so we can do daily AD later
				for day in sorted(list(self.volumes[year][month].keys())):
					date = "{0}-{1:0>2}-{2:0>2}".format(year, month, day);

					close = self.closes[date];
					high = self.highs[date];
					low = self.lows[date];


					#Calculate daily MFM and MFV
					#-MFM as zero affects nothing, and helps avoid ZeroDivisionError (when high == low)
					mfm = 0;
					if (high != low):
						mfm = ((close - low) - (high - close)) / (high - low);
					mfv = mfm * self.volumes[year][month][day];
					ad += mfv;

					#Ensure we don't get KeyErrors
					if (year not in self.ad.keys()):
						self.ad[year] = {};
					if (month not in self.ad[year].keys()):
						self.ad[year][month] = {};

					#Fill in our data structures
					self.ad[year][month][day] = ad;
					self.adList.append( [pd.to_datetime(date), ad] );



	def calculateAroon(self, periodLength):
		"""
		Measures if a security is in a trend, the magnitude of that trend, and whether that trend is likely to reverse (or not)
		
		Aroon Up:   ( (25 - Days Since 25 Day High) / 25 ) * 100
		Aroon Down: ( (25 - Days Since 25 Day Low) / 25 ) * 100
		"""
		last25Highs = [];
		last25Lows = [];
		date = self.earliestDate;
		currentDate = self.latestDate;

		#Calculate Aroon Indicators for every date we have
		while(date != currentDate):
			dateStr = str(date).split(' ')[0]
			year = int(dateStr[0:4]);
			month = int(dateStr[5:7]);
			day = int(dateStr[8:10]);

			#Retrieve highest value for this date
			highValue = None;
			try:
				highValue = self.highs[dateStr];
			except KeyError:
				date += pd.Timedelta('1 day');
				continue;

			last25Highs.append(highValue);
			if (len(last25Highs) > periodLength):
				last25Highs.pop(0);

			#Retrieve lowest value for this date
			lowValue = None;
			try:
				lowValue = self.lows[dateStr];
			except KeyError:
				date += pd.Timedelta('1 day');
				continue;

			last25Lows.append(lowValue);
			if (len(last25Lows) > periodLength):
				last25Lows.pop(0);

			#Calculate Aroon Up
			timeSinceHigh = periodLength - last25Highs.index(max(last25Highs));
			aroonUp = ( (periodLength - timeSinceHigh) / periodLength ) * 100;

			#Calculate Aroon Down
			timeSinceLow = periodLength - last25Lows.index(min(last25Lows));
			aroonDown = ( (periodLength - timeSinceLow) / periodLength ) * 100;

			#Ensure we don't get KeyErrors
			if (year not in self.aroon.keys()):
				self.aroon[year] = {};
			if (month not in self.aroon[year].keys()):
				self.aroon[year][month] = {};
			if (day not in self.aroon[year][month].keys()):
				self.aroon[year][month][day] = {};

			#Fill in our data structures
			self.aroon[year][month][day]["Up"] = aroonUp;
			self.aroon[year][month][day]["Down"] = aroonDown;
			self.aroonList.append( [date, aroonUp, aroonDown] );

			#Increment our counter
			date += pd.Timedelta('1 day');



#-------------------------------Plotting Methods----------------------------------------

	def plotPEtoPBV(self, startDate, endDate):
		'''Plots the PE * PBV value for a stock'''
		#Startdate and enddate must be in pd_datetime format already

		lowestDecisionRatio = 0;

		#Get our information from the object
		dataList = [];
		for key in self.information["PE"]:
			date = pd.to_datetime(key);

			if (date < startDate or date > endDate):
				continue;

			#Calculate the decision ratio
			decisionRatio = None;
			try:
				decisionRatio = (self.information["PE"][key] * self.information["PBV"][key]);
			except KeyError:
				continue;

			if (decisionRatio < lowestDecisionRatio):
				lowestDecisionRatio = decisionRatio;

			dataList.append( [date, decisionRatio] );

		fig, ax = plt.subplots();

		#Plot data
		ax.scatter(*zip(*dataList));
		ax.hlines(self.limit, startDate, endDate, color='r', linewidth=3);

		#Format plot
		fig.suptitle(self.ticker + " (P/E)*(P/BV) Score Over Time")
		
		if (startDate is not None and endDate is not None):
			plt.xlim(startDate, endDate);
		
		plt.ylim(lowestDecisionRatio, 100);
		ax.set_xlabel("Date");
		ax.set_ylabel("Indicator");

		fig.autofmt_xdate();

		#Show plot
		plt.show();



	def plotAD(self, startDate, endDate):
		"""
		Plot this stock's Accumulation/Distribition Line
		"""

		toPlot = self.adList

		#CAN EITHER TO THIS, OR JUST SET THE XLIM
		if (startDate is None):
			if (endDate is None):
				pass;
			else:
				toPlot = [info for info in self.adList if info[0] <= endDate];
		else:
			if (endDate is None):
				toPlot = [info for info in self.adList if info[0] >= startDate];
			else:
				toPlot = [info for info in self.adList if info[0] <= endDate and info[0] >= startDate]

		fig, ax = plt.subplots();
		ax.plot(*zip(*toPlot));
		ax.hlines(0, toPlot[0][0], toPlot[-1][0], linewidth=2);

		#Formatter method to get us "10M, 1M, etc"
		def millions(x, pos):
			return '%1.0fM' % (x*1e-6)

		formatter = mticker.FuncFormatter(millions);

		fig.suptitle(self.ticker + " Accumulation/Distribution Line");
		ax.set_xlabel("Date");
		ax.set_ylabel("A/D");
		ax.yaxis.set_major_formatter(formatter);
		fig.autofmt_xdate();
		plt.show();



	def plotClosesLineGraph(self, startDate, endDate):
		"""
		Plots the closes for a stock as a line graph
		Rough granularity, only at the day level b/c we don't have access to intraday trade info
		"""
		
		toPlot = self.closeList

		#CAN EITHER TO THIS, OR JUST SET THE XLIM
		if (startDate is None):
			if (endDate is None):
				pass;
			else:
				toPlot = [info for info in self.closeList if info[0] <= endDate];
		else:
			if (endDate is None):
				toPlot = [info for info in self.closeList if info[0] >= startDate];
			else:
				toPlot = [info for info in self.closeList if info[0] <= endDate and info[0] >= startDate]


		fig, ax = plt.subplots();
		ax.plot(*zip(*toPlot));

		fig.suptitle(self.ticker + " Closes");
		ax.set_xlabel("Date");
		ax.set_ylabel("Close Price");
		fig.autofmt_xdate();
		plt.show();



	def plotClosesCandlestickOHLC(self, startDate, endDate):
		"""
		Plots the closes for a stock as a Candlestick OHLC plot
		"""




#-------------------------------Decision Making Methods----------------------------------------

	def makeDecisionInTimeframe(self, startDate, endDate, outlier):
		"""
		Decide if this stock meets the limit criteria for a given timeframe
		"""
		sDate = startDate;
		eDate = endDate
		if (startDate is None):
			sDate = pd.to_datetime('1800-01-01');
		if (endDate is None):
			eDate = pd.to_datetime('today');
		ratioList = []

		for key in self.information["PE"]:
			keyDate = pd.to_datetime(key);
			if (keyDate < sDate or keyDate > eDate):
				continue;

			try:
				pe = self.information["PE"][key];
				pbv = self.information["PBV"][key];
			except KeyError:
				continue;

			ratio = pe*pbv;

			ratioList.append(ratio);

		npRatioList = np.asarray(ratioList);
		avg = np.mean(npRatioList);
		std = np.std(npRatioList);
		self.ratio = avg;

		#Method to reject any data points outside 'm' standard deviations from the mean
		def reject_outliers(data, m):
			return data[abs(data - np.mean(data)) < m * np.std(data)]

		npRatioListNoOutliers = reject_outliers(npRatioList, outlier);
		avg2 = np.mean(npRatioListNoOutliers);
		std2 = np.std(npRatioListNoOutliers);
		self.ratioWithoutOutliers = avg2;


		self.decision = (avg2 <= self.limit);
		self.decision = (avg <= self.limit);



if __name__ == "__main__":
	print("Stock.py isn't made to be called directly!");
	sys.exit();

