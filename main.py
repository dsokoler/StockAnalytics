#TODO:
#-DO RIGHT NOW:
# -Check if we already have calculations in DB
# -Convert mass calculate methods to individual day ones that go inside the while(date..) loop
# -Verify methods work: calculateTMA, calculateSlopeMA, calculateEMA (double/triple), identifyLongCandles, identifyDoji, identifyMarubozu
#
#-Urgent:
# -Make a 'Moving Average' class/object that we can include in Stock
#  -Type ('SMA', 'TMA'), calculation (method that does the calculation), period, (and any other info)
# -Add an 'updateCurrentDayInfo' method that grabs the most up to date info for 'today'
# -Make pd.Timedelta('1 day') a variable of the Stock class so we don't have to continually make it
# -Check in our SMA/EMA calculations if try/except is faster than if/else
# -Add overbought/oversold indicators (when we get to the analysis phase)
# -Research types of stock analysis (http://www.investopedia.com)
#
#-Less Urgent:
# -Change calculate methods to return dicts/lists instead of doing the assignation inside those methods
# -Build a treemap for visualization of data (see https://i.redd.it/b0viuwrmo85x.png)
#  -Smallest: single stock, represented by ticker.
#  -Size of square is represented by the Market Cap of that stock
#  -Color of the square is represented by the change in stock price (changable 1d, 1w, 1m, 6m, 1y, 5y)
#
#-Not Urgent:
# -Combine stock prices (Google Finance) with income/world development indicators (World Bank Group api or Yahoo Finance) and currency values (Open Exchange Rates api)
#  -http://www.programmableweb.com/api/open-exchange-rates
#  -http://www.programmableweb.com/api/world-bank
# -Figure out how to use Bloomberg API with python (or build C program and integrate with python) (http://www.programmableweb.com/api/bloomberg)
# -Find info on stock performance by market (tech, clothing, finance, etc) and built that into the analytics of stocks

#Nasdaq pre-market trading hours: 4:00am to 9:30am (http://www.investopedia.com/terms/p/premarket.asp)
#		market hours from 9:30am to 4:00pm
#		after-market hours from 4:00pm to 8:00pm (http://www.investopedia.com/terms/a/afterhourstrading.asp)

import sys, getopt, json

importError = False;
try:
	import googlefinance
except ImportError:
	print("Please install googlefinance : 'pip install googlefinance'");
	importError = True;

#For help see https://github.com/lukaszbanasiak/yahoo-finance
try:
	from yahoo_finance import Share
except ImportError:
	print("Please install yahoo-finance : 'pip install yahoo-finance'");
	importError = True;

try:
    from urllib.request import Request, urlopen
except ImportError:
	print("Please install urllib : 'pip install urllib'");
	importError = True;

try:
	from Stock import Stock
except ImportError:
	print("Unable to find the Stock module");
	importError = True;

#Pandas is for datetimes
try:
	import pandas as pd
except ImportError:
	print("Please install Pandas");
	importError = True;

if (importError):
	sys.exit();




googleFinanceKeyToFullName = {
#Abbreviation  : Full Name
	u'id'      : u'ID',
	u't'       : u'StockSymbol',
	u'e'       : u'Index',
	u'l'       : u'LastTradePrice',
	u'l_cur'   : u'LastTradeWithCurrency',
	u'l_fix'   : u'',
	u's'       : u'LastTradeSize',
	u'ltt'     : u'LastTradeTime',
	u'lt'      : u'LastTradeDateTimeLong',
	u'lt_dts'  : u'LastTradeDateTime',
	u'c'       : u'Change',
#	u'div'     : u'Dividend',
#	u'yld'     : u'Yield',
	u'c_fix'   : u'',
	u'cp'       : u'ChangePercent',
	u'cp_fix'  : u'',
	u'ccol'    : u'',
	u'pcls_fix': u'PreviousClosePrice',
	u'eo'      : u'',
	u'delay'   : u'',
	u'op'      : u'',
	u'hi'      : u'',
	u'lo'      : u'',
	u'vo'      : u'',
	u'avvo'    : u'',
	u'hi52'    : u'52WeekHigh',
	u'lo52'    : u'52WeekLow',
	u'mc'      : u'',
	u'pe'      : u'',
	u'fwpe'    : u'',
	u'beta'    : u'',
	u'eps'     : u'',
	u'shares'  : u'TotalSharesOnMarket',
#	u'inst_own': u'',
	u'name'    : u'StockFullName',
	u'type'    : u''
#	u'el'      : u'ExtHrsLastTradePrice',
#	u'el_cur'  : u'ExtHrsLastTradeWithCurrency',
#	u'elt'     : u'ExtHrsLastTradeDateTimeLong',
#	u'ec'      : u'ExtHrsChange',
#	u'ecp'     : u'ExtHrsChangePercent'
}

