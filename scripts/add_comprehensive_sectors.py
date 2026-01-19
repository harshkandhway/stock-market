#!/usr/bin/env python3
"""
Add comprehensive sector metadata for top 500 Indian stocks
Based on Nifty 500 constituents and major indices
"""

import pandas as pd

# Load current CSV
df = pd.read_csv('data/stock_tickers_enhanced.csv')

# Comprehensive sector mapping for major Indian stocks
# Source: Based on Nifty sector indices and company classifications
sector_mappings = {
    # Information Technology
    'Information Technology': [
        'TCS.NS', 'INFY.NS', 'WIPRO.NS', 'HCLTECH.NS', 'TECHM.NS', 'LTTS.NS', 
        'COFORGE.NS', 'MPHASIS.NS', 'PERSISTENT.NS', 'LTIM.NS', 'MINDTREE.NS',
        'TATAELXSI.NS', 'CYIENT.NS', 'SONATSOFTW.NS', 'ZENSAR.NS', 'KPIT.NS',
        'HAPPSTMNDS.NS', 'ROUTE.NS', 'MASTEK.NS', 'INTELLECT.NS', 'RATEGAIN.NS',
        'NAUKRI.NS', 'ZOMATO.NS', 'IRCTC.NS', 'POLICYBZR.NS',
    ],
    
    # Financial Services - Banking
    'Financial Services': [
        'HDFCBANK.NS', 'ICICIBANK.NS', 'KOTAKBANK.NS', 'AXISBANK.NS', 'SBIN.NS',
        'INDUSINDBK.NS', 'BANKBARODA.NS', 'PNB.NS', 'FEDERALBNK.NS', 'IDFCFIRSTB.NS',
        'BANDHANBNK.NS', 'AUBANK.NS', 'RBLBANK.NS', 'CANBK.NS', 'UNIONBANK.NS',
        'INDIANB.NS', 'MAHABANK.NS', 'J&KBANK.NS', 'CENTRALBK.NS', 'IOB.NS',
        'DCBBANK.NS', 'SOUTHBANK.NS', 'CITYUNIONBK.NS', 'KARUR.NS',
        # NBFCs
        'BAJFINANCE.NS', 'BAJAJFINSV.NS', 'CHOLAFIN.NS', 'LICHSGFIN.NS', 'SBICARD.NS',
        'M&MFIN.NS', 'L&TFH.NS', 'ICICIGI.NS', 'SBILIFE.NS', 'HDFCLIFE.NS',
        'ICICIPRULI.NS', 'MAXHEALTH.NS', 'STARHEALTH.NS', 'ICICIPRU.NS',
    ],
    
    # Consumer Goods - FMCG
    'Consumer Goods': [
        'HINDUNILVR.NS', 'ITC.NS', 'NESTLEIND.NS', 'BRITANNIA.NS', 'DABUR.NS',
        'MARICO.NS', 'GODREJCP.NS', 'COLPAL.NS', 'TATACONSUM.NS', 'UBL.NS',
        'EMAMILTD.NS', 'VBL.NS', 'RADICO.NS', 'MCDOWELL-N.NS', 'GILLETTE.NS',
        'PGHH.NS', 'BAYERCROP.NS', 'PIDILITIND.NS', 'JYOTHYLAB.NS', 'ZYDUSLIFE.NS',
        # Retail
        'DMART.NS', 'TRENT.NS', 'SHOPERSTOP.NS', 'ABFRL.NS', 'PAGEIND.NS',
        'TITAN.NS', 'RELAXO.NS', 'BATA.NS', 'KALYANKJIL.NS',
    ],
    
    # Automobile
    'Automobile': [
        'MARUTI.NS', 'M&M.NS', 'TATAMOTORS.NS', 'BAJAJ-AUTO.NS', 'EICHERMOT.NS',
        'HEROMOTOCO.NS', 'TVSMOTOR.NS', 'ASHOKLEY.NS', 'ESCORTS.NS', 'MOTHERSON.NS',
        'BOSCHLTD.NS', 'EXIDEIND.NS', 'AMARAJABAT.NS', 'MRF.NS', 'APOLLOTYRE.NS',
        'BALKRISIND.NS', 'CEAT.NS', 'JK TYRE.NS', 'SANDHAR.NS', 'FINCABLES.NS',
        'TIINDIA.NS', 'SUPRAJIT.NS', 'GABRIEL.NS', 'ENDURANCE.NS',
    ],
    
    # Metals & Mining
    'Metals & Mining': [
        'TATASTEEL.NS', 'JSWSTEEL.NS', 'HINDALCO.NS', 'VEDL.NS', 'COALINDIA.NS',
        'SAIL.NS', 'NMDC.NS', 'JINDALSTEL.NS', 'HINDZINC.NS', 'NATIONALUM.NS',
        'MOIL.NS', 'RATNAMANI.NS', 'WELCORP.NS', 'WELSPUNIND.NS', 'KAJARIACER.NS',
        'ORIENTCEM.NS', 'JKCEMENT.NS', 'RAMCOCEM.NS', 'HERITGFOOD.NS', 'STAR CEMENT.NS',
    ],
    
    # Oil & Gas
    'Oil & Gas': [
        'RELIANCE.NS', 'ONGC.NS', 'IOC.NS', 'BPCL.NS', 'HINDPETRO.NS',
        'GAIL.NS', 'OIL.NS', 'MGL.NS', 'IGL.NS', 'PETRONET.NS',
        'GUJGASLTD.NS', 'AEGISCHEM.NS', 'DEEPAKNI T.NS', 'NOCIL.NS',
    ],
    
    # Pharmaceuticals & Healthcare
    'Healthcare': [
        'SUNPHARMA.NS', 'DRREDDY.NS', 'CIPLA.NS', 'DIVISLAB.NS', 'AUROPHARMA.NS',
        'LUPIN.NS', 'ALKEM.NS', 'TORNTPHARM.NS', 'BIOCON.NS', 'IPCALAB.NS',
        'LAURUSLABS.NS', 'GLENMARK.NS', 'ZYDUSLIFE.NS', 'NATCOPHARM.NS', 'LALPATHLAB.NS',
        'APOLLOHOSP.NS', 'FORTIS.NS', 'MAXHEALTH.NS', 'METROPOLIS.NS', 'THYROCARE.NS',
        'JUBLPHARMA.NS', 'GRANULES.NS', 'SUVEN.NS', 'SYNGENE.NS', 'CONCOR.NS',
    ],
    
    # Infrastructure & Construction
    'Infrastructure': [
        'LT.NS', 'ULTRACEMCO.NS', 'GRASIM.NS', 'SHREECEM.NS', 'AMBUJACEM.NS',
        'ACC.NS', 'INFRATEL.NS', 'PFC.NS', 'RECLTD.NS', 'IRFC.NS',
        'NBCC.NS', 'NCC.NS', 'IRB.NS', 'KNR.NS', 'ASTRAZEN.NS',
        'CESC.NS', 'SJVN.NS', 'NHPC.NS', 'RVNL.NS', 'CONCOR.NS',
    ],
    
    # Power & Energy
    'Power': [
        'POWERGRID.NS', 'NTPC.NS', 'TATAPOWER.NS', 'ADANIPOWER.NS', 'TORNTPOWER.NS',
        'ADANIGREEN.NS', 'ADANITRANS.NS', 'CESC.NS', 'SJVN.NS', 'NHPC.NS',
        'JSWENERGY.NS', 'RELINFRA.NS', 'SUZLON.NS', 'INOXWIND.NS',
    ],
    
    # Telecom
    'Telecommunications': [
        'BHARTIARTL.NS', 'IDEA.NS', 'TATACOMM.NS', 'ROUTE.NS', 'STERLITE.NS',
        'GTPL.NS', 'HFCL.NS', 'TEJAS.NS', 'DIXON.NS',
    ],
    
    # Media & Entertainment
    'Media & Entertainment': [
        'ZEEL.NS', 'SUNTV.NS', 'TV18BRDCST.NS', 'PVR.NS', 'INOXLEIS.NS',
        'DISHTV.NS', 'NETWORK18.NS', 'NAZARA.NS', 'BALAJITELE.NS',
    ],
    
    # Chemicals
    'Chemicals': [
        'UPL.NS', 'PIDILITIND.NS', 'SRF.NS', 'AARTI IND.NS', 'DEEPAKNTR.NS',
        'TATACHEM.NS', 'GUJALKALI.NS', 'GHCL.NS', 'ALKYLAMINE.NS', 'CLEAN SCIENCE.NS',
        'NAVINFLUOR.NS', 'TATAELXSI.NS', 'FLUOROCHEM.NS', 'ALKYLAMINE.NS',
    ],
    
    # Real Estate
    'Real Estate': [
        'DLF.NS', 'GODREJPR OP.NS', 'OBEROIRLTY.NS', 'PHOENIXLTD.NS', 'BRIGADE.NS',
        'PRESTIGE.NS', 'SOBHA.NS', 'MACROTECH.NS', 'MAHLIFE.NS', 'SUNTECK.NS',
    ],
    
    # Textiles
    'Textiles': [
        'RAYMOND.NS', 'ARVIND.NS', 'VARDHMAN.NS', 'TRIDENT.NS', 'KPR.NS',
        'WELSPUNIND.NS', 'GRASIM.NS', 'SPANDANA.NS', 'SOMICONVEY.NS',
    ],
}

