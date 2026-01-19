"""
Stock Metadata Update Script
Enhance stock_tickers.csv with sector, market cap, and ETF data

Author: Harsh Kandhway
Date: January 19, 2026
"""

import pandas as pd
import logging
from pathlib import Path
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# NSE Sector Classifications (Simplified - will expand based on actual stock data)
SECTOR_MAP = {
    # Large Cap IT
    'TCS.NS': {'sector': 'Information Technology', 'sub_sector': 'IT Services'},
    'INFY.NS': {'sector': 'Information Technology', 'sub_sector': 'IT Services'},
    'HCLTECH.NS': {'sector': 'Information Technology', 'sub_sector': 'IT Services'},
    'WIPRO.NS': {'sector': 'Information Technology', 'sub_sector': 'IT Services'},
    'TECHM.NS': {'sector': 'Information Technology', 'sub_sector': 'IT Services'},
    'LTIM.NS': {'sector': 'Information Technology', 'sub_sector': 'IT Services'},
    'COFORGE.NS': {'sector': 'Information Technology', 'sub_sector': 'IT Services'},
    
    # Large Cap Banks
    'HDFCBANK.NS': {'sector': 'Financial Services', 'sub_sector': 'Private Banks'},
    'ICICIBANK.NS': {'sector': 'Financial Services', 'sub_sector': 'Private Banks'},
    'AXISBANK.NS': {'sector': 'Financial Services', 'sub_sector': 'Private Banks'},
    'KOTAKBANK.NS': {'sector': 'Financial Services', 'sub_sector': 'Private Banks'},
    'SBIN.NS': {'sector': 'Financial Services', 'sub_sector': 'Public Banks'},
    'BANKBARODA.NS': {'sector': 'Financial Services', 'sub_sector': 'Public Banks'},
    'PNB.NS': {'sector': 'Financial Services', 'sub_sector': 'Public Banks'},
    
    # Large Cap Oil & Gas
    'RELIANCE.NS': {'sector': 'Oil & Gas', 'sub_sector': 'Refining & Marketing'},
    'ONGC.NS': {'sector': 'Oil & Gas', 'sub_sector': 'Exploration & Production'},
    'BPCL.NS': {'sector': 'Oil & Gas', 'sub_sector': 'Refining & Marketing'},
    'IOC.NS': {'sector': 'Oil & Gas', 'sub_sector': 'Refining & Marketing'},
    'GAIL.NS': {'sector': 'Oil & Gas', 'sub_sector': 'Gas Distribution'},
    
    # Large Cap Consumer
    'HINDUNILVR.NS': {'sector': 'Consumer Goods', 'sub_sector': 'FMCG'},
    'ITC.NS': {'sector': 'Consumer Goods', 'sub_sector': 'FMCG'},
    'NESTLEIND.NS': {'sector': 'Consumer Goods', 'sub_sector': 'FMCG'},
    'BRITANNIA.NS': {'sector': 'Consumer Goods', 'sub_sector': 'FMCG'},
    'DABUR.NS': {'sector': 'Consumer Goods', 'sub_sector': 'FMCG'},
    'MARICO.NS': {'sector': 'Consumer Goods', 'sub_sector': 'FMCG'},
    'TITAN.NS': {'sector': 'Consumer Goods', 'sub_sector': 'Jewelry & Watches'},
    
    # Large Cap Pharma
    'SUNPHARMA.NS': {'sector': 'Healthcare', 'sub_sector': 'Pharmaceuticals'},
    'DRREDDY.NS': {'sector': 'Healthcare', 'sub_sector': 'Pharmaceuticals'},
    'CIPLA.NS': {'sector': 'Healthcare', 'sub_sector': 'Pharmaceuticals'},
    'DIVISLAB.NS': {'sector': 'Healthcare', 'sub_sector': 'Pharmaceuticals'},
    'APOLLOHOSP.NS': {'sector': 'Healthcare', 'sub_sector': 'Hospitals'},
    
    # Large Cap Auto
    'MARUTI.NS': {'sector': 'Automobile', 'sub_sector': 'Passenger Vehicles'},
    'TATAMOTORS.NS': {'sector': 'Automobile', 'sub_sector': 'Commercial Vehicles'},
    'M&M.NS': {'sector': 'Automobile', 'sub_sector': 'Passenger Vehicles'},
    'BAJAJ-AUTO.NS': {'sector': 'Automobile', 'sub_sector': 'Two Wheelers'},
    'EICHERMOT.NS': {'sector': 'Automobile', 'sub_sector': 'Two Wheelers'},
    'HEROMOTOCO.NS': {'sector': 'Automobile', 'sub_sector': 'Two Wheelers'},
    
    # Large Cap Metals
    'TATASTEEL.NS': {'sector': 'Metals & Mining', 'sub_sector': 'Steel'},
    'JSWSTEEL.NS': {'sector': 'Metals & Mining', 'sub_sector': 'Steel'},
    'HINDALCO.NS': {'sector': 'Metals & Mining', 'sub_sector': 'Aluminum'},
    'VEDL.NS': {'sector': 'Metals & Mining', 'sub_sector': 'Diversified Mining'},
    'COALINDIA.NS': {'sector': 'Metals & Mining', 'sub_sector': 'Coal'},
    
    # Large Cap Infrastructure
    'LT.NS': {'sector': 'Infrastructure', 'sub_sector': 'Construction'},
    'ULTRACEMCO.NS': {'sector': 'Infrastructure', 'sub_sector': 'Cement'},
    'AMBUJACEM.NS': {'sector': 'Infrastructure', 'sub_sector': 'Cement'},
    'ACC.NS': {'sector': 'Infrastructure', 'sub_sector': 'Cement'},
    'SHREECEM.NS': {'sector': 'Infrastructure', 'sub_sector': 'Cement'},
    
    # Telecom
    'BHARTIARTL.NS': {'sector': 'Telecom', 'sub_sector': 'Telecom Services'},
    
    # Power
    'NTPC.NS': {'sector': 'Power', 'sub_sector': 'Power Generation'},
    'POWERGRID.NS': {'sector': 'Power', 'sub_sector': 'Power Transmission'},
    'ADANIPOWER.NS': {'sector': 'Power', 'sub_sector': 'Power Generation'},
    
    # Add more mappings as needed...
}

