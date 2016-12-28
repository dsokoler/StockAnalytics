
#TODO: finish retrieval in range methods
import sqlite3, sys, configparser

importError = False;

try:
	import pandas as pd
except ImportError:
	print("Database.py unable to find Pandas module");
	importError = True;

try:
	import requests
except ImportError:
	print("Database.py unable to find Requests module");
	importError = True;

if (importError):
	sys.exit();

class Database:

	#SQL Query to test if this stock's table exists
	testTableExistence = "SELECT name FROM sqlite_master WHERE type='table' AND name=?;"
	testTableExistence2 = "SELECT name FROM sqlite_master";

	#SQL Query to create a table for a certain stock
	#VULNERABLE TO SQL INJECTION ATM
	createStockTable = '''CREATE TABLE %s (Date text, Open real, Close real, High Real, Low Real, Volume integer, PE real, PBV real)'''
	
	#Insert into a stock table
	#VULNERABLE TO SQL INJECTION ATM
	insertQuery = '''INSERT INTO %s (Date, Open, Close, High, Low, Volume, PE, PBV) VALUES (?, ?, ?, ?, ?, ?, ?, ?)'''

	#Retrieve information needed to access Intrinio API
	config = configparser.ConfigParser();
	config.read("config.ini");
	username = config["INTRINIO"]["username"];
	password = config["INTRINIO"]["password"];

	keys = {
		'Opens': 'adj_open_price',
		'Closes': 'adj_close_price',
		'Highs': 'adj_high_price',
		'Lows': 'adj_low_price',
		'Volumes': 'adj_volume',
		"PE": "pricetoearnings",
		"PBV": "pricetobook"
	}

	genericHistoricURL = "https://api.intrinio.com/historical_data?identifier={0}&item={1}";

	#Dates must be in YYYY-MM-DD format
	addStartDateToURL = "&start_date={0}";
	addEndDateToURL = "&end_date={0}";

	def __init__(self, dbName):
		self.name = dbName + '.db';
		self.conn = sqlite3.connect(self.name + '.db');
		self.cursor = self.conn.cursor();



#--------------------------SQL Methods-----------------------------------------

	def hasTable(self, ticker):
		"""
		Check if a table already exists for this ticker
		"""

		self.cursor.execute(Database.testTableExistence, (ticker,));
		rows = self.cursor.fetchall();
		
		#Table already exists
		if (len(rows) == 1):
			return True;
		return False;



	def updateStockInformation(self, ticker):
		"""
		If this is the first call for this ticker, create a table for this stock
		Then update the stock's information

		Str  | Float| Float | Float|Float| Float  |Float| Float
		Date | Open | Close | High | Low | Volume | P/E | P/BV
		"""
		#if we have table, don't create it, just call retrival method
		startDate = None;
		endDate = str(pd.to_datetime('today')).split(' ')[0];

		#If we don't have a table, make it.
		if (not self.hasTable(ticker)):
			self.cursor.execute(Database.createStockTable % ticker);



		else:
			query = "SELECT MAX(Date) FROM %s" % ticker;
			self.cursor.execute(query);
			rows = self.cursor.fetchall();
			dateStr = rows[0][0];
			date = pd.to_datetime(dateStr);

			#No data to fill in, can't fill in for current day b/c won't have close yet
			if (date >= (pd.to_datetime('today') - pd.Timedelta('1 day'))):
				print("Table for %s is up to date" % ticker);
				return;

			startDate = dateStr;



		earliestDate, latestDate, data = self.retrieveInformation(ticker, startDate, None);

		for date in data['Opens'].keys():
			try:
				dayOpen = data['Opens'][date];
				dayClose = data['Closes'][date];
				dayHigh = data['Highs'][date];
				dayLow = data['Lows'][date];
				dayVolume = data['Volumes'][date];
				dayPE = data['PE'][date];
				dayPBV = data['PBV'][date];
			except KeyError:
				continue;

			self.cursor.execute(Database.insertQuery % ticker, (date, dayOpen, dayClose, dayHigh, dayLow, dayVolume, dayPE, dayPBV));

		self.conn.commit();




		

#----------------------------------Retrieval Methods----------------------------------

	def retrieveInformation(self, ticker, startDate, endDate):
		"""
		Retrieve the P/E and P/BV ratios for our stock
		"""
		keys = Database.keys;

		earliestDate = None;
		latestDate = None;

		data = {};

		#Get information from API
		for key in keys.keys():
			data[key] = {};

			apiUrl = Database.genericHistoricURL.format(ticker, keys[key]);
			if (startDate is not None):
				apiUrl += Database.addStartDateToURL.format(startDate);
			if (endDate is not None):
				apiUrl += Database.addEndDateToURL.format(endDate);

			r = requests.get(apiUrl, auth=(Database.username, Database.password));
			d = r.json();

			if (d["data"] == None):
				print("No data for " + ticker);
				return;

			for item in d["data"]:
				if (item["value"] == "nm"):
					continue;

				date = item["date"];
				value = item["value"];

				data[key][date] = value;

				date = pd.to_datetime(date);
				if (earliestDate is None or date < earliestDate):
					earliestDate = date;
				if (latestDate is None or date > latestDate):
					latestDate = date;

		return (earliestDate, latestDate, data);






	def printDB(self, ticker):
		query = "SELECT * FROM %s" % ticker;
		self.cursor.execute(query);
		rows = self.cursor.fetchall();
		print(rows);

if __name__ == "__main__":
	db = Database('test');

	db.cursor.execute('DELETE FROM GOOG WHERE Date >= "2016-12-01"');
	db.cursor.execute("SELECT MAX(Date) FROM GOOG")
	rows = db.cursor.fetchall()
	print(rows);

	db.updateStockInformation('GOOG');

	db.cursor.execute("SELECT MAX(Date) FROM GOOG")
	rows = db.cursor.fetchall()
	print(rows);


	#print("Database.py isn't made to be called directly!");
	sys.exit();


