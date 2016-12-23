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
	Represents a suite of methods utilized to conduct stock analysis in the way of Warren Buffet
	Looks for stocks with a (P/E) * (P/BV) <= 22.5 (or the specified limit, default is 22.5)

	P = (# of Outstanding Shares) * (Current Share Price)
	E = ((Net Income) - (Dividends on Preferred Stock)) / (Average Outstanding Shares)
		Dividends = (Equity's Dividend Rate) * (Par Value of the Preferred Stock)
	BV = (Tangible Assets) - (Liabilities)	

	Process:
	 -Initialize stock object
	 -Retrieve stock information (retrieveRatios)
	 -Make decision (makeDecisionInTimeframe)
	"""

	#Retrieve information needed to access Intrinio API
	config = configparser.ConfigParser();
	config.read("config.ini");
	username = config["INTRINIO"]["username"];
	password = config["INTRINIO"]["password"];


	def __init__(self, ticker, startDate, endDate, limit, outlier=1):
		self.ticker = ticker;				#Ticker of this stock
		self.information = None;			#Information on the stock
		self.ratio = None;					#The ratio indicator with all data
		self.ratioWithoutOutliers = None;	#The ratio indicator sans outliers
		self.decision = None;				#Is this stock a good or bad pick
		self.startDate = startDate;			#The start of the timeframe for our analysis
		self.endDate = endDate;				#The end of the timeframe for our analysis
		self.limit = limit;					#The PE*PBV limit (less means a better stock, but is harder to find)
		self.outlier = outlier;				#Number of standard deviations to be considered an outlier
		self.retrieveRatios();
		self.makeDecisionInTimeframe(startDate, endDate, outlier);

		#		
		self.earliestDate = None;	#Earliest date seen in our dataset
		self.latestDate = None;		#Latest date seen in our dataset

		self.opens = {};		#Holds date to open price
		self.retrieveOpens();
		
		self.closes = {};		#Holds date to close price
		self.retrieveCloses();
		
		self.highs = {};		#Holds date to high price
		self.retrieveHighs();
		
		self.lows = {};			#Holds date to low price
		self.retrieveLows();

		self.volumes = {};		#Holds volumes for the stock
		self.retrieveVolumes();

		self.stochastics = {};	#Holds stochastic information about the stock
		self.calculateStochastics();

		self.mfv = {};
		self.calculateMFV();



	def retrieveOpens(self):
		url = "https://api.intrinio.com/historical_data?identifier={0}&item=adj_open_price".format(self.ticker);
		r = requests.get(url, auth=(Stock.username, Stock.password));
		d = r.json();

		for item in d["data"]:
			if (item["value"] == "nm"):
				continue;

			date = item["date"];
			value = item["value"];
			self.opens[date] = value;

			datetime = pd.to_datetime(date);

			if (self.earliestDate is None or datetime < self.earliestDate):
				self.earliestDate = datetime;
			if (self.latestDate is None or datetime > self.latestDate):
				self.latestDate = datetime;



	def retrieveCloses(self):
		url = "https://api.intrinio.com/historical_data?identifier={0}&item=adj_close_price".format(self.ticker);
		r = requests.get(url, auth=(Stock.username, Stock.password));
		d = r.json();

		for item in d["data"]:
			if (item["value"] == "nm"):
				continue;

			date = item["date"];
			value = item["value"];
			self.closes[date] = value;

			datetime = pd.to_datetime(date);

			if (self.earliestDate is None or datetime < self.earliestDate):
				self.earliestDate = datetime;
			if (self.latestDate is None or datetime > self.latestDate):
				self.latestDate = datetime;



	def retrieveHighs(self):
		url = "https://api.intrinio.com/historical_data?identifier={0}&item=adj_high_price".format(self.ticker);
		r = requests.get(url, auth=(Stock.username, Stock.password));
		d = r.json();

		for item in d["data"]:
			if (item["value"] == "nm"):
				continue;

			date = item["date"];
			value = item["value"];
			self.highs[date] = value;

			datetime = pd.to_datetime(date);

			if (self.earliestDate is None or datetime < self.earliestDate):
				self.earliestDate = datetime;
			if (self.latestDate is None or datetime > self.latestDate):
				self.latestDate = datetime;



	def retrieveLows(self):
		url = "https://api.intrinio.com/historical_data?identifier={0}&item=adj_low_price".format(self.ticker);
		r = requests.get(url, auth=(Stock.username, Stock.password));
		d = r.json();

		for item in d["data"]:
			if (item["value"] == "nm"):
				continue;

			date = item["date"];
			value = item["value"];
			self.lows[date] = value;

			datetime = pd.to_datetime(date);

			if (self.earliestDate is None or datetime < self.earliestDate):
				self.earliestDate = datetime;
			if (self.latestDate is None or datetime > self.latestDate):
				self.latestDate = datetime;



	def retrieveVolumes(self):
		url = "https://api.intrinio.com/historical_data?identifier={0}&item=adj_volume".format(self.ticker);
		r = requests.get(url, auth=(Stock.username, Stock.password));
		d = r.json();

		for item in d["data"]:
			if (item["value"] == "nm"):
				continue;

			date = item["date"];
			year = int(date[0:4]);
			month = int(date[5:7]);
			day = int(date[8:10]);

			if (year not in self.volumes.keys()):
				self.volumes[year] = {};
			if (month not in self.volumes[year].keys()):
				self.volumes[year][month] = {};

			value = item["value"];
			self.volumes[year][month][day] = value;

			datetime = pd.to_datetime(date);

			if (self.earliestDate is None or datetime < self.earliestDate):
				self.earliestDate = datetime;
			if (self.latestDate is None or datetime > self.latestDate):
				self.latestDate = datetime;




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

				historicData[keyset[0]][item["date"]] = item["value"];

		self.information = historicData;



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

			date += pd.Timedelta("1 day");



	def calculateMFV(self):
		"""
		Money Flow Multiplier = [(Close - Low) - (High - Close)] / (High - Low)  |  Should be -1 <= x <= 1
		Money Flow Volume = MFM * (Volume for Period)
		AD = (Previous AD) + MFV

		Period is 'day', 'month', 'year'
		"""

		#Do the calculations for yearly so we can do yearly AD later
		for year in list(self.volumes.keys()):
			yearlyMFM = 0;
			yearlyVolumeAverage = 0;
			numYearlyVolumes = 0;

			#Do the calculations for monthly so we can do monthly AD later
			for month in list(self.volumes[year].keys()):
				monthlyMFM = 0;
				monthlyVolumeAverage = 0;
				numMonthlyVolumes = 0;

				#Do the calculations for daily so we can do daily AD later
				for day in list(self.volumes[year][month].keys()):
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

					#Ensure we don't get KeyErrors
					if (year not in self.mfv.keys()):
						self.mfv[year] = {};
					if (month not in self.mfv[year].keys()):
						self.mfv[year][month] = {};

					self.mfv[year][month][day] = mfv;
		'''					
					#Update our cumulative monthly MFM, volume, and count
					monthlyMFM += mfm;
					monthlyVolumeAverage += self.volumes[year][month][day];
					numMonthlyVolumes += 1;
					
					#Update our cumulative yearly MFM, volume, and count
					yearlyMFM += mfm;
					yearlyVolumeAverage += self.volumes[year][month][day];
					numYearlyVolumes += 1;

				#Calculate our monthly MFV
				monthlyVolumeAverage = (monthlyVolumeAverage / numMonthlyVolumes);
				monthlyMFM = (monthlyMFM / numMonthlyVolumes);
				monthlyMFV = (monthlyMFM * monthlyVolumeAverage);
				self.mfv[year][month]["MFV"] = monthlyMFV;

			#Calculate our yearly MFV
			yearlyVolumeAverage = (yearlyVolumeAverage / numYearlyVolumes);
			yearlyMFM = (yearlyMFM / numYearlyVolumes);
			yearlyMFV = (yearlyMFM * yearlyVolumeAverage);
			self.mfv[year]["MFV"] = yearlyMFV;

		print(str(self.mfv));
		'''



	#BUGGY AF, GOOGLE RETURNS AD OF 33 MILLION, should be at ~2500
	def calculateAD(self, startDate, endDate):
		"""
		Calculates the Accumulation/Distribution for a time interval at a set granularity
		AD = (Previous AD) + MFV
		"""
		date = None;
		if (startDate is None):
			minYear = min(self.mfv.keys());
			minMonth = min(self.mfv[minYear].keys());
			minDay = min(self.mfv[minYear][minMonth]);
			date = "{0}-{1:0>2}-{2:0>2}".format(minYear, minMonth, minDay);
		else:
			date = startDate;
		
		currentDate = None;
		if (endDate is None):
			maxYear = max(self.mfv.keys());
			maxMonth = max(self.mfv[minYear].keys());
			maxDay = max(self.mfv[minYear][minMonth]);
			currentDate = "{0}-{1:0>2}-{2:0>2}".format(maxYear, maxMonth, maxDay);
		else:
			currentDate = endDate;

		ad = 0;
		date = pd.to_datetime(date);
		currentDate = pd.to_datetime(currentDate);
		while (date != currentDate):
			strDate = str(date);
			year = int(strDate[0:4]);
			month = int(strDate[5:7]);
			day = int(strDate[8:10]);

			try:
				ad += self.mfv[year][month][day];
			except KeyError:
				date += pd.Timedelta('1 day');
				continue;

			date += pd.Timedelta('1 day');

		return ad;



	def makeDecisionInTimeframe(self, startDate, endDate, outlier):
		"""
		Decide if this stock meets the limit criteria for a given timeframe
		"""
		ratioList = []

		for key in self.information["PE"]:
			keyDate = pd.to_datetime(key);
			if (keyDate < startDate or keyDate > endDate):
				continue;

			pe = self.information["PE"][key];
			pbv = self.information["PBV"][key];
			ratio = pe*pbv;

			ratioList.append(ratio);

		npRatioList = np.asarray(ratioList);
		avg = np.mean(npRatioList);
		std = np.std(npRatioList);
		self.ratio = avg;

		npRatioListNoOutliers = reject_outliers(npRatioList, outlier);
		avg2 = np.mean(npRatioListNoOutliers);
		std2 = np.std(npRatioListNoOutliers);
		self.ratioWithoutOutliers = avg2;


		self.decision = (avg2 <= self.limit);
		self.decision = (avg <= self.limit);



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
		plt.xlim(startDate, endDate);
		plt.ylim(lowestDecisionRatio, 100);
		ax.set_xlabel("Date");
		ax.set_ylabel("Indicator");

		fig.autofmt_xdate();

		#Show plot
		plt.show();




	def retrieveInformation(self):
		"""
		Retrieve as much information as we can in order to calcualte PE and PBV
		User https://intrinio.com/sdk/web-api#
		Other tags: http://docs.intrinio.com/tags/intrinio-public#historical-data
		"""

		#Stuff thats done on a monthly basis
		keys = (
			[("Shares", "volume"),
			("SharePrice", "adj_close_price"),
			],
			"https://api.intrinio.com/historical_data?identifier={0}&item={1}&frequency=monthly"
		);

		#Stuff thats done on a yearly basis
		keys2 = (
			[("NetIncome", "netincome"),	#Doesn't seem to be any data on intrinio about net income
			 ("Dividends", "cashdividendspershare")
			],
			"https://api.intrinio.com/historical_data?identifier={0}&item={1}&frequency=yearly"
		);

		#Stuff thats done on a daily basis
		keys3 = (
			[("AverageShares", "average_daily_volume")],
			"https://api.intrinio.com/historical_data?identifier={0}&item={1}&frequency=daily"
		);

		#Stuff thats done every three months
		keys4 = (
			[("Dividends", "cashdividendspershare"),
			 ("Assets", "totalassets"),
			 ("Liabilities", "totalliabilities")
			 ("PE", "pricetoearnings")
			 ("PBV", "pricetobook")
			],
			"https://api.intrinio.com/historical_data?identifier={0}&item={1}"
		);

		historicData = {};

		for keySet in keys[0]:
			print("Filling for " + keySet[0]);
			url = keys[1].format(self.ticker, keySet[1]);
			r = requests.get(url, auth=(Stock.username, Stock.password));
			
			d = r.json();


			if (keySet[0] == "Assets"):
				print(str(d));


			data = d["data"];
			for info in data:
				year = info["date"][:4];
				month = info["date"][5:7];

				#Apparantly people do stuff every three months, soooooooo
				if (int(month) % 3 != 0):
					continue;

				#Fill set with empty dictionary to avoid key error
				if (year not in historicData.keys()):
					historicData[year] = {};
				if (month not in historicData[year].keys()):
					historicData[year][month] = {};

				historicData[year][month][keySet[0]] = info["value"];

		'''
		url = "https://api.intrinio.com/historical_data?identifier={0}&item={1}".format(self.ticker, "cashdividendspershare");
		r = requests.get(url, auth=(username, password));
		d = r.json();
		print(str(d));
		'''
		print();
		print(str(historicData));
		print();

		

def reject_outliers(data, m):
    return data[abs(data - np.mean(data)) < m * np.std(data)]



if __name__ == "__main__":
	print("Stock.py isn't made to be called directly!");
	sys.exit();

