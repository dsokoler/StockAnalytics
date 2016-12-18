#TODO:
#-DO RIGHT NOW:
#
#-Urgent:
# -Convert this entire program to C, its finance and should be fast
# -Use Yahoo Finance API (or some other API) to retrive historical data for stocks
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

#INSTALL GOOGLEFINANCE BEFORE RUNNING
import googlefinance, sys, getopt
from yahoo_finance import Share

optionsList = [""];
longOptionsList = ["stocks="];

googleFinanceFullNames = [
	u'ID',
	u'StockSymbol',
	u'Index',
	u'LastTradePrice',
	u'LastTradeWithCurrency',
	u'LastTradeTime',
	u'LastTradeDateTime',
	u'LastTradeDateTimeLong',
	u'Dividend',
	u'Yield',
	u'LastTradeSize',
	u'Change',
	u'ChangePercent',
	u'ExtHrsLastTradePrice',
	u'ExtHrsLastTradeWithCurrency',
	u'ExtHrsLastTradeDateTimeLong',
	u'ExtHrsChange',
	u'ExtHrsChangePercent',
	u'PreviousClosePrice'
]

googleFinanceKeyToFullName = {
    u'id'     : u'ID',
    u't'      : u'StockSymbol',
    u'e'      : u'Index',
    u'l'      : u'LastTradePrice',
    u'l_cur'  : u'LastTradeWithCurrency',
    u'ltt'    : u'LastTradeTime',
    u'lt_dts' : u'LastTradeDateTime',
    u'lt'     : u'LastTradeDateTimeLong',
    u'div'    : u'Dividend',
    u'yld'    : u'Yield',
    u's'      : u'LastTradeSize',
    u'c'      : u'Change',
    u'c'      : u'ChangePercent',
    u'el'     : u'ExtHrsLastTradePrice',
    u'el_cur' : u'ExtHrsLastTradeWithCurrency',
    u'elt'    : u'ExtHrsLastTradeDateTimeLong',
    u'ec'     : u'ExtHrsChange',
    u'ecp'    : u'ExtHrsChangePercent',
    u'pcls_fix': u'PreviousClosePrice'
}

#Get keys by doing googleFinanceKeyToFullName.keys().  Won't be ordered



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