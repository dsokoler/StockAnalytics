#TODO:
#-DO RIGHT NOW:
# -PUSH TO GITHUB SO WE CAN ACCESS THIS AT HOME
#
#-Urgent:
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
# -Combine stock prices (Google Finance) with income/world development indicators (World Bank Group api) and currency values (Open Exchange Rates api)
#  -http://www.programmableweb.com/api/open-exchange-rates
#  -http://www.programmableweb.com/api/world-bank
# -Figure out how to use Bloomberg API with python (or build C program and integrate with python) (http://www.programmableweb.com/api/bloomberg)

#INSTALL GOOGLEFINANCE BEFORE RUNNING
import googlefinance, sys, getopt

optionsList = [""];
longOptionsList = ["stocks="];

def retrieveCurrentStocks(stocks):
	"""
	Retrive Google Finance information on a set of stocks
	stocks: a list of strings, each string is the ticker for a stock
	returns a dictionary where each key is a ticker and each value is the google finance information (in dictionary form) for that ticker
	"""
	stockData = dict.fromkeys(stocks);	#Is a dictionary {stock1:None, stock2:None, ...}

	quotes = googlefinance.getQuotes(stocks);	#GetQuotes returns a list of dictionaries (1 dict per stock specified)
	for quote in quotes:
		ticker = quote["StockSymbol"];
		stockData[ticker] = quote;

	#stockData now has the quotes from google finance as the values {stock1:Quotes, stock2:Quotes, ...}
	return stockData;



def retrieveHistoricalData(stocks):
	"""
	Uses YahooFinance to gather historical data on stock listings
	"""
	pass;



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

	stockData = retrieveCurrentStocks(stocks);



if __name__ == "__main__":
	try:
		main();
	except KeyboardInterrupt:
		exit();