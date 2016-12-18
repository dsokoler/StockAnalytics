#TODO:
#-DO RIGHT NOW:
#
#-Urgent:
# -Research types of stock analysis (http://www.investopedia.com)
# -Read through quantarisk.com for good blog posts
# -Change over from using googlefinance module to getting posts manually (see quantarisk blog post on retrieving info from google finance)
#
#-Less Urgent:
# -Build an sqlite db to store this information so we don't have to go get it repeatedly
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

#INSTALL GOOGLEFINANCE BEFORE RUNNING
import sys, getopt

importError = False;
try:
	import googlefinance
except ImportError:
	print("Please install googlefinance : 'pip install googlefinance'");
	importError = True;

try:
	from yahoo_finance import Share
except ImportError:
	print("Please install yahoo-finance : 'pip install yahoo-finance'");
	importError = True;

if (importError):
	sys.exit();



optionsList = [""];
longOptionsList = ["stocks="];

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
	u'div'     : u'Dividend',
	u'yld'     : u'Yield',
	u'c'       : u'ChangePercent',
	u'c_fix'   : u'';
	u'cp'      : u'',
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
	u'hi52'    : u'',
	u'lo52'    : u'',
	u'mc'      : u'',
	u'pe'      : u'',
	u'fwpe'    : u'',
	u'beta'    : u'',
	u'eps'     : u'',
	u'shares'  : u'TotalSharesOnMarket',
	u'inst_own': u'',
	u'name'    : u'',
	u'type'    : u'',
	u'el'      : u'ExtHrsLastTradePrice',
	u'el_cur'  : u'ExtHrsLastTradeWithCurrency',
	u'elt'     : u'ExtHrsLastTradeDateTimeLong',
	u'ec'      : u'ExtHrsChange',
	u'ecp'     : u'ExtHrsChangePercent',
}

googleFinanceKeys = googleFinanceKeyToFullName.keys();



def retrieveCurrentStockData(stocks):
	"""
	Retrive Google Finance information on a set of stocks
	stocks: a list of strings, each string is the ticker for a stock
	returns a dictionary where each key is a ticker and each value is the google finance information (in dictionary form) for that ticker
	"""
	
	#This line is the same as the three below it
	#return {quote["StockSymbol"]:quote for quote in googlefinance.getQuotes(stocks)};

	quotes = googlefinance.getQuotes(stocks);	#GetQuotes returns a list of dictionaries (1 dict per stock specified)
	stockData = {quote["StockSymbol"]:quote for quote in quotes};

	#stockData now has the quotes from google finance as the values {stock1:Quote, stock2:Quote, ...}
	return stockData;



def retrieveHistoricalStockData(stocks):
	"""
	Uses YahooFinance to gather historical data on stock listings
	"""
	return {stock:Share(stock) for stock in stocks};


def main():

	"""
	Main method, handles argument validation
	"""

	try:
		opts, args = getopt.getopt(sys.argv[1:], optionsList, longOptionsList);
	except getopt.GetoptError as err:
		print(err);
		sys.exit();

	stocks = [];
	for opt, arg in opts:
		if (opt == "--stocks"):
			stocks = arg.replace(', ', ',').split(',');

	#empty lists identify as false
	if (not stocks):
		print("Please specify one or more stocks");
		sys.exit();

	#
	currentStockData = retrieveCurrentStockData(stocks);
	print(str(currentStockData));

	print();

	historicalStockData = retrieveHistoricalStockData(stocks);
	print(str(historicalStockData));



if __name__ == "__main__":
	try:
		main();
	except KeyboardInterrupt:
		exit();