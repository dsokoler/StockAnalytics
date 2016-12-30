
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
	createStockTable = '''CREATE TABLE %s (Date text PRIMARY KEY, Opens real, Closes real, Highs Real, Lows Real, Volumes integer, PE real, PBV real)'''
	
	#Insert into a stock table
	#VULNERABLE TO SQL INJECTION ATM
	insertQuery = '''INSERT OR IGNORE INTO %s (Date, Opens, Closes, Highs, Lows, Volumes, PE, PBV) VALUES (?, ?, ?, ?, ?, ?, ?, ?)'''

	dataPoints = ['Date', 'Opens', 'Closes', 'Highs', 'Lows', 'Volumes', 'PE', 'PBV']

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
		self.name = dbName;
		self.conn = sqlite3.connect(self.name + '.db');
		self.conn.row_factory = sqlite3.Row
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
			
			#Empty table, need to fill but not check dates on
			#SHOULD ONLY EVER BE ONE
			for row in rows:
				dateStr = rows[0][0];
				date = pd.to_datetime(dateStr);

				#No data to fill in, can't fill in for current day b/c won't have close yet
				if (date >= (pd.to_datetime('today') - pd.Timedelta('1 day'))):
					print("Table for %s is up to date" % ticker);
					return;

				startDate = dateStr;



		data = self.retrieveInformationFromAPI(ticker, startDate, None);

		dayOpen = None;
		dayClose = None;
		dayHigh = None;
		dayLow = None
		dayVolume = None
		dayPE = 0;
		dayPBV = 0;
		for date in data['Opens'].keys():
			try:
				dayOpen = data['Opens'][date];
				dayClose = data['Closes'][date];
				dayHigh = data['Highs'][date];
				dayLow = data['Lows'][date];
				dayVolume = data['Volumes'][date];
			except KeyError:
				continue;

			try:
				dayPE = data['PE'][date];
				dayPBV = data['PBV'][date];
			except KeyError:
				dayPE = 0;
				dayPBV = 0;

			self.cursor.execute(Database.insertQuery % ticker, (date, dayOpen, dayClose, dayHigh, dayLow, dayVolume, dayPE, dayPBV));

		self.conn.commit();



	def retrieveAllInformationForStock(self, ticker):
		"""
		Pull all information for a particular stock

		returns a dictionary: {'Opens': {Dict: {Date: Open}, List: [Date, Open]}}
		"""

		#Column names in our database
		columnNames = Database.keys.keys();

		#Set up the structure to hold our data
		data = {}
		data['Dict'] = {};
		data['List'] = {};
		for name in columnNames:
			data['Dict'][name] = {};
			data['List'][name] = []

		query = "SELECT Date, Opens, Closes, Highs, Lows, Volumes, PE, PBV FROM %s" % ticker;
		self.cursor.execute(query);

		earliestDate = None;
		latestDate = None;

		#Date, Open, Close, High, Low, Volume, PE, PBV
		for row in self.cursor.fetchall():
			rowKeys = row.keys()
			date = row[rowKeys[0]];

			#Determine if this date is earlier/later than the previous ones
			datetime = pd.to_datetime(date);
			if (earliestDate is None or datetime < earliestDate):
				earliestDate = datetime;
			if (latestDate is None or datetime > latestDate):
				latestDate = datetime;

			for key in rowKeys[1:]:
				data['Dict'][key][date] = row[key];
				data['List'][key].append( [ date, row[key] ] );

		return (earliestDate, latestDate, data);



	def isCalculated(self, ticker, calcName, calcPeriod):
		queryGetColNames = "PRAGMA table_info(%s)" % ticker;
		self.cursor.execute(queryGetColNames);

		columnName = None;
		if (calcPeriod is None):
			columnName = calcName;
		else:
			columnName = calcName + str(calcPeriod);
		
		hasColumnForCalc = False;
		for row in self.cursor.fetchall():
			if (row[1] in self.dataPoints):
				continue;
			elif(row[1] == columnName):
				hasColumnForCalc = True;
				break

		return hasColumnForCalc;




	def addCalculation(self, ticker, maName, maPeriod, maList):
		"""
		Adds the list of moving average calculations to the appropriate table
		Ticker: the stock ticker to add the information to
		maName: the name of the moving average (e.g. 'KAMA', 'TMA', etc)
		maList: a list of [Date, MA] to store
		"""

		queryGetColNames = "PRAGMA table_info(%s)" % ticker;
		self.cursor.execute(queryGetColNames);

		columnName = None;
		if (maPeriod is None):
			columnName = maName;
		else:
			columnName = maName + str(maPeriod);
		
		hasColumnForMA = False;
		for row in self.cursor.fetchall():
			if (row[1] == columnName):
				hasColumnForMA = True;
				break;

		#If we don't have a column for this Moving Average, make one. No need to store extra data we don't need
		#Column name is the moving average abbreviation (e.g. 'KAMA', 'SMA') with its period appended on the end
		if (not hasColumnForMA):
			addColQuery = "ALTER TABLE {0} ADD COLUMN {1} {2}".format(ticker, columnName, 'real');
			self.cursor.execute(addColQuery);

		query = "UPDATE {0} SET {1}=? WHERE Date = '%s'".format(ticker, columnName);
		for calc in maList:
			dateStr = str(calc[0]).split(' ')[0];
			self.cursor.execute(query % dateStr, (calc[1],));

		self.conn.commit();



	def retrieveCalculation(self, ticker, maName, maPeriod, startDate, endDate):
		"""
		Retrieve information for the moving average (for the specific period)
		StartDate and EndDate MUST be strings

		Interestingly, we can get this method down to two lines
		"""
		queryGetColNames = "PRAGMA table_info(%s)" % ticker;
		self.cursor.execute(queryGetColNames);

		columnName = None;
		if (maPeriod is None):
			columnName = maName;
		else:
			columnName = maName + str(maPeriod);
		
		match = False;
		for row in self.cursor.fetchall():
			if (columnName == row[1]):
				match = True;
				break;

		if (not match):
			return None;

		sd = str(startDate).split(' ')[0];
		ed = str(endDate).split(' ')[0];
		query = "SELECT Date, ? FROM %s WHERE Date >= ? and Date <= ?";
		self.cursor.execute( query % ticker, (columnName, sd, ed) );

		cdict = {};
		clist = [];
		for row in self.cursor.fetchall():
			cdict[row[0]] = row[1];
			clist.append( [row[0], row[1]] );
		
		return (cdict, clist);



		

#----------------------------------Retrieval Methods----------------------------------

	def retrieveInformationFromAPI(self, ticker, startDate, endDate):
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

		return data;






	def printDB(self, ticker):
		colNames = [];
		queryGetColNames = "PRAGMA table_info(%s)" % ticker;
		self.cursor.execute(queryGetColNames);
		
		for row in self.cursor.fetchall():
			colNames.append(row[1]);

		print(' '.join(colNames));

		query = "SELECT * FROM %s ORDER BY Date ASC" % ticker;
		self.cursor.execute(query);
		rows = self.cursor.fetchall();
		for row in rows:
			for item in row:
				print(str(item) + ' ', end='')
			print();

if __name__ == "__main__":
	print("Database.py isn't made to be called directly!");
	sys.exit();












