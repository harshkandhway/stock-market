"""
On-Demand Analysis Service
Handles user-requested BUY signal analysis with filtering

Author: Harsh Kandhway
Date: January 19, 2026
"""

import logging
import time
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy.orm import Session

from src.bot.database.models import UserSignalRequest, UserSignalResponse
from src.bot.services.analysis_service import analyze_stock, get_current_price

logger = logging.getLogger(__name__)


class OnDemandAnalysisService:
    """Service for on-demand BUY signal analysis"""
    
    CACHE_DURATION_MINUTES = 15  # Cache results for 15 minutes
    RATE_LIMIT_PER_HOUR = 100  # Max 5 requests/hour/user
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.stock_metadata = self._load_stock_metadata()
    
    def _load_stock_metadata(self) -> pd.DataFrame:
        """Load stock metadata from enhanced CSV"""
        try:
            df = pd.read_csv('data/stock_tickers_enhanced.csv')
            logger.info(f"Loaded {len(df)} stocks with metadata")
            return df
        except FileNotFoundError:
            logger.warning("Enhanced CSV not found, using basic CSV")
            df = pd.read_csv('data/stock_tickers.csv')
            # Add default metadata
            df['sector'] = 'Others'
            df['market_cap'] = 'Unknown'
            df['is_etf'] = False
            df['sub_sector'] = 'Diversified'
            return df
    
    async def analyze_on_demand(
        self,
        user_id: int,
        sectors: Optional[List[str]] = None,
        market_caps: Optional[List[str]] = None,
        include_etf: bool = False,
        min_confidence: float = 70.0,
        min_risk_reward: float = 2.0
    ) -> Dict:
        """
        Perform on-demand analysis with filters
        
        Args:
            user_id: Telegram user ID
            sectors: List of sectors to include (None = all)
            market_caps: List of market caps to include (None = all)
            include_etf: Whether to include ETFs
            min_confidence: Minimum confidence threshold
            min_risk_reward: Minimum risk-reward ratio
            
        Returns:
            Dict with signals and metadata
        """
        start_time = time.time()
        
        # Check rate limit
        if not self._check_rate_limit(user_id):
            raise ValueError(f"Rate limit exceeded. Max {self.RATE_LIMIT_PER_HOUR} requests/hour.")
        
        # Check cache
        cached_result = self._get_cached_result(user_id, sectors, market_caps, include_etf)
        if cached_result:
            logger.info(f"Returning cached result for user {user_id}")
            return cached_result
        
        # Filter stocks
        filtered_stocks = self._filter_stocks(sectors, market_caps, include_etf)
        total_stocks = len(filtered_stocks)
        
        if total_stocks == 0:
            raise ValueError("No stocks match your filters")
        
        # User feedback: NO stock limit - analyze all filtered stocks
        logger.info(f"Analyzing {total_stocks} stocks (no limit applied)")
        
        # Analyze stocks
        signals = await self._analyze_stocks(filtered_stocks, min_confidence, min_risk_reward)
        
        # Save request to database
        request_record = self._save_request(
            user_id, sectors, market_caps, include_etf,
            min_confidence, min_risk_reward,
            total_stocks, len(signals),
            time.time() - start_time
        )
        
        # Save individual signals
        self._save_signals(request_record.id, user_id, signals)
        
        return {
            'request_id': request_record.id,
            'total_stocks_analyzed': total_stocks,
            'signals_found': len(signals),
            'signals': signals,
            'filters_applied': {
                'sectors': sectors,
                'market_caps': market_caps,
                'include_etf': include_etf,
                'min_confidence': min_confidence,
                'min_risk_reward': min_risk_reward
            },
            'analysis_duration_seconds': time.time() - start_time,
            'cached': False
        }
    
    def _filter_stocks(
        self,
        sectors: Optional[List[str]],
        market_caps: Optional[List[str]],
        include_etf: bool
    ) -> List[Dict]:
        """Filter stocks based on criteria"""
        df = self.stock_metadata.copy()
        
        # Filter by sector
        if sectors:
            df = df[df['sector'].isin(sectors)]
        
        # Filter by market cap
        if market_caps:
            df = df[df['market_cap'].isin(market_caps)]
        
        # Filter by ETF status
        # include_etf can be: True="ETF Only", False="Stocks Only", None="All"
        if include_etf is True:  # ETF Only mode
            df = df[df['is_etf'] == True]
        elif include_etf is False:  # Stocks Only mode
            df = df[df['is_etf'] == False]
        # If include_etf is None, don't filter (include both)
        
        # Convert to list of dicts
        return df.to_dict('records')
    
    async def _analyze_stocks(
        self,
        stocks: List[Dict],
        min_confidence: float,
        min_risk_reward: float
    ) -> List[Dict]:
        """Analyze stocks and return BUY signals"""
        signals = []
        errors = []
        total_stocks = len(stocks)
        
        logger.info(f"🚀 Starting analysis of {total_stocks} stocks...")
        
        for idx, stock in enumerate(stocks, 1):
            ticker = stock['ticker']
            try:
                # Use existing analyzer (correct parameters)
                result = analyze_stock(
                    ticker,
                    mode='balanced',
                    timeframe='medium',
                    horizon='3months',
                    use_cache=False
                )
                
                # Log result for each stock
                rec = result['recommendation_type']
                conf = result['confidence']
                rr = result['risk_reward']
                
                # Filter for BUY signals only
                if rec in ['STRONG BUY', 'BUY', 'WEAK BUY']:
                    if conf >= min_confidence and rr >= min_risk_reward:
                        # Add metadata
                        result['sector'] = stock.get('sector')
                        result['market_cap'] = stock.get('market_cap')
                        result['is_etf'] = stock.get('is_etf', False)
                        signals.append(result)
                        logger.info(f"  ✅ [{idx}/{total_stocks}] {ticker}: {rec} | Conf: {conf}% | R:R: {rr:.2f}")
                    else:
                        logger.debug(f"  ⚠️ [{idx}/{total_stocks}] {ticker}: {rec} filtered (conf={conf}%, rr={rr:.2f})")
                else:
                    logger.debug(f"  [{idx}/{total_stocks}] {ticker}: {rec}")
            
            except Exception as e:
                error_msg = f"{ticker}: {str(e)}"
                logger.warning(f"  ⚠️ [{idx}/{total_stocks}] Error: {error_msg}")
                errors.append(error_msg)
                continue
            
            # Progress update every 100 stocks
            if idx % 100 == 0:
                progress = (idx / total_stocks) * 100
                logger.info(f"📊 Progress: {idx}/{total_stocks} ({progress:.1f}%) | Signals: {len(signals)} | Errors: {len(errors)}")
        
        # Sort by confidence (descending)
        signals.sort(key=lambda x: x['confidence'], reverse=True)
        
        logger.info(f"✅ Analysis complete: {len(signals)} BUY signals from {total_stocks} stocks ({len(errors)} errors)")
        if errors and len(errors) <= 10:
            for err in errors:
                logger.warning(f"   Error detail: {err}")
        
        return signals
    
    def _check_rate_limit(self, user_id: int) -> bool:
        """Check if user has exceeded rate limit"""
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        count = self.db.query(UserSignalRequest).filter(
            UserSignalRequest.user_id == user_id,
            UserSignalRequest.request_timestamp >= one_hour_ago
        ).count()
        
        return count < self.RATE_LIMIT_PER_HOUR
    
    def _get_cached_result(
        self,
        user_id: int,
        sectors: Optional[List[str]],
        market_caps: Optional[List[str]],
        include_etf: bool
    ) -> Optional[Dict]:
        """Get cached result if available"""
        cache_cutoff = datetime.utcnow() - timedelta(minutes=self.CACHE_DURATION_MINUTES)
        
        # Find recent request with same filters
        recent_request = self.db.query(UserSignalRequest).filter(
            UserSignalRequest.user_id == user_id,
            UserSignalRequest.request_timestamp >= cache_cutoff,
            UserSignalRequest.sectors == json.dumps(sectors),
            UserSignalRequest.market_caps == json.dumps(market_caps),
            UserSignalRequest.include_etf == include_etf
        ).first()
        
        if recent_request:
            # Get signals from cache
            responses = self.db.query(UserSignalResponse).filter(
                UserSignalResponse.request_id == recent_request.id
            ).all()
            
            signals = [{
                'symbol': r.ticker,
                'recommendation': r.recommendation,
                'recommendation_type': r.recommendation_type,
                'confidence': r.confidence,
                'risk_reward': r.risk_reward,
                'current_price': r.current_price,
                'target': r.target,
                'stop_loss': r.stop_loss,
                'sector': r.sector,
                'market_cap': r.market_cap,
                'is_etf': r.is_etf
            } for r in responses]
            
            return {
                'request_id': recent_request.id,
                'total_stocks_analyzed': recent_request.total_stocks_analyzed,
                'signals_found': recent_request.total_signals_found,
                'signals': signals,
                'filters_applied': {
                    'sectors': json.loads(recent_request.sectors) if recent_request.sectors else None,
                    'market_caps': json.loads(recent_request.market_caps) if recent_request.market_caps else None,
                    'include_etf': recent_request.include_etf
                },
                'analysis_duration_seconds': recent_request.analysis_duration_seconds,
                'cached': True
            }
        
        return None
    
    def _save_request(
        self,
        user_id: int,
        sectors: Optional[List[str]],
        market_caps: Optional[List[str]],
        include_etf: bool,
        min_confidence: float,
        min_risk_reward: float,
        total_analyzed: int,
        signals_found: int,
        duration: float
    ) -> UserSignalRequest:
        """Save request to database"""
        request = UserSignalRequest(
            user_id=user_id,
            sectors=json.dumps(sectors) if sectors else None,
            market_caps=json.dumps(market_caps) if market_caps else None,
            include_etf=include_etf,
            min_confidence=min_confidence,
            min_risk_reward=min_risk_reward,
            total_stocks_analyzed=total_analyzed,
            total_signals_found=signals_found,
            signals_sent=signals_found,
            analysis_duration_seconds=duration,
            cached=False
        )
        
        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)
        
        return request
    
    def _save_signals(self, request_id: int, user_id: int, signals: List[Dict]):
        """Save individual signals to database"""
        for signal in signals:
            response = UserSignalResponse(
                request_id=request_id,
                user_id=user_id,
                ticker=signal['symbol'],
                recommendation=signal['recommendation'],
                recommendation_type=signal['recommendation_type'],
                confidence=signal['confidence'],
                risk_reward=signal['risk_reward'],
                current_price=signal['current_price'],
                target=signal.get('target'),
                stop_loss=signal.get('stop_loss'),
                sector=signal.get('sector'),
                market_cap=signal.get('market_cap'),
                is_etf=signal.get('is_etf', False)
            )
            self.db.add(response)
        
        self.db.commit()


def get_on_demand_analysis_service(db_session: Session) -> OnDemandAnalysisService:
    """Factory function"""
    return OnDemandAnalysisService(db_session)