googleFinanceKeys = googleFinanceKeyToFullName.keys();

googleFinanceURL = "http://www.google.com/finance/info?infotype=infoquoteall&q="; #Add 'MARKET:TICKER' at the end



def retrieveCurrentStockData(market, stocks):
	"""
	Retrive Google Finance information on a set of stocks using the googlefinance module
	stocks: a list of strings, each string is the ticker for a stock
	returns a dictionary where each key is a ticker and each value is the google finance information (in dictionary form) for that ticker
	"""
	
	#This line is the same as the three below it
	#return {quote["StockSymbol"]:quote for quote in googlefinance.getQuotes(stocks)};

	quotes = googlefinance.getQuotes(stocks);	#GetQuotes returns a list of dictionaries (1 dict per stock specified)
	stockData = {quote["StockSymbol"]:quote for quote in quotes};

	#stockData now has the quotes from google finance as the values {stock1:Quote, stock2:Quote, ...}
	return stockData;

def retrieveCurrentStockData2(market, stocks):
	"""
	Retrieve Google Finance informatin on a set of stocks using urllib
	returns a dictionary where each key is a ticker and each value is the google finance information (in dictionary form) for that ticker
	"""

	global googleFinanceURL;
	stockData = dict.fromkeys(stocks);

	for stock in stocks:
		#print("Retrieving for " + googleFinanceURL + market + ':' + stock)
		
		try:
			r = Request(googleFinanceURL + market + ':' + stock);
			response = urlopen(r)
		except urllib.error.HTTPError:
			print("HTTPError");
			return None;

		content = response.read().decode('ascii', 'ignore').strip();
		content = content[3:];

		stockInfo = json.loads(content);
		stockData[stock] = stockInfo[0];

	return stockData;



def retrieveHistoricalStockData(market, stocks):
	"""
	Uses YahooFinance to gather historical data on stock listings
	"""
	return {stock:Share(stock) for stock in stocks};


optionsList = [""];
longOptionsList = ["stocks=", "market=", "limit=", "startDate=", 
					"endDate=", "outlier=", "removeOutliers", 
					"period=", "database="];
def main():

	"""
	Main method, handles argument validation
	"""

	try:
		opts, args = getopt.getopt(sys.argv[1:], optionsList, longOptionsList);
	except getopt.GetoptError as err:
		print(err);
		sys.exit();

	market = None;
	stocks = [];
	limit = 22.5;
	startDate = None;
	endDate = None;
	outlier = 1;
	removeOutliers = False;
	period = 26;		#Length of time for averages and indicators (in days)
	database = "default";
	listTables = False;

	for opt, arg in opts:
		if (opt == "--market"):
			market = arg;
		
		elif (opt == "--stocks"):
			stocks = arg.replace(', ', ',').split(',');

		elif (opt == "--limit"):
			try:
				limit = int(arg);
			except ValueError:
				print("Limit should be an integer.  Defaulting to 22.5")
		
		elif (opt == "--startDate"):
			try:
				startDate = pd.to_datetime(arg);
			except Exception as valueError:
				print("Invalid --startDate option: " + arg);
				print(str(valueError));
		
		elif (opt == "--endDate"):
			try:
				endDate = pd.to_datetime(arg);
			except Exception as valueError:
				print("Invalid --endDate option: " + arg);
				print(str(valueError));

		#A number is considered an outlier if it is more than X std deviations away from the mean
		elif(opt == "--outlier"):
			try:
				outlier = int(arg)
			except ValueError:
				print("Outlier specification should be an integer, defaulting to 1");

		elif (opt == "--removeOutliers"):
			removeOutliers = True;

		elif (opt == "--period"):
			try:
				period = int(arg);
			except ValueError:
				print("The 'Period' option should be an integer, defaulting to 26");

			periodDatetime = pd.Timedelta(arg + ' days');
			endDate = pd.to_datetime('today');
			startDate = endDate - periodDatetime;

		#If this is not specified we default to "default.db"
		elif (opt == "--database"):
			database = arg;

	#empty lists identify as false
	if (not stocks):
		print("Please specify one or more stocks");
		sys.exit();

	#
	if (market is None):
		print("Please specify the market you wish to retrieve data from");
		sys.exit();

	#
	#currentStockData = retrieveCurrentStockData2(market, stocks);
	#historicalStockData = retrieveHistoricalStockData(market, stocks);

	periodsToPlot2 = None;

	masToPlot = {
		#'KAMA': 10,
		#'EMA': 12
	}

	#Build an array of our Stock objects
	stockObjects = [Stock(stock, startDate, endDate, limit, periodsToPlot2, database) for stock in stocks];
	for stock in stockObjects:
		stock.plotClosesCandlestickOHLC(stock.startDate, stock.endDate, masToPlot);






if __name__ == "__main__":
	try:
		main();
	except KeyboardInterrupt:
		exit();
