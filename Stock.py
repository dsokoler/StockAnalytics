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
	"""


	def __init__(self, ticker, limit=22.5):
		self.ticker = ticker;		#Ticker of this stock
		self.information = None;	#Information on the stock
		self.decision = None;		#Is this stock a good or bad pick
		self.limit = limit;			#The PE*PBV limit (less means a better stock, but is harder to find)



	def makeDecisionInTimeframe(self, startDate, endDate, outlier, rejectOutliers):
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
		std = np.std(npRatioList);
		if (rejectOutliers):
			npRatioList = reject_outliers(npRatioList, outlier);

		avg = np.mean(npRatioList);

		print("Ratio: " + str(avg) + "        Std dev: " + str(std));

		return avg <= self.limit;



	def retrieveRatios(self):
		#Set up our data holder
		historicData = {};
		historicData["PE"] = {};
		historicData["PBV"] = {};

		#Retrieve information needed to access Intrinio API
		config = configparser.ConfigParser();
		config.read("config.ini");
		username = config["INTRINIO"]["username"];
		password = config["INTRINIO"]["password"];

		url = "https://api.intrinio.com/historical_data?identifier={0}&item={1}";

		keys = [
			("PE", "pricetoearnings"),
			("PBV", "pricetobook")
		];

		#Get information from API
		for keyset in keys:
			apiUrl = url.format(self.ticker, keyset[1]);
			r = requests.get(apiUrl, auth=(username, password));
			d = r.json();

			if (d["data"] == None):
				print("No data for " + self.ticker);
				break;

			for item in d["data"]:
				if (item["value"] == "nm"):
					continue;

				historicData[keyset[0]][item["date"]] = item["value"];

		self.information = historicData;
		return historicData;



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

		config = configparser.ConfigParser();
		config.read("config.ini");
		username = config["INTRINIO"]["username"];
		password = config["INTRINIO"]["password"];


		for keySet in keys[0]:
			print("Filling for " + keySet[0]);
			url = keys[1].format(self.ticker, keySet[1]);
			r = requests.get(url, auth=(username, password));
			
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