# Nifty 50 stocks (Large Cap)
NIFTY_50 = [
    'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS',
    'HINDUNILVR.NS', 'ITC.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'KOTAKBANK.NS',
    'LT.NS', 'AXISBANK.NS', 'ASIANPAINT.NS', 'MARUTI.NS', 'SUNPHARMA.NS',
    'TITAN.NS', 'BAJAJ-AUTO.NS', 'ULTRACEMCO.NS', 'NESTLEIND.NS', 'WIPRO.NS',
    'M&M.NS', 'ONGC.NS', 'TATAMOTORS.NS', 'NTPC.NS', 'JSWSTEEL.NS',
    'TATASTEEL.NS', 'POWERGRID.NS', 'HCLTECH.NS', 'COALINDIA.NS', 'INDUSINDBK.NS',
    'BAJFINANCE.NS', 'TECHM.NS', 'ADANIPORTS.NS', 'GRASIM.NS', 'EICHERMOT.NS',
    'HINDALCO.NS', 'BRITANNIA.NS', 'DRREDDY.NS', 'CIPLA.NS', 'DIVISLAB.NS',
    'APOLLOHOSP.NS', 'HEROMOTOCO.NS', 'SHRIRAMFIN.NS', 'TATACONSUM.NS', 'BPCL.NS',
    'ADANIENT.NS', 'SBILIFE.NS', 'BAJAJFINSV.NS', 'LTIM.NS', 'HDFCLIFE.NS'
]

# Nifty Next 50 stocks (Large-Mid cap boundary)
NIFTY_NEXT_50 = [
    'ADANIGREEN.NS', 'ADANIPORTS.NS', 'AMBUJACEM.NS', 'BANDHANBNK.NS', 'BEL.NS',
    'BERGEPAINT.NS', 'BOSCHLTD.NS', 'CANBK.NS', 'CHOLAFIN.NS', 'COLPAL.NS',
    'DABUR.NS', 'DLF.NS', 'GAIL.NS', 'GODREJCP.NS', 'HAVELLS.NS',
    'ICICIPRULI.NS', 'INDIGO.NS', 'INDUSTOWER.NS', 'IOC.NS', 'JINDALSTEL.NS',
    'MARICO.NS', 'MCDOWELL-N.NS', 'MUTHOOTFIN.NS', 'NMDC.NS', 'PAGEIND.NS',
    'PIDILITIND.NS', 'PNB.NS', 'SIEMENS.NS', 'SRF.NS', 'TATACOMM.NS',
    'TATAPOWER.NS', 'TORNTPHARM.NS', 'TRENT.NS', 'UBL.NS', 'UPL.NS',
    'VEDL.NS', 'VOLTAS.NS', 'ZYDUSLIFE.NS', 'MPHASIS.NS', 'DMART.NS',
    'MOTHERSON.NS', 'PETRONET.NS', 'PFC.NS', 'RECLTD.NS', 'LTTS.NS',
    'SAIL.NS', 'IRCTC.NS', 'HAL.NS', 'ZOMATO.NS', 'DIXON.NS'
]

