import sys, configparser, json
from datetime import datetime


importError = False;

try:
	import requests
except ImportError:
	print("Please install requests: 'pip3 install requests'");
	importError = True;

#MatPlotLib for visualizations
try:
	import matplotlib.pyplot as plt;
	import matplotlib.ticker as mticker
	from matplotlib.finance import candlestick_ohlc
	import matplotlib.dates as mdates
except ImportError:
	print("Please install matplotlib: 'pip3 install matplotlib'");
	importError = True;

#Pandas is for datetimes
try:
	import pandas as pd
except ImportError:
	print("Please install Pandas: 'pip3 install pandas'");
	importError = True;

#Numpy for line of best fit
try:
	import numpy as np
except ImportError:
	print("Please install Numpy: 'pip3 install numpy'");
	importError = True;

try:
	from Database import Database;
except ImportError:
	print("Unable to find the Database module");
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

	For Calculate Methods: KeyError means there is NO data for that day, something being
	none indicates that there was PARTIAL data for that day
	"""

	#Retrieve information needed to access Intrinio API
	config = configparser.ConfigParser();
	config.read("config.ini");
	username = config["INTRINIO"]["username"];
	password = config["INTRINIO"]["password"];

	periods = [12, 26, 50, 200];

	kamaPeriod = 7;

	#Methods must be in the form 'calculateCALC'.  When we add a new calculation
	# method, add it's abbreviation and whether or not it utilizes a period here
	methods = {
	#   Name : Uses Period
		'SMA': True,
		'TMA': True,
		'SlopeMA': True,
		'EMA': True,
		'KAMA': True,
		'Stochastics': False,
		'AD': False,
		'Aroon': True,
		'OBV': False
	}

	def __init__(self, ticker, startDate, endDate, limit, period, database, outlier=1):
		"""
		Ticker: the abbreviation of this stock
		startDate: the date on which to start all our analysis
		endDate: the date on which to end all our analysis
		limit: the PE*PBV ratio limit
		period: 1 or more periods to calculate our MAs on
		"""
		if (type(period) == int and period not in Stock.periods):
			Stock.periods.append(period);
		elif(type(period)  == list):
			for p in period:
				if (p not in Stock.periods):
					Stock.periods.append(p);

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
		
		self.database = Database(database);
		self.database.updateStockInformation(ticker);
			
		#self.makeDecisionInTimeframe(startDate, endDate, outlier);

		self.earliestDate, self.latestDate, data = self.database.retrieveAllInformationForStock(ticker);

		#FIND A WAY TO AUTOMATE THIS BASED ON DATABASE COLUMNS
		#Dictionary is for easy analysis at certain time periods, list is for easy plotting over time periods
		self.opens = data['Dict']['Opens'];			#Holds date to open price
		self.openList = data['List']['Opens'];		#(Date, open)
		
		self.closes = data['Dict']['Closes'];		#Holds date to close price
		self.closeList = data['List']['Closes'];	#(Date, close)
		
		self.highs = data['Dict']['Highs'];			#Holds date to high price
		self.highList = data['List']['Highs'];		#(Date, high)
		
		self.lows = data['Dict']['Lows'];			#Holds date to low price
		self.lowList = data['List']['Lows'];		#(Date, low)

		self.volumes = data['Dict']['Volumes'];		#Holds volumes for the stock
		self.volumeList = data['List']['Volumes'];	#(Date, volume)

		self.pe = data['Dict']['PE'];				#Holds Price/Earnings ratios for the stock
		self.peList = data['List']['PE'];			#(Date, P/E)

		self.pbv = data['Dict']['PBV'];				#Holds Price/Book Value ratios for the stock
		self.pbvList = data['List']['PBV']			#(Date, P/BV)


		#SMA, EMA, KAMA, SlopeMA
		self.calcs = {}; 		#maName: {maPeriod: {date: value}}
		self.calcsList = {}; 	#maName: {maPeriod: [date, value]}

		#Force 'SMA' to be first calculation, as we need it for others
		methodKeyList = list(Stock.methods.keys());
		methodKeyList.insert(0, methodKeyList.pop(methodKeyList.index('SMA')))

		#Do all our calculations
		for method in methodKeyList:
			funcToCall = getattr(Stock, 'calculate' + method);

			#If 'funcToCall' uses a period
			periodsToUse = Stock.periods;
			if (Stock.methods[method]):
				#Avoid KeyError
				if (method not in self.calcs.keys()):
					self.calcs[method] = {};
				if (method not in self.calcsList.keys()):
					self.calcsList[method] = {};
				
				for p in periodsToUse:
					#If we've already calculated this for the stock
					if (self.database.isCalculated(self.ticker, method, p)):
						self.calcs[method][p], self.calcsList[method][p] = self.database.retrieveCalculation(self.ticker, method, p, self.startDate, self.endDate);
					#If we haven't already calculated this
					else:
						funcToCall(self, period=p);

			#'funcToCall' doesn't use a period
			else:
				#If we've already calculated this for the stock
				if (self.database.isCalculated(self.ticker, method, None)):
					self.calcs[method], self.calcsList[method] = self.database.retrieveCalculation(self.ticker, method, None, self.startDate, self.endDate);
				#If we haven't already calculated this
				else:
					funcToCall(self);

		self.objects = {}		#Holds items such as Doji, Marubozu, Spinning Tops, etc
		#self.identifyObjects();	#Marubozu, Doji, Spinning Tops, etc

		#self.database.printDB(self.ticker);



#-----------------------------------Calculation Methods-----------------------------------------
#Should probably break these up by type (trend/momentum prediction, overlap studies, etc)
#KAMA > EMA > (SlopeMA == TMA == SMA)
	
	def calculateSMA(self, period=12):
		"""
		Calculates the SMA for this stock with the given time period

		SMA = sum(LastXAverages) / X
		"""
		date = self.earliestDate;

		if ('SMA' not in self.calcs.keys()):
			self.calcs['SMA'] = {};
		elif (period in self.calcs['SMA'].keys()):
			print("Already calculated SMA for period " + str(period));
			return;
		if (period not in self.calcs['SMA'].keys()):
			self.calcs['SMA'][period] = {};

		if ('SMA' not in self.calcsList.keys()):
			self.calcsList['SMA'] = {};
		if (period not in self.calcsList['SMA'].keys()):
			self.calcsList['SMA'][period] = [];

		lastPeriodCloses = [];
		while(len(lastPeriodCloses) < period):
			dateStr = str(date).split(' ')[0];
			#Will err if we try to access a day the market was closed
			try:
				lastPeriodCloses.append( self.closes[dateStr] );
			except KeyError:
				pass;

			date += pd.Timedelta('1 day');

		while(date <= self.latestDate):
			dateStr = str(date).split(' ')[0]

			sma = sum(lastPeriodCloses)/period;		#mean(lastPeriodCloses)

			#Happens when we hit a weekend
			todayClose = None;
			try:
				todayClose = self.closes[dateStr];
			except KeyError:
				date += pd.Timedelta('1 day');
				continue;

			#todayClose would be None if the API did not have close data for this date
			if (todayClose is not None):
				lastPeriodCloses.append(todayClose);

			if (len(lastPeriodCloses) > period):
				lastPeriodCloses.pop(0);
			
			self.calcs['SMA'][period][dateStr] = sma;
			self.calcsList['SMA'][period].append( [date, sma] );

			date += pd.Timedelta('1 day');

		self.database.addCalculation(self.ticker, 'SMA', period, self.calcsList['SMA'][period]);



	def calculateTMA(self, period=12):
		"""
		Calculates the triangular moving average for a stock over a period of time
		"""
		
		if ('TMA' not in self.calcs.keys()):
			self.calcs['TMA'] = {};
		elif (period in self.calcs['TMA'].keys()):
			print("Already calculated TMA for period " + str(period));
			return;
		if (period not in self.calcs['TMA'].keys()):
			self.calcs['TMA'][period] = {};

		if ('TMA' not in self.calcsList.keys()):
			self.calcsList['TMA'] = {};
		if (period not in self.calcsList['TMA'].keys()):
			self.calcsList['TMA'][period] = [];

		periodToTD = pd.Timedelta(str(period) + ' days');
		date = self.earliestDate + periodToTD;
		dateStr = str(date).split(' ')[0];

		#Fill the initial array of closes
		lastPeriodSMAs = [];
		while(len(lastPeriodSMAs) < (period - 1)):
			try:
				lastPeriodSMAs.append(self.calcs['SMA'][period][dateStr]);
			except KeyError as k:
				pass;

			date += pd.Timedelta('1 day');
			dateStr = str(date).split(' ')[0];

		while(date <= self.latestDate):
			try:
				lastPeriodSMAs.append(self.calcs['SMA'][period][dateStr]);
			except KeyError:
				date += pd.Timedelta('1 day');
				dateStr = str(date).split(' ')[0];

			tma = sum(lastPeriodSMAs) / period;

			self.calcs['TMA'][period][dateStr] = tma;
			self.calcsList['TMA'][period].append( [date, tma] );

			date += pd.Timedelta('1 day');
			dateStr = str(date).split(' ')[0];

		self.database.addCalculation(self.ticker, 'TMA', period, self.calcsList['TMA'][period]);



	def calculateSlopeMA(self, period=2):
		"""
		Calculates the moving average of the slope the closes over the specified period

		slope = (y2 - y1)/(x2 - x1)
		"""

		if ('SlopeMA' not in self.calcs.keys()):
			self.calcs['SlopeMA'] = {};
		elif (period in self.calcs['SlopeMA'].keys()):
			print("Already calculated SlopeMA for period " + str(period));
			return;
		if (period not in self.calcs['SlopeMA'].keys()):
			self.calcs['SlopeMA'][period] = {};

		if ('SlopeMA' not in self.calcsList.keys()):
			self.calcsList['SlopeMA'] = {};
		if (period not in self.calcsList['SlopeMA'].keys()):
			self.calcsList['SlopeMA'][period] = [];

		date = self.earliestDate;
		dateStr = None;
		lastPeriodCloses = [];
		lastPeriodDates = [];

		while(len(lastPeriodCloses) < (period - 1) ):
			dateStr = str(date).split(' ')[0];
			#Will err if we try to access a day the market was closed
			try:
				lastPeriodCloses.append( self.closes[dateStr] );
			except KeyError:
				pass;

			date += pd.Timedelta('1 day');

		slopeOverPeriod = 0;
		while(date <= self.latestDate):
			dateStr = str(date).split(' ')[0];

			#Occurs when we try to access a day that the market was closed
			todayClose = None;
			try:
				todayClose = self.closes[dateStr];
			except KeyError:
				date += pd.Timedelta('1 day');
				continue;

			#Occurs if the API does not have close information for this date
			if (todayClose is not None):
				lastPeriodCloses.append(todayClose);
				lastPeriodDates.append(dateStr);

				slopeOverPeriod = (lastPeriodCloses[-1] - lastPeriodCloses[0]) / np.busday_count(lastPeriodDates[-1], lastPeriodDates[0]);

			self.calcs['SlopeMA'][period][dateStr] = slopeOverPeriod;
			self.calcsList['SlopeMA'][period].append( [dateStr, slopeOverPeriod] );

			if (len(lastPeriodCloses) > period):
				lastPeriodCloses.pop(0);
				lastPeriodDates.pop(0);

			date += pd.Timedelta('1 day');

		self.database.addCalculation(self.ticker, 'SlopeMA', period, self.calcsList['SlopeMA'][period]);



	def calculateEMA(self, period=12, emaType='Single', percentage=None):
		"""
		Calculates the EMA for this stock based on the specified time period (in days)
		For regular EMA, emaType='Single'	(Default)
		For double EMA, emaType='Double'
		For triple EMA, emaType='Triple'
		
		EITHER PERIOD OR PERCENTAGE SHOULD HAVE A VALUE, THE OTHER SHOULD BE NONE

		To convert from percentage to period: (2/percentage) - 1

		Multiplier: 2/(period + 1)
		EMA = prevEMA + Multiplier * (Close - prevEMA)
		"""

		emaTypeToNumber = {
			'Single': '',
			'Double': '2',
			'Triple': '3'
		};

		toMult = period;
		if(period is None):
			toMult = (2/percentage) - 1;

		multiplier = 2/(toMult + 1);

		periodToTD = pd.Timedelta(str(period) + ' days');

		if ('EMA' not in self.calcs.keys()):
			self.calcs['EMA'] = {};
		elif (period in self.calcs['EMA'].keys()):
			print("Already calculated EMA for period " + str(period));
			return;
		if (period not in self.calcs['EMA'].keys()):
			self.calcs['EMA'][period] = {};

		if ('EMA' not in self.calcsList.keys()):
			self.calcsList['EMA'] = {};
		if (period not in self.calcsList['EMA'].keys()):
			self.calcsList['EMA'][period] = [];

		date = self.earliestDate + periodToTD;
		dateStr = str(date - pd.Timedelta('1 day')).split(' ')[0];
		
		#UGLY AF!!!  Used to prevent keyerrors when the starting day is a Monday
		prevEma = None;
		if (dateStr not in self.calcs['EMA'][period].keys()):
			counter = 0;
			while (prevEma is None):
				d = date + pd.Timedelta(str(counter) + ' days');
				dStr = str(d).split(' ')[0];

				if (dStr not in self.calcs['SMA'][period].keys()):
					counter += 1;
					continue;
				else:
					prevEma = self.calcs['SMA'][period][dStr]
		else:
			prevEma = self.calcs['EMA'][period][dateStr];

		#This makes it easier to do double/triple EMA
		def ema(prevEma, multiplier, close):
			return (prevEma + multiplier*(close - prevEma));

		while(date <= self.latestDate):
			dateStr = str(date).split(' ')[0]

			todayClose = None;
			#Happens when the market wasn't open, (holiday, weekend, etc)
			try:
				#ema and ema2 MUST be equal!!
				todayClose = self.closes[dateStr];
			except KeyError:
				date += pd.Timedelta('1 day');
				continue;

			expMovAvg = None;
			emaName = None;

			#Occurs if the API didn't have close information for this date
			if (todayClose is None):
				expMovAvg = prevEma;
			else:
				expMovAvg = ema(prevEma, multiplier, todayClose);
				expMovAvg2 = prevEma + multiplier * (todayClose - prevEma);
				
				#( 2*EMA(n) ) – ( EMA(EMA(n)) ) where ‘n’ is #ofDays
				if (emaType == 'Double'):
					expMovAvg = 2 * ema(prevEma, multiplier, expMovAvg) - ema( prevEma, multiplier, ema(prevEma, multiplier, expMovAvg) );
				
				#3*EMA(n) – 3*EMA(EMA(n)) + EMA(EMA(EMA(n)))
				elif (emaType == 'Triple'):
					expMovAvg = 3 * ema(prevEma, multiplier, expMovAvg) - 3 * ema( prevEma, multiplier, ema(prevEma, multiplier, expMovAvg) ) + ema(prevEma, multiplier, ema(prevEma, multiplier, ema(prevEma, multiplier, expMovAvg)));

				prevEma = expMovAvg;

				emaName = (emaTypeToNumber[emaType] + 'EMA');

			self.calcs[emaName][period][dateStr] = expMovAvg;
			self.calcsList[emaName][period].append( [date, expMovAvg] );

			date += pd.Timedelta('1 day');

		self.database.addCalculation(self.ticker, 'EMA', period, self.calcsList['EMA'][period]);



	def calculateKAMA(self, period=10, fastest=2, slowest=30):
		"""
		Period: recommended to be 10
		Fastest: recommended to be 2
		Slowest: recommended to be 30

		This is a Kaufman Adaptive Moving Average (KAMA):
		1.	Efficiency Ratio = Change / Volatility
			a.	Change = abs(Close – close10PeriodsAgo)
			b.	Volatility is the sum of the absolute value of the last ten price changes

		2.	FastestSC = 2/(FastestEMA + 1)
		3.	SlowestSC = 2/(SlowestEMA + 1)
		4.	Smoothing Constant = [ER * (FastestSC – SlowestSC) + SlowestSC]^2 = [ER * (2/3 – 2/31) + 2/31]^2
		"""
		date = self.earliestDate;
		dateStr = None;

		if ('KAMA' not in self.calcs.keys()):
			self.calcs['KAMA'] = {};
		elif (period in self.calcs['KAMA'].keys()):
			print("Already calculated KAMA for period " + str(period));
			return;
		if (period not in self.calcs['KAMA'].keys()):
			self.calcs['KAMA'][period] = {};

		if ('KAMA' not in self.calcsList.keys()):
			self.calcsList['KAMA'] = {};
		if (period not in self.calcsList['KAMA'].keys()):
			self.calcsList['KAMA'][period] = [];

		lastPeriodCloses = [];
		lastPeriodPriceChanges = []	#index corresponds directly to the same index in lastPeriodCloses

		#Fill up our initial 'period' closes, so we can calculate 'Change' easily
		while(len(lastPeriodCloses) < period):
			dateStr = str(date).split(' ')[0];
			
			#Will err if we try to access a day the market was closed
			try:
				todayClose = self.closes[dateStr]
			except KeyError:
				date += pd.Timedelta('1 day');
				continue;
			
			#Occurs when the API does not have close information for this date
			if (todayClose is None):
				date += pd.Timedelta('1 day');
				continue;

			lastPeriodCloses.append( self.closes[dateStr] );

			#Calculate the most recent change
			if (len(lastPeriodCloses) > 1):
				lastPeriodPriceChanges.append( abs(lastPeriodCloses[-1] - lastPeriodCloses[-2]) );
			else:
				lastPeriodPriceChanges.append(0);

			date += pd.Timedelta('1 day');

		#Our first "prevKama" is just the SMA of the first 'period' closes
		prevKama = sum(lastPeriodCloses)/len(lastPeriodCloses);

		#Start doing our calculations
		while (date <= self.latestDate):
			dateStr = str(date).split(' ')[0];

			#Occurs when we try to access a day that the market was closed
			todayClose = None;
			try:
				todayClose = self.closes[dateStr];
			except KeyError:
				date += pd.Timedelta('1 day');
				continue;

			kama = prevKama;

			#Make sure we don't do calculations on 'None' data
			if (todayClose is not None):
				#Change = abs(Close – close10PeriodsAgo)
				change = abs(todayClose - lastPeriodCloses[0]);
				
				#Volatility is the sum of the absolute value of the last ten price changes
				volatility = sum(lastPeriodPriceChanges);
				
				#Efficiency Ratio = Change / Volatility
				er = change/volatility;

				#Calculate our fastest Smoothing Constant
				fastestSC = None;
				if (fastest is None):
					fastestSC = 2/(2 + 1);
				else:
					fastestSC = 2/(fastest + 1);

				#Calculate our slowest Smoothing Constant
				slowestSC = None;
				if (slowest is None):
					slowestSC = 2/(10 + 1);
				else:
					slowestSC = 2/(slowest + 1);

				#Our real Smoothing Constant = [ER * (FastestSC – SlowestSC) + SlowestSC]^2 = [ER * (2/3 – 2/31) + 2/31]^2
				sc = (er * (fastestSC - slowestSC) + slowestSC) ** 2;	# '**' is exponentiation
				
				#KAMA = prevKAMA + SmoothingConstant * (Close - prevKAMA)
				kama = prevKama + sc * (todayClose - prevKama);

			self.calcs['KAMA'][period][dateStr] = kama;
			self.calcsList['KAMA'][period].append( [date, kama] );

			#Fix our last KAMA and our last 'period' information (close and change)
			prevKama = kama;
			lastPeriodCloses.append(todayClose);
			lastPeriodCloses.pop(0);
			lastPeriodPriceChanges.append( abs(lastPeriodCloses[-1] - lastPeriodCloses[-2]) );
			lastPeriodPriceChanges.pop(0)

			date += pd.Timedelta('1 day');

		self.database.addCalculation(self.ticker, 'KAMA', period, self.calcsList['KAMA'][period]);



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

		stochastics = {};
		stochasticList = []

		lastFiveCloses = [];
		lastFiveHighs = [];
		lastFiveLows = [];
		date = self.earliestDate;
		currentDate = self.latestDate;

		lastThreeKs = [];

		#Calculate stochastics for every date we have
		prevK = 0;
		prevD = 0;
		while(date <= currentDate):
			dateStr = str(date).split(' ')[0]
			
			closeValue = None;
			highValue = None;
			lowValue = None;
			try:
				#Retrieve closing value for this date
				closeValue = self.closes[dateStr];

				#Retrieve highest value for this date
				highValue = self.highs[dateStr];

				#Retrieve lowest value for this date
				lowValue = self.lows[dateStr];
			except KeyError:	#odds are this is caused by this date being a non-trading day, or not having today's close
				date += pd.Timedelta("1 day");
				continue;

			#Occurs when the API doesn't have particular values, just take the last ones...
			if (closeValue is None or highValue is None or lowValue is None):
				k = prevK;
				d = prevD;

			else:
				lastFiveCloses.append(closeValue);
				if (len(lastFiveCloses) > 5):
					lastFiveCloses.pop(0);

				lastFiveHighs.append(highValue);
				if (len(lastFiveHighs) > 5):
					lastFiveHighs.pop(0);

				lastFiveLows.append(lowValue);
				if (len(lastFiveLows) > 5):
					lastFiveLows.pop(0);


				#Calculate 'k' point and 'd' point
				try:
					k = 100 * ( (lastFiveCloses[-1] - min(lastFiveLows)) / (max(lastFiveHighs) - min(lastFiveLows)) )
					d = ( sum(lastThreeKs) / 3);
				except ZeroDivisionError as zde:
					date += pd.Timedelta("1 day");
					continue;

			prevK = k;
			prevD = d;

			lastThreeKs.append(k);
			if (len(lastThreeKs) > 3):
				lastThreeKs.pop(0);

			#Store values
			stochastics[dateStr] = {};
			stochastics[dateStr]['K'] = k;
			stochastics[dateStr]['D'] = d;

			stochasticList.append( [date, k, d] );

			date += pd.Timedelta("1 day");

		self.database.addCalculation(self.ticker, 'Stochastics', None, stochasticList);

		self.calcs['Stochastics'] = stochastics;
		self.calcsList['Stochastics'] = stochasticList;



	def calculateAD(self):
		"""
		Money Flow Multiplier = [(Close - Low) - (High - Close)] / (High - Low)  |  Should be -1 <= x <= 1
		Money Flow Volume = MFM * (Volume for Period)
		Accumulation Distribution Point = (Previous AD) + MFV

		Period is 'day', 'month', 'year'
		"""
		adDict = {};
		adList = [];

		ad = 0;

		for date in sorted(self.volumes.keys()):
			close = None;
			high = None;
			low = None;

			try:
				close = self.closes[date];
				high = self.highs[date];
				low = self.lows[date];
			except KeyError:
				continue;

			#Occurs if the API does not have some data for this date
			if (close is not None and high is not None and low is not None):
				#Calculate daily MFM and MFV
				#-MFM as zero affects nothing, and helps avoid ZeroDivisionError (when high == low)
				mfm = 0;
				if (high != low):
					mfm = ((close - low) - (high - close)) / (high - low);
				mfv = mfm * self.volumes[date];
				ad += mfv;

			#Fill in our data structures
			adDict[date] = ad;
			adList.append( [pd.to_datetime(date), ad] );

		self.database.addCalculation(self.ticker, 'AD', None, adList);

		self.calcs['AD'] = adDict;
		self.calcsList['AD'] = adList;



	def calculateAroon(self, period=12):
		"""
		Measures if a security is in a trend, the magnitude of that trend, and whether that trend is likely to reverse (or not)
		
		Aroon Up:   ( (25 - Days Since 25 Day High) / 25 ) * 100
		Aroon Down: ( (25 - Days Since 25 Day Low) / 25 ) * 100
		"""
		period
		aroonDict = {};
		aroonList = [];

		last25Highs = [];
		last25Lows = [];
		date = self.earliestDate;
		currentDate = self.latestDate;

		#Calculate Aroon Indicators for every date we have
		aroonUp = 0;
		aroonDown = 0;
		while(date <= currentDate):
			dateStr = str(date).split(' ')[0]

			#Retrieve highest value for this date
			highValue = None;
			try:
				highValue = self.highs[dateStr];
			except KeyError:
				date += pd.Timedelta('1 day');
				continue;
			
			#Retrieve lowest value for this date
			lowValue = None;
			try:
				lowValue = self.lows[dateStr];
			except KeyError:
				date += pd.Timedelta('1 day');
				continue;

			#Occurs if the API does not have some information for that day
			if (highValue is not None and lowValue is not None):
				last25Highs.append(highValue);
				if (len(last25Highs) > period):
					last25Highs.pop(0);

				last25Lows.append(lowValue);
				if (len(last25Lows) > period):
					last25Lows.pop(0);

				#Calculate Aroon Up
				timeSinceHigh = period - last25Highs.index(max(last25Highs));
				aroonUp = ( (period - timeSinceHigh) / period ) * 100;

				#Calculate Aroon Down
				timeSinceLow = period - last25Lows.index(min(last25Lows));
				aroonDown = ( (period - timeSinceLow) / period ) * 100;

			#Ensure we don't get KeyErrors
			if (period not in aroonDict.keys()):
				aroonDict[period] = {};
			if (dateStr not in aroonDict[period].keys()):
				aroonDict[period][dateStr] = {};

			#Fill in our data structures
			aroonDict[period][dateStr]["Up"] = aroonUp;
			aroonDict[period][dateStr]["Down"] = aroonDown;
			aroonList.append( [date, aroonUp, aroonDown] );

			#Increment our counter
			date += pd.Timedelta('1 day');

		self.database.addCalculation(self.ticker, 'Aroon', period, aroonList);

		self.calcs['Aroon'] = aroonDict;

		if ('Aroon' not in self.calcsList.keys()):
			self.calcsList['Aroon'] = {};
		self.calcsList['Aroon'][period] = aroonList;



	def calculateOBV(self):
		"""
		Calculates the On-Balance Volume for a stock
		
		i.	 If todayClose > yesterdayClose, currentOBV = prevOBV + todayVolume
		ii.	 If todayClose < yesterdayClose, currentOBV = prevOBV – todayVolume
		iii. If todayClose == yesterdayClose, currentOBV = prevOBV

		When plotting, don't have Y axis labels.  We really only care about the 
		changes from point to point (slope), and what the line looks like.
		-High positive slope may indicate a soon-to-be price rise
		-High negative slope may inticate a soon-to-be price fall
		"""
		obv = 0;
		date = self.earliestDate;
		dateStr = str(date).split(' ')[0];

		obvDict = {};
		obvList = [];

		#Get our first data point
		yesterdayClose = None;
		while(yesterdayClose is None):
			volume = None;
			try:
				yesterdayClose = self.closes[dateStr];
				volume = self.volumes[dateStr];
				obv += volume;
			except KeyError:
				pass;
			else:
				#Need to add info to data structures before increasing date!
				obvDict[dateStr] = obv;
				obvList.append( [date, obv] );
				

			date += pd.Timedelta('1 day');
			dateStr = str(date).split(' ')[0];
		

		#Calculate the rest of the data points
		while(date <= self.latestDate):
			todayClose = None;
			todayVolume = None;

			#KeyError occurs when we try to access a day the market was closed
			try:
				todayClose = self.closes[dateStr];
				todayVolume = self.volumes[dateStr];
			except KeyError:
				date += pd.Timedelta('1 day');
				dateStr = str(date).split(' ')[0];
				continue;

			if (todayClose > yesterdayClose):
				obv = obv + todayVolume;
			elif (todayClose < yesterdayClose):
				obv = obv - todayVolume;

			obvDict[dateStr] = obv;
			obvList.append( [date, obv] );

			date += pd.Timedelta('1 day');
			dateStr = str(date).split(' ')[0];
			yesterdayClose = todayClose;

		self.calcs['OBV'] = obvDict;
		self.calcsList['OBV'] = obvList;

		self.database.addCalculation(self.ticker, 'OBV', None, obvList);





#-------------------------------Trend Identifier Methods--------------------------------

	def identifyObjects(self, candleOC, dojiOC, marubozuDiff):
		"""
		Identify all objects of relevance (IN THE APPROPRIATE ORDER!!)
		"""
		identifyLongCandles(candleOC);
		identifyDoji(dojiOC);
		identifyMarubozu(marubozuDiff);



	def identifyLongCandles(self, openCloseMultiplier):
		"""
		Identify dates that have long white or black candles

		hiLoMultiplier: the difference required to be a candle (i.e. high must be hiLoMultiplier*low)

		Long White Candle: 'LWC' : Open >>>>> Close
		Long Black Candle: 'LBC' : Close >>>>> Open

		HIGH VS LOW PERCENTAGE/MULTIPLIER TO BE A LWC/LBC?
		-e.g. for LWC open must be 1.5x close (or whatever it is)
		"""
		if ('Candles' in self.objects.keys()):
			print("Already calculated Long Candles for " + self.ticker);
			return;

		#Ensure no KeyErrors
		self.objects['Candles'] = {}
		self.objects['Candles']['LWC'] = {};
		self.objects['Candles']['LBC'] = {};

		#First Date!
		date = self.earliestDate;
		dateStr = str(date).split(' ')[0];

		#Start Calculations
		dayOpen = None;
		dayClose = None;
		while(date != self.latestDate):

			#Occurs when we have a day that the market was closed
			try:
				dayOpen = self.opens[dateStr];
				dayClose = self.closes[dateStr];
			except KeyError:
				date += pd.Timedelta('1 day');
				dateStr = str(date).split(' ')[0];
				continue;

				#LWC
				if (dayOpen >= dayClose * openCloseMultiplier):
					self.objects['Candles']['LWC'][dateStr] = True;

				#LBC
				elif (dayClose >= dayOpen * openCloseMultiplier):
					self.objects['Candles']['LBC'][dateStr] = True;

			date += pd.Timedelta('1 day');
			dateStr = str(date).split(' ')[0];



	def identifyDoji(self, openCloseMultiplier):
		"""
		Identify any points in time where there are any form of doji (open and close extremely close together)


		Regular Doji: 'D' : open and close are extremely close together
		Doji Evening Star: 'DES' : Long White Candle + Doji
		Doji Morning Star: 'DMS' : Long Black Candle + Doji
		Long Legged Doji: 'LLD' : Small Real Body w/ long upper and lower shadows of approximately equal length
		Dragonfly Doji: 'DD' : Open, close, and high are all equal, with a long lower shadow
					  : Look for Long White Candle beforehand
		Gravestone Doji: 'GD' : Open, close, and low are all equal, with a long upper shadow
					   : Look for Long Black Candle beforehand
		"""

		#Day + 1 b/c we are looking for LWC or LBC before some of these
		if ('LWC' not in self.objects.keys()):
			print("Please run 'identifyLongCandles' before 'identifyDoji'");
			sys.exit();

		if ('Doji' in self.objects.keys()):
			print("Already identified Doji locations for " + self.ticker);
			return;

		self.objects['Doji'] = {};			#Doji holder
		self.objects['Doji']['D'] = {};		#Regular Doji
		self.objects['Doji']['DES'] = {};	#Doji Evening Star
		self.objects['Doji']['DMS'] = {};	#Doji Morning Star
		self.objects['Doji']['LLD'] = {};	#Long Legged Doji
		self.objects['Doji']['DD'] = {};	#Dragonfly Doji
		self.objects['Doji']['GD'] = {};	#Gravestone Doji

		date = self.earliestDate + pd.Timedelta('1 day');
		dateStr = str(date).split(' ')[0];

		while(date != self.latestDate):
			#hasLWC = (dateStr in self.);
			#hasLBC = ();


			date += pd.Timedelta('1 day');
			dateStr = str(date).split(' ')[0];



	def identifyMarubozu(self, difference):
		"""
		Identify any points in time where there are any form of marubozu

		difference: how much different the open/high, etc need to be to form a Marubozu

		Black Marubozu: open was the high and the close was the low
		White Marubozu: open was the low and the close was the high
		"""
		date = self.earliestDate;
		dateStr = str(date).split(' ')[0];
		if ('Marubozu' in self.objects.keys()):
			print("Already calculated Marubozu Locations for " + self.ticker);
			
		self.objects['Marubozu'] = {};
		self.objects['Marubozu']['B'] = {};
		self.objects['Marubozu']['W'] = {};

		dayOpen = None;
		dayClose = None;
		dayHigh = None;
		dayLow = None;
		dayVolume = None;

		while(date != self.latestDate):
			#Grab all the information we need
			try:
				dayOpen = self.opens[date];
				dayClose = self.closes[date];
				dayHigh = self.highs[date];
				dayLow = self.lows[date];
			except KeyError:	#We need all this info, so missing any one piece means we skip the day (unfortunately)
				continue;

			#MARUBOZU IN TERMS OF PERCENTAGE?
			#-E.G. for Black Marubozu how close to the high does the open have to be for it to qualify?
			if (dayOpen == dayHigh and dayClose == dayLow):
				self.objects['Marubozu']['B'][dateStr] = True;
			elif (dayClose == dayHigh and dayOpen == dayLow):
				self.objects['Marubozu']['W'][dateStr] = True;

			date += pd.Timedelta('1 day');
			dateStr = str(date).split(' ')[0];



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
		fig, ax = plt.subplots();
		ax.plot(*zip(*self.closeList));

		fig.suptitle(self.ticker + " Closes");
		ax.set_xlabel("Date");
		ax.set_ylabel("Close Price");
		fig.autofmt_xdate();
		plt.show();



	def plotClosesCandlestickOHLC(self, startDate, endDate, maAndPeriod):
		"""
		Plots the closes for a stock as a Candlestick OHLC plot
		takes date, open, high, low, close, volume

		movingAverages is a list of strings ('SMA', 'EMA', etc) identifying which MAs we plot
		"""

		dayOpen = None;
		dayClose = None;
		dayHigh = None;
		dayLow = None;
		dayVolume = None;

		dohlcv = [];	#Date Open High Low Close Volume

		for date in self.opens.keys():
			datetime = pd.to_datetime(date);
			if (datetime < startDate or datetime > endDate):
				continue;
			try:
				dayDate = mdates.date2num(datetime);
				dayOpen = self.opens[date];
				dayClose = self.closes[date];
				dayHigh = self.highs[date];
				dayLow = self.lows[date];
				dayVolume = self.volumes[date];
			except KeyError:	#We need all this info, so missing any one piece means we skip the day (unfortunately)
				continue;

			#Some of these seem to be randomly missing...
			if (dayDate is None or dayOpen is None or dayClose is None or dayHigh is None or dayLow is None or dayVolume is None):
				continue;

			dohlcv.append([dayDate, dayOpen, dayHigh, dayLow, dayClose, dayVolume]);

		fig, ax = plt.subplots();
		candlestick_ohlc(ax, dohlcv, colorup='#77d879', colordown='#db3f3f');

		haveLabel = False;
		for ma in maAndPeriod.keys():
			p = maAndPeriod[ma];

			#Haven't run the calcution for this moving average at this period
			if (p not in self.calcsList[ma]):
				funcToCall = getattr(Stock, 'calculate' + ma);

				#HELLO ANONYMOUS FUNCTION CALL!
				funcToCall(self, period=p);

			#Prevent error if we try to plot a MA or period that doesn't exist
			try:
				newMasList = [entry for entry in self.calcsList[ma][p] if (entry[0] >= startDate and entry[0] <= endDate)];
				ax.plot(*zip(*newMasList), label=(ma + str(p)));
				haveLabel = True;
			except KeyError:
				print("BORKED!    " + str(ma) + " :: " + str(p));
				continue;

		ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'));
		ax.xaxis.set_major_locator(mticker.MaxNLocator(10));
		ax.grid(True);
		
		plt.xlabel('Date');
		plt.ylabel('Close');
		plt.title(self.ticker.upper() + " Closes from " + str(startDate).split(' ')[0] + " to " + str(endDate).split(' ')[0]);
		#Only add a legend if we have things that need a legend
		if (haveLabel):
			plt.legend();
		fig.autofmt_xdate();
		plt.show();




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

		for key in self.pe:
			keyDate = pd.to_datetime(key);
			if (keyDate < sDate or keyDate > eDate):
				continue;

			try:
				pe = self.pe[key];
				pbv = self.pbv[key];
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

