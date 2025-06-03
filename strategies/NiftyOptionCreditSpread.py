import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
import logging
import traceback
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress specific pandas warnings
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=pd.errors.SettingWithCopyWarning)

class NiftyOptionCreditSpread:
    def __init__(self):
        self.name = "Nifty Option Credit Spread"
        self.timeframe = "1H"
        self.symbol = "NIFTY"
        logger.info(f"Initialized {self.name} strategy")
        
    def calculate_ema(self, data, period=20):
        """Calculate Exponential Moving Average (EMA)
        
        Args:
            data (pd.Series): Price data series
            period (int): EMA period
            
        Returns:
            pd.Series: EMA values
        """
        try:
            multiplier = 2 / (period + 1)
            ema = pd.Series(index=data.index, dtype=float)
            ema.iloc[period-1] = data.iloc[:period].mean()
            
            for i in range(period, len(data)):
                ema.iloc[i] = (data.iloc[i] - ema.iloc[i-1]) * multiplier + ema.iloc[i-1]
            
            logger.debug(f"Calculated EMA with period {period}")
            return ema
        except Exception as e:
            logger.error(f"Error calculating EMA: {str(e)}")
            logger.error("Stack trace:", exc_info=True)
            raise

    def calculate_supertrend(self, df, period=10, multiplier=3.5):
        """Calculate SuperTrend indicator"""
        try:
            high = df['high']
            low = df['low']
            close = df['close']
            
            # Calculate ATR
            tr1 = pd.DataFrame(high - low)
            tr2 = pd.DataFrame(abs(high - close.shift(1)))
            tr3 = pd.DataFrame(abs(low - close.shift(1)))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(period).mean()
            
            # Calculate SuperTrend
            hl2 = (high + low) / 2
            upperband = hl2 + (multiplier * atr)
            lowerband = hl2 - (multiplier * atr)
            
            supertrend = pd.Series(index=df.index, dtype=float)
            direction = pd.Series(index=df.index, dtype=int)
            
            # Use iloc for positional indexing
            for i in range(period, len(df)):
                if close.iloc[i] > upperband.iloc[i-1]:
                    supertrend.iloc[i] = lowerband.iloc[i]
                    direction.iloc[i] = 1
                elif close.iloc[i] < lowerband.iloc[i-1]:
                    supertrend.iloc[i] = upperband.iloc[i]
                    direction.iloc[i] = -1
                else:
                    supertrend.iloc[i] = supertrend.iloc[i-1]
                    direction.iloc[i] = direction.iloc[i-1]
                    
                    if supertrend.iloc[i] == upperband.iloc[i-1] and close.iloc[i] > upperband.iloc[i]:
                        supertrend.iloc[i] = lowerband.iloc[i]
                        direction.iloc[i] = 1
                    elif supertrend.iloc[i] == lowerband.iloc[i-1] and close.iloc[i] < lowerband.iloc[i]:
                        supertrend.iloc[i] = upperband.iloc[i]
                        direction.iloc[i] = -1
            
            logger.debug(f"Calculated SuperTrend with period {period} and multiplier {multiplier}")
            return supertrend, direction
        except Exception as e:
            logger.error(f"Error calculating SuperTrend: {str(e)}")
            logger.error("Stack trace:", exc_info=True)
            raise

    def get_expiry_date(self, current_date):
        """Get the expiry date based on the day of the week
        - If order is placed on Monday, Tuesday, or Wednesday: Next week's Thursday
        - If order is placed on Thursday or Friday: Next Thursday
        """
        try:
            current_date = pd.Timestamp(current_date)
            current_weekday = current_date.weekday()  # 0=Monday, 1=Tuesday, ..., 4=Friday
            
            # Calculate days until next Thursday
            days_until_thursday = (3 - current_weekday) % 7  # 3 represents Thursday
            
            if current_weekday <= 2:  # Monday, Tuesday, or Wednesday
                # Get next week's Thursday
                expiry_date = current_date + pd.Timedelta(days=days_until_thursday + 7)
            else:  # Thursday or Friday
                # Get next Thursday
                expiry_date = current_date + pd.Timedelta(days=days_until_thursday)
            
            logger.info(f"Calculated expiry date: {expiry_date.strftime('%Y-%m-%d')}")
            return expiry_date
        except Exception as e:
            logger.error(f"Error calculating expiry date: {str(e)}")
            logger.error("Stack trace:", exc_info=True)
            raise

    def generate_signals(self, df):
        """Generate trading signals based on the strategy rules"""
        try:
            # Create a copy of the dataframe to avoid chained assignment
            df = df.copy()
            
            # Calculate indicators
            df['ema20'] = self.calculate_ema(df['close'], period=20)
            _, df['supertrend_direction'] = self.calculate_supertrend(df)
            
            # Initialize signals column
            df['signal'] = 0
            
            # Create a mask for long and short conditions
            long_condition = (df['close'] > df['ema20']) & (df['supertrend_direction'] == 1)
            short_condition = (df['close'] < df['ema20']) & (df['supertrend_direction'] == -1)
            
            # Apply signals using loc
            df.loc[long_condition, 'signal'] = 1
            df.loc[short_condition, 'signal'] = -1
            
            logger.info(f"Generated signals. Long signals: {long_condition.sum()}, Short signals: {short_condition.sum()}")
            return df
        except Exception as e:
            logger.error(f"Error generating signals: {str(e)}")
            logger.error("Stack trace:", exc_info=True)
            raise

    def calculate_option_strikes(self, spot_price, signal):
        """Calculate option strikes for credit spread"""
        try:
            # Round spot price to nearest 50
            base_strike = round(spot_price / 50) * 50
            
            if signal == 1:  # Long Credit Spread
                # Buy higher strike put, sell lower strike put
                buy_strike = base_strike + 400  # D+400
                sell_strike = base_strike + 250  # D+250
                option_type = 'put'
            else:  # Short Credit Spread
                # Buy lower strike call, sell higher strike call
                buy_strike = base_strike - 250  # D-250
                sell_strike = base_strike - 400  # D-400
                option_type = 'call'
            
            logger.info(f"Calculated option strikes - Type: {option_type}, Buy: {buy_strike}, Sell: {sell_strike}")
            return {
                'buy_strike': buy_strike,
                'sell_strike': sell_strike,
                'type': option_type
            }
        except Exception as e:
            logger.error(f"Error calculating option strikes: {str(e)}")
            logger.error("Stack trace:", exc_info=True)
            raise

    def execute_strategy(self, data):
        """Execute the complete strategy"""
        try:
            # Convert data to DataFrame if not already
            if not isinstance(data, pd.DataFrame):
                df = pd.DataFrame(data)
            else:
                df = data.copy()
            
            # Generate signals
            df = self.generate_signals(df)
            
            # Get current expiry date
            current_date = pd.Timestamp.now()
            expiry_date = self.get_expiry_date(current_date)
            
            # Get latest signal
            latest_signal = df['signal'].iloc[-1]
            
            if latest_signal != 0:
                # Calculate option strikes
                spot_price = df['close'].iloc[-1]
                option_strikes = self.calculate_option_strikes(spot_price, latest_signal)
                
                result = {
                    'signal': latest_signal,
                    'spot_price': spot_price,
                    'expiry_date': expiry_date,
                    'option_strikes': option_strikes,
                    'timestamp': df.index[-1]
                }
                
                logger.info(f"Strategy execution completed - Signal: {latest_signal}")
                return result
            
            logger.info("No trading signal generated")
            return None
        except Exception as e:
            logger.error(f"Error executing strategy: {str(e)}")
            logger.error("Stack trace:", exc_info=True)
            raise

    def get_strategy_info(self):
        """Return strategy information"""
        return {
            'name': self.name,
            'timeframe': self.timeframe,
            'symbol': self.symbol,
            'description': """
            Nifty Option Credit Spread Strategy:
            1. Timeframe: 1 Hour
            2. Expiry: Next's week Thursday if order is placed on monday, tuesday, wednesday
            otherwise next thursday if order is placed on thursday, friday
            3. Long Entry Conditions:
               - EMA(20) Close above
               - SuperTrend = Green (10-3.5)
               - Credit Spread: Buy D+400 Put, Sell D+250 Put
            4. Short Entry Conditions:
               - EMA Below (20)
               - SuperTrend = Red (10-3.5)
               - Credit Spread: Buy D-250 Call, Sell D-400 Call
            """
        }