# Market cap mappings based on Nifty indices
large_cap_stocks = [
    'TCS.NS', 'RELIANCE.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS', 'KOTAKBANK.NS',
    'HINDUNILVR.NS', 'ITC.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'BAJFINANCE.NS', 'LT.NS',
    'AXISBANK.NS', 'ASIANPAINT.NS', 'MARUTI.NS', 'WIPRO.NS', 'HCLTECH.NS', 'ULTRACEMCO.NS',
    'SUNPHARMA.NS', 'NESTLEIND.NS', 'TITAN.NS', 'TATASTEEL.NS', 'BAJAJFINSV.NS',
    'TECHM.NS', 'NTPC.NS', 'ONGC.NS', 'POWERGRID.NS', 'M&M.NS', 'JSWSTEEL.NS',
    'DIVISLAB.NS', 'ADANIENT.NS', 'TATAMOTORS.NS', 'COALINDIA.NS', 'IOC.NS',
    'GRASIM.NS', 'BRITANNIA.NS', 'CIPLA.NS', 'DRREDDY.NS', 'EICHERMOT.NS',
    'BPCL.NS', 'APOLLOHOSP.NS', 'HEROMOTOCO.NS', 'INDUSINDBK.NS', 'HINDALCO.NS',
    'SHREECEM.NS', 'UPL.NS', 'SBILIFE.NS', 'ADANIPORTS.NS', 'TATACONSUM.NS',
]

