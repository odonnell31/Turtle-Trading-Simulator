# -*- coding: utf-8 -*-
"""
Created on Sat Sep 12 18:26:49 2020

@author: ODsLaptop

Course: DATA604, Simulation and Modeling Techniques

Final Project: Turtle Trading Simulator, Michael O'Donnell, 7.16.20

Project Details: create a simulator that implements the famous "Turtle Trading"
strategy on any stock for any time frame and displays the results.
The rules of the "Turle Trading" strategy (the original Trend Trading strategy) are:
1. each trading unit is 1% of your total investment dollars
2. enter at a stock's 55-day high with 1 unit
3. add another unit if the stock climbs to .5N (N is the Average True Range)
4. exit if the stock dips below latest entry price minus N
"""

# For the end user, change the parameters below and run script:
stock = 'NFLX'              # choose your stock here
start_date = '2016-06-01'   # choose your initial investment date
end_date = '2020-09-01'      # choose your exit date
investment_dollars = 80000  # choose the total dollars to invest


# import libraries
"""
# yfinance library
try:
    import yfinance
except ImportError:
    !pip install yfinance

# yahoofinancials library
try:
    import yahoofinancials
except ImportError:
    !pip install yahoofinancials
"""
from modsim import *
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
from yahoofinancials import YahooFinancials


# function that will create a dataframe for a single stock
def create_stock_df(stock, start, end, SMA):
    
    # get the data from yahoo finance
    df = yf.download(stock, 
                     start=start, 
                     end=end, 
                     progress=False)
    
    # add extra columns for day, stock title,
    # simple moving average, and closing price average difference
    df['day'] = range(1, len(df) + 1)
    df['stock'] = stock
    df['SMA_x'] = df.iloc[:,4].rolling(window=SMA).mean()
    df['shifted_close'] = df['Close'].shift(1)
    df['close_difference'] = df['Close'] - df['shifted_close']
    
    # reset the index
    df = df.reset_index()
    
    # return the dataframe
    return df

# function to plot the stock dataframe's closing prices
def plot_stock_price(df):
    
    x = df['Date']
    y = df['Close']

    # plotting the points  
    plt.plot(x, y) 

    # naming the axes 
    plt.xlabel('date')
    plt.ylabel('price/share')

    # rotate the tick marks
    plt.xticks(rotation=70)

    # title
    plt.title('Stock Price over time') 

    # function to show the plot 
    plt.show()
    
    
# create a function that defines a state object
# for financial information that will change during simulation

# input your:
# 1. total dollars to invest
# 2. your entry signal in days
# 3. your exit signal (based on N, i.e. .5N)
def create_state_object(dollars, entry, exit):

    financial_state = State(dollars = dollars,
                           shares = 0,
                           total_value = dollars,
                           x_day_high = 0,
                           x_day_low = 0,
                           current_price = 0,
                           ATR = 0,
                           SMA_x = 0,
                           x = entry,
                           exit_x = exit,
                           status = 'out',
                           entry_price = 0,
                           exit_price = 0)
    
    return financial_state


# function that will create a system of parameters (that will not change during simulation)
def make_system(df, state, starting_dollars,
                unit_size, add_unit_signal):
    
    return System(t_0 = get_first_label(df),
                  t_end = get_last_label(df),
                  starting_dollars = starting_dollars,
                  unit_size = starting_dollars*unit_size,
                  add_unit_signal = add_unit_signal,
                  entry_signal = state.x,
                  exit_signal = state.exit_x,
                  stock = get_first_value(df['stock']),
                  financials = state)
    
    