# ETF List (Exchange Traded Funds)
ETF_LIST = [
    'NIFTYBEES.NS', 'JUNIORBEES.NS', 'BANKBEES.NS', 'INFRABEES.NS',
    'PSUBNKBEES.NS', 'PVTBNKBEES.NS', 'ITSECTOR.NS', 'CPSEETF.NS',
    'GOLDBEES.NS', 'LIQUIDBEES.NS', 'SETFGOLD.NS', 'NIFTYETF.NS',
    'MON100.NS', 'AUTOETF.NS', 'PHARMAETF.NS', 'BANKIETF.NS'
]


def classify_market_cap(ticker: str) -> str:
    """Classify stock by market capitalization"""
    # Check if it's an ETF first
    if ticker in ETF_LIST:
        return 'ETF'
    
    # Large Cap: Nifty 50
    if ticker in NIFTY_50:
        return 'Large Cap'
    
    # Mid Cap: Nifty Next 50 + some buffer
    if ticker in NIFTY_NEXT_50:
        return 'Mid Cap'
    
    # By default, classify as Small Cap
    # (In production, you'd use actual market cap data from API)
    return 'Small Cap'


def get_sector_metadata(ticker: str) -> Dict[str, str]:
    """Get sector metadata for a stock"""
    if ticker in SECTOR_MAP:
        return SECTOR_MAP[ticker]
    else:
        # Default for unmapped stocks
        # In production, you'd fetch this from NSE API or manual curation
        return {
            'sector': 'Others',
            'sub_sector': 'Diversified'
        }


def is_etf(ticker: str) -> bool:
    """Check if ticker is an ETF"""
    return ticker in ETF_LIST or 'ETF' in ticker.upper() or 'BEES' in ticker.upper()


def update_stock_tickers_csv():
    """Main function to update stock tickers CSV with metadata"""
    logger.info("Starting stock tickers CSV enhancement...")
    
    # Read existing CSV
    csv_path = Path('data/stock_tickers.csv')
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    df = pd.read_csv(csv_path)
    logger.info(f"Loaded {len(df)} stocks from CSV")
    
    # Add new columns
    logger.info("Adding sector metadata...")
    df['sector'] = df['ticker'].apply(lambda t: get_sector_metadata(t)['sector'])
    df['sub_sector'] = df['ticker'].apply(lambda t: get_sector_metadata(t)['sub_sector'])
    
    logger.info("Classifying market capitalization...")
    df['market_cap'] = df['ticker'].apply(classify_market_cap)
    
    logger.info("Identifying ETFs...")
    df['is_etf'] = df['ticker'].apply(is_etf)
    
    # Save enhanced CSV
    output_path = Path('data/stock_tickers_enhanced.csv')
    df.to_csv(output_path, index=False)
    logger.info(f"✅ Enhanced CSV saved to: {output_path}")
    
    # Print statistics
    logger.info("\n📊 Statistics:")
    logger.info(f"  Total stocks: {len(df)}")
    logger.info(f"  ETFs: {df['is_etf'].sum()}")
    logger.info(f"\n  Market Cap Distribution:")
    logger.info(f"{df['market_cap'].value_counts()}")
    logger.info(f"\n  Top 10 Sectors:")
    logger.info(f"{df['sector'].value_counts().head(10)}")
    
    # Show sample
    logger.info("\n📝 Sample (first 10 rows):")
    print(df.head(10).to_string())
    
    return df


if __name__ == "__main__":
    try:
        enhanced_df = update_stock_tickers_csv()
        print("\n✅ CSV enhancement complete!")
        print(f"Enhanced file: data/stock_tickers_enhanced.csv")
        print(f"\nNext steps:")
        print(f"1. Review the enhanced CSV")
        print(f"2. Manually update SECTOR_MAP for more stocks")
        print(f"3. Run database migration to add new tables")
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