# Apply sector mappings
for sector, tickers in sector_mappings.items():
    for ticker in tickers:
        # Update both NS and BO versions
        mask_ns = df['ticker'] == ticker
        mask_bo = df['ticker'] == ticker.replace('.NS', '.BO')
        
        df.loc[mask_ns, 'sector'] = sector
        df.loc[mask_bo, 'sector'] = sector
        
        # Set sub_sector to sector name for now
        df.loc[mask_ns, 'sub_sector'] = sector
        df.loc[mask_bo, 'sub_sector'] = sector

# Apply large cap classifications
for ticker in large_cap_stocks:
    mask_ns = df['ticker'] == ticker
    mask_bo = df['ticker'] == ticker.replace('.NS', '.BO')
    
    df.loc[mask_ns, 'market_cap'] = 'Large Cap'
    df.loc[mask_bo, 'market_cap'] = 'Large Cap'

# Save updated CSV
df.to_csv('data/stock_tickers_enhanced.csv', index=False)

# Print statistics
total_stocks = len(df)
stocks_with_sectors = len(df[df['sector'] != 'Others'])
unique_sectors = df[df['sector'] != 'Others']['sector'].nunique()
large_caps = len(df[df['market_cap'] == 'Large Cap'])

print(f"✅ Sector metadata update complete!")
print(f"\nStatistics:")
print(f"  Total stocks: {total_stocks}")
print(f"  Stocks with sectors: {stocks_with_sectors}")
print(f"  Stocks without sectors: {total_stocks - stocks_with_sectors}")
print(f"  Unique sectors: {unique_sectors}")
print(f"  Large cap stocks: {large_caps}")
print(f"\nSector distribution:")
print(df['sector'].value_counts().head(15))