# The update function takes the state during the current time step
# and returns the state during the next time step.
def update_func(df, state, t, system):

    d = state.dollars
    shares = state.shares
    #current_price = state.current_price
    x = state.x
    exit_x = state.exit_x
    status = state.status
    entry_price = state.entry_price
    exit_price = state.exit_price
    add_unit_signal = system.add_unit_signal
    
    if t <= x+2:
        
        xdh = max(df['Close'][1:x])
        xdl = min(df['Close'][1:x])
        sma_x = df['SMA_x'][t]
        atr = (xdh - xdl)/1.5
        current_price = df['Close'][t]
        
    if t > x+2:
        
        xdh = max(df['Close'][t-x:t+1])
        xdl = min(df['Close'][t-x:t+1])
        sma_x = df['SMA_x'][t]
        atr = (xdh - xdl)/1.5
        current_price = df['Close'][t]
        
        # if you see the entry signal and you're out
        if current_price >= xdh and status == 'out':
            
            entry_price = current_price
            shares = (system.unit_size)//(entry_price)
            d = d - ((system.unit_size)//(entry_price)) * entry_price
            status = 'in'
        
        # if you see the add unit signal and you're already in
        elif (status == 'in') and (current_price > (entry_price + (atr*add_unit_signal))) and (d > current_price):
            
            entry_price = current_price
            shares = shares + (system.unit_size)//(entry_price)
            d = d - ((system.unit_size)//(entry_price)) * entry_price
            status = 'in'
        
        # if you're in and you see the exit signal
        elif (current_price < (sma_x - (atr*exit_x))) and (status == 'in'):
            
            exit_price = current_price
            d = d + (shares * exit_price)
            shares = 0
            status = 'out'
        
        # you're just cruisin
        else:
            
            entry_price = entry_price
            exit_price = exit_price
            shares = shares
            d = d
        
    return State(dollars = d,
                 shares = shares,
                 total_value = d + (shares*current_price),
                 x_day_high = xdh,
                 x_day_low = xdl,
                 current_price = current_price,
                 ATR = atr,
                 SMA_x = sma_x,
                 x = x,
                 exit_x = exit_x,
                 status = status,
                 entry_price = entry_price,
                 exit_price = exit_price)
    

# define run simulation function that stores results in a TimeFrame
def run_simulation(df, system, update_func):
    
    # create a TimeFrame to keep track of financials over time
    frame = TimeFrame(columns = system.financials.index)
    frame.row[system.t_0] = system.financials
    
    # run the simluation for every day in the date range
    for t in linrange(system.t_0, system.t_end):
        frame.row[t+1] = update_func(df, frame.row[t], t, system)
        
    return frame


# function to plot the results
def plot_results(results, df):
    
    # call for four plots
    fig, axs = plt.subplots(2, 2, figsize = (14,9))

    # add a title to the figure
    fig.suptitle("Results of Simulation")

    # setup top left plot
    axs[0, 0].plot(results.index, results.dollars)
    axs[0, 0].set_title('dollars')
    axs[0, 0].grid(True, alpha = 0.5)

    # setup top right plot
    axs[0, 1].plot(results.index, results.shares)
    axs[0, 1].set_title('shares')
    axs[0, 1].grid(True, alpha = 0.5)

    # setup bottom left plot
    axs[1, 0].plot(results.index, results.total_value)
    axs[1, 0].set_title('total value')
    axs[1, 0].grid(True, alpha = 0.5)

    # setup bottom right plot
    axs[1, 1].plot(df['Date'], df['Close'])
    axs[1, 1].set_title('stock price')
    axs[1, 1].grid(True, alpha = 0.5)
    
    # rotate tick marks of final plot
    plt.xticks(rotation=45)
    plt.show()
    
    # print beginning and ending values
    print('')
    print("Stock:", df['stock'][0])
    print("initial investment date:", df['Date'][0])
    print("initial investment:", get_first_value(results.total_value))
    print("="*50)
    print("last date of investment:", df['Date'].iloc[-1])
    print("end date total investment value:", round(get_last_value(results.total_value), 2))
    print("="*50)
    print("return: $", round(get_last_value(results.total_value) - get_first_value(results.total_value), 2))
    

# finally, create a function for the end user that will take the parameters:
# 1. stock
# 2. date range
# 3. total investment dollars
# 4. entry signal
# 5. exit signal
# 6. unit size
# 7. add unit signal
# 8. simple moving average length

# and the function will run the functions
# 1. create_stock_df
# 2. create_state_object
# 3. make_system
# 4. run_simulation
# 5. plot_results

def trend_trader_simulator(stock = 'GOOG', start_date = '2014-01-01',
                           end_date = '2020-02-01', investment_dollars = 50000,
                           entry_signal = 55,
                           exit_signal = 1, unit_size = 0.1,
                           add_unit_signal = .5, update_function = update_func):
    
    # create stock dataframe
    TT_df = create_stock_df(stock, start_date, end_date, entry_signal)
    
    # create financial state object
    TT_financial_state = create_state_object(investment_dollars, entry_signal, exit_signal)
    
    # create system object
    TT_system = make_system(TT_df, TT_financial_state, investment_dollars,
                         unit_size, add_unit_signal)
    
    # run the simulation
    TT_results = run_simulation(TT_df, TT_system, update_function)
    
    # plot the results
    plot_results(results = TT_results, df = TT_df)
    

# function to test simulator on many stocks at once
def trend_trader_aggregater(stock = 'GOOG', start_date = '2014-01-01',
                           end_date = '2020-02-01', investment_dollars = 50000,
                           entry_signal = 55,
                           exit_signal = 1, unit_size = 0.1,
                           add_unit_signal = .5, update_function = update_func):
    
    # create stock dataframe
    TT_df = create_stock_df(stock, start_date, end_date, entry_signal)
    
    # create financial state object
    TT_financial_state = create_state_object(investment_dollars, entry_signal, exit_signal)
    
    # create system object
    TT_system = make_system(TT_df, TT_financial_state, investment_dollars,
                         unit_size, add_unit_signal)
    
    # run the simulation
    TT_results = run_simulation(TT_df, TT_system, update_function)
    
    # plot the results
    #plot_results(results = TT_results, df = TT_df)
    return round(get_last_value(TT_results.total_value), 2)

# uncomment below code to run on multiple stocks
"""
tech_stocks = ['XRX', 'NLOK', 'GOOG', 'STX', 'IT',
               'MSFT', 'DELL', 'ADBE', 'T', 'FB',
               'BABA', 'AAPL', 'INTC', 'WORK', 'CRM']

final_value = []

for t in tech_stocks:
    
    value = trend_trader_aggregater(stock = t,
                       start_date = '2015-01-01',
                       end_date = '2020-7-15',
                       investment_dollars = 10000,
                       update_function = update_func)
    
    final_value.append(value)
    
tech_stocks_df = pd.DataFrame({'Stock':tech_stocks,'Day':final_value})
#tech_stocks_df

plt.figsize = (14,9)


plt.bar(tech_stocks, final_value, color='blue')
plt.xlabel("Stock")
plt.ylabel("Final Value of Portfolio")
plt.title("Final Value after 5 Years")

plt.xticks(rotation=90)

plt.axhline(y=10000,linewidth=4, color='r')

plt.show()
"""

trend_trader_simulator(stock = stock,
                       start_date = start_date,
                       end_date = end_date,
                       investment_dollars = investment_dollars,
                       update_function = update_func)