"""
Paper Trade Analysis Service
Analyzes performance and generates improvement recommendations

Author: Harsh Kandhway
"""

import logging
from typing import Dict, List
from datetime import datetime, timedelta
from collections import defaultdict

import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from src.bot.database.models import (
    PaperTradingSession, PaperTrade, PaperTradeAnalytics
)

logger = logging.getLogger(__name__)


class PaperTradeAnalysisService:
    """Service for analyzing paper trading performance and generating insights"""

    def __init__(self, db_session: Session):
        """
        Initialize analysis service

        Args:
            db_session: Database session
        """
        self.db = db_session

    def calculate_daily_analytics(
        self,
        session: PaperTradingSession,
        date: datetime
    ) -> PaperTradeAnalytics:
        """
        Calculate daily performance metrics

        Args:
            session: Paper trading session
            date: Date to analyze

        Returns:
            PaperTradeAnalytics record
        """
        # Get trades that closed today
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        trades = self.db.query(PaperTrade).filter(
            PaperTrade.session_id == session.id,
            PaperTrade.exit_date >= day_start,
            PaperTrade.exit_date < day_end
        ).all()

        # Calculate metrics
        metrics = self._calculate_metrics(trades, session, day_start, day_end)
        metrics['period_type'] = 'daily'

        # Create analytics record
        analytics = PaperTradeAnalytics(**metrics)

        # Save to database
        self.db.add(analytics)
        self.db.commit()
        self.db.refresh(analytics)

        logger.info(
            "📊 Daily analytics calculated: %d trades, %.1f%% win rate, profit factor %.2f",
            metrics['trades_count'], metrics['win_rate_pct'], metrics['profit_factor']
        )

        return analytics

    def calculate_weekly_analytics(
        self,
        session: PaperTradingSession,
        week_start: datetime
    ) -> PaperTradeAnalytics:
        """
        Calculate weekly performance metrics

        Args:
            session: Paper trading session
            week_start: Start of week (Monday)

        Returns:
            PaperTradeAnalytics record
        """
        week_end = week_start + timedelta(days=7)

        trades = self.db.query(PaperTrade).filter(
            PaperTrade.session_id == session.id,
            PaperTrade.exit_date >= week_start,
            PaperTrade.exit_date < week_end
        ).all()

        # Calculate metrics
        metrics = self._calculate_metrics(trades, session, week_start, week_end)
        metrics['period_type'] = 'weekly'

        # Create analytics record
        analytics = PaperTradeAnalytics(**metrics)

        self.db.add(analytics)
        self.db.commit()
        self.db.refresh(analytics)

        logger.info(
            "📊 Weekly analytics calculated: %d trades, %.1f%% win rate, profit factor %.2f",
            metrics['trades_count'], metrics['win_rate_pct'], metrics['profit_factor']
        )

        return analytics

    def _calculate_metrics(
        self,
        trades: List[PaperTrade],
        session: PaperTradingSession,
        period_start: datetime,
        period_end: datetime
    ) -> Dict:
        """
        Calculate performance metrics for a set of trades

        Args:
            trades: List of trades
            session: Paper trading session
            period_start: Period start date
            period_end: Period end date

        Returns:
            Dictionary of metrics
        """
        # Separate winners and losers
        winners = [t for t in trades if t.is_winner]
        losers = [t for t in trades if not t.is_winner]

        # Trade statistics
        trades_count = len(trades)
        winning_trades = len(winners)
        losing_trades = len(losers)
        win_rate_pct = (winning_trades / trades_count * 100) if trades_count > 0 else 0

        # P&L metrics
        gross_profit = sum(t.pnl for t in winners) if winners else 0
        gross_loss = sum(abs(t.pnl) for t in losers) if losers else 0
        net_pnl = gross_profit - gross_loss
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        # Performance metrics
        avg_win = np.mean([t.pnl for t in winners]) if winners else 0
        avg_loss = np.mean([abs(t.pnl) for t in losers]) if losers else 0
        avg_r_multiple = np.mean([t.r_multiple for t in trades]) if trades else 0
        best_trade_pnl = max([t.pnl for t in trades]) if trades else 0
        worst_trade_pnl = min([t.pnl for t in trades]) if trades else 0
        avg_hold_time_days = np.mean([t.days_held for t in trades]) if trades else 0

        # Exit reasons breakdown
        exit_reasons = {}
        for trade in trades:
            reason = trade.exit_reason
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

        # Capital metrics
        starting_capital = session.current_capital - net_pnl
        ending_capital = session.current_capital
        period_return_pct = (net_pnl / starting_capital * 100) if starting_capital > 0 else 0

        # Max drawdown (simplified - from peak capital)
        max_drawdown_pct = 0
        if session.peak_capital > 0:
            drawdown = (session.peak_capital - session.current_capital) / session.peak_capital * 100
            max_drawdown_pct = max(drawdown, 0)

        # Get max concurrent positions (from session tracking)
        max_concurrent_positions = session.max_positions  # Simplified

        return {
            'session_id': session.id,
            'period_start': period_start,
            'period_end': period_end,
            'trades_count': trades_count,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate_pct': win_rate_pct,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'net_pnl': net_pnl,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'avg_r_multiple': avg_r_multiple,
            'best_trade_pnl': best_trade_pnl,
            'worst_trade_pnl': worst_trade_pnl,
            'avg_hold_time_days': avg_hold_time_days,
            'max_concurrent_positions': max_concurrent_positions,
            'starting_capital': starting_capital,
            'ending_capital': ending_capital,
            'period_return_pct': period_return_pct,
            'max_drawdown_pct': max_drawdown_pct,
            'exit_reasons_breakdown': self._dict_to_json(exit_reasons),
            'insights': None  # Will be populated separately
        }

    def analyze_winning_trades(self, session: PaperTradingSession) -> Dict:
        """
        Analyze what worked in winning trades

        Args:
            session: Paper trading session

        Returns:
            Analysis of winning patterns
        """
        winners = self.db.query(PaperTrade).filter(
            PaperTrade.session_id == session.id,
            PaperTrade.is_winner == True
        ).all()

        if not winners:
            return {'total_winners': 0, 'message': 'No winning trades yet'}

        # Group by signal type
        by_signal = defaultdict(list)
        for trade in winners:
            by_signal[trade.recommendation_type].append(trade)

        # Find best signal type
        signal_stats = {}
        for signal_type, trades in by_signal.items():
            signal_stats[signal_type] = {
                'count': len(trades),
                'avg_pnl': np.mean([t.pnl for t in trades]),
                'avg_pnl_pct': np.mean([t.pnl_pct for t in trades]),
                'avg_r_multiple': np.mean([t.r_multiple for t in trades]),
                'avg_confidence': np.mean([t.entry_confidence for t in trades]),
                'avg_hold_days': np.mean([t.days_held for t in trades])
            }

        best_signal_type = max(signal_stats.keys(), key=lambda k: signal_stats[k]['count'])

        # Overall statistics
        avg_win_pct = np.mean([t.pnl_pct for t in winners])
        avg_r_multiple = np.mean([t.r_multiple for t in winners])
        avg_confidence = np.mean([t.entry_confidence for t in winners])
        avg_hold_days = np.mean([t.days_held for t in winners])

        # Common patterns
        patterns = []
        patterns.append(f"Winners held avg {avg_hold_days:.1f} days")
        patterns.append(f"{best_signal_type} signals have highest win count ({signal_stats[best_signal_type]['count']})")
        patterns.append(f"Avg confidence of winners: {avg_confidence:.1f}%")

        if avg_r_multiple > 1.5:
            patterns.append(f"Strong R:R performance: {avg_r_multiple:.2f}R average")

        return {
            'total_winners': len(winners),
            'avg_win_pct': avg_win_pct,
            'avg_r_multiple': avg_r_multiple,
            'avg_confidence': avg_confidence,
            'avg_hold_days': avg_hold_days,
            'best_signal_type': best_signal_type,
            'signal_stats': signal_stats,
            'common_patterns': patterns
        }

    def analyze_losing_trades(self, session: PaperTradingSession) -> Dict:
        """
        Analyze what didn't work in losing trades

        Args:
            session: Paper trading session

        Returns:
            Analysis of losing patterns
        """
        losers = self.db.query(PaperTrade).filter(
            PaperTrade.session_id == session.id,
            PaperTrade.is_winner == False
        ).all()

        if not losers:
            return {'total_losers': 0, 'message': 'No losing trades yet'}

        # Exit reasons breakdown
        exit_reasons = defaultdict(int)
        for trade in losers:
            exit_reasons[trade.exit_reason] += 1

        # Premature stop-outs (trades that reversed after hitting stop)
        premature_stops = sum(1 for t in losers if t.exit_reason == 'STOP_LOSS' and t.max_unrealized_gain > 0)

        # Group by signal type
        by_signal = defaultdict(list)
        for trade in losers:
            by_signal[trade.recommendation_type].append(trade)

        signal_stats = {}
        for signal_type, trades in by_signal.items():
            signal_stats[signal_type] = {
                'count': len(trades),
                'avg_loss': np.mean([abs(t.pnl) for t in trades]),
                'avg_loss_pct': np.mean([abs(t.pnl_pct) for t in trades]),
                'avg_confidence': np.mean([t.entry_confidence for t in trades])
            }

        # Find worst performing signal type
        worst_signal_type = max(signal_stats.keys(), key=lambda k: signal_stats[k]['count']) if signal_stats else None

        # Overall statistics
        avg_loss_pct = np.mean([abs(t.pnl_pct) for t in losers])
        avg_confidence = np.mean([t.entry_confidence for t in losers])

        # Common patterns
        patterns = []
        if premature_stops > len(losers) * 0.3:
            patterns.append(f"{premature_stops}/{len(losers)} losses were premature stop-outs")

        if worst_signal_type and signal_stats[worst_signal_type]['count'] > len(losers) * 0.4:
            patterns.append(f"{worst_signal_type} signals have high loss rate ({signal_stats[worst_signal_type]['count']} losses)")

        if avg_confidence < 65:
            patterns.append(f"Low avg confidence on losers: {avg_confidence:.1f}%")

        return {
            'total_losers': len(losers),
            'avg_loss_pct': avg_loss_pct,
            'avg_confidence': avg_confidence,
            'exit_reasons': dict(exit_reasons),
            'premature_stops': premature_stops,
            'worst_signal_type': worst_signal_type,
            'signal_stats': signal_stats,
            'common_patterns': patterns
        }

    def generate_improvement_recommendations(self, session: PaperTradingSession) -> List[Dict]:
        """
        Generate data-driven system improvement recommendations

        Requires minimum 10 trades for statistical validity

        Args:
            session: Paper trading session

        Returns:
            List of recommendations with priority and expected impact
        """
        all_trades = self.db.query(PaperTrade).filter(
            PaperTrade.session_id == session.id
        ).all()

        if len(all_trades) < 10:
            return [{
                'category': 'INSUFFICIENT_DATA',
                'priority': 'INFO',
                'recommendation': 'Need more trades for recommendations',
                'rationale': f'Only {len(all_trades)} trades completed (need 10+ for statistical validity)',
                'expected_impact': 'N/A'
            }]

        recommendations = []

        # Analyze signal type performance
        signal_performance = defaultdict(lambda: {'wins': 0, 'losses': 0, 'total_pnl': 0})

        for trade in all_trades:
            signal_type = trade.recommendation_type
            if trade.is_winner:
                signal_performance[signal_type]['wins'] += 1
            else:
                signal_performance[signal_type]['losses'] += 1
            signal_performance[signal_type]['total_pnl'] += trade.pnl

        # Recommendation 1: Filter weak signal types
        for signal_type, perf in signal_performance.items():
            total = perf['wins'] + perf['losses']
            win_rate = (perf['wins'] / total * 100) if total > 0 else 0

            if win_rate < 50 and signal_type == 'WEAK BUY' and total >= 5:
                recommendations.append({
                    'category': 'SIGNAL_FILTERING',
                    'priority': 'HIGH',
                    'recommendation': f'Avoid {signal_type} signals with confidence <70%',
                    'rationale': f'Only {win_rate:.0f}% win rate for {signal_type} signals ({perf["wins"]}/{total})',
                    'expected_impact': f'Reduce losing trades by {(total - perf["wins"]) / len(all_trades) * 100:.0f}%',
                    'data_support': {
                        'sample_size': total,
                        'win_rate': win_rate,
                        'losses': perf['losses']
                    }
                })

        # Recommendation 2: Premature stop-outs
        stop_loss_exits = [t for t in all_trades if t.exit_reason == 'STOP_LOSS']
        if len(stop_loss_exits) > len(all_trades) * 0.3:  # >30% stopped out
            premature = sum(1 for t in stop_loss_exits if t.max_unrealized_gain > 0)
            if premature > len(stop_loss_exits) * 0.3:
                recommendations.append({
                    'category': 'RISK_MANAGEMENT',
                    'priority': 'HIGH',
                    'recommendation': 'Widen stop losses for high-confidence entries (>75%)',
                    'rationale': f'{premature}/{len(stop_loss_exits)} stop-outs reversed (premature exits)',
                    'expected_impact': 'Reduce false stop-outs by 30%',
                    'data_support': {
                        'total_stops': len(stop_loss_exits),
                        'premature_stops': premature,
                        'premature_pct': (premature / len(stop_loss_exits) * 100) if stop_loss_exits else 0
                    }
                })

        # Recommendation 3: Optimize position sizing
        strong_buy_trades = [t for t in all_trades if t.recommendation_type == 'STRONG BUY']
        if strong_buy_trades:
            strong_buy_win_rate = sum(1 for t in strong_buy_trades if t.is_winner) / len(strong_buy_trades)
            if strong_buy_win_rate > 0.75:
                recommendations.append({
                    'category': 'POSITION_SIZING',
                    'priority': 'MEDIUM',
                    'recommendation': 'Increase position size for STRONG BUY with confidence >80%',
                    'rationale': f'{strong_buy_win_rate * 100:.0f}% win rate on STRONG BUY - underutilized opportunity',
                    'expected_impact': 'Increase overall profit by 15-20%',
                    'data_support': {
                        'sample_size': len(strong_buy_trades),
                        'win_rate': strong_buy_win_rate * 100
                    }
                })

        # Recommendation 4: Hold time optimization
        winners = [t for t in all_trades if t.is_winner]
        losers = [t for t in all_trades if not t.is_winner]

        if winners and losers:
            avg_winner_hold = np.mean([t.days_held for t in winners])
            avg_loser_hold = np.mean([t.days_held for t in losers])

            if avg_winner_hold > avg_loser_hold * 1.5:
                recommendations.append({
                    'category': 'EXIT_STRATEGY',
                    'priority': 'MEDIUM',
                    'recommendation': 'Let winners run longer - avoid early exits',
                    'rationale': f'Winners held avg {avg_winner_hold:.1f} days vs losers {avg_loser_hold:.1f} days',
                    'expected_impact': 'Increase avg win by 10-15%',
                    'data_support': {
                        'avg_winner_hold': avg_winner_hold,
                        'avg_loser_hold': avg_loser_hold
                    }
                })

        # Recommendation 5: Confidence threshold
        if winners and losers:
            avg_winner_conf = np.mean([t.entry_confidence for t in winners])
            avg_loser_conf = np.mean([t.entry_confidence for t in losers])

            if avg_winner_conf > avg_loser_conf + 5:  # 5% difference
                recommendations.append({
                    'category': 'SIGNAL_FILTERING',
                    'priority': 'HIGH',
                    'recommendation': f'Only trade signals with confidence >{avg_loser_conf + 5:.0f}%',
                    'rationale': f'Winners avg {avg_winner_conf:.1f}% confidence vs losers {avg_loser_conf:.1f}%',
                    'expected_impact': 'Increase win rate by 10-15%',
                    'data_support': {
                        'avg_winner_confidence': avg_winner_conf,
                        'avg_loser_confidence': avg_loser_conf
                    }
                })

        # Sort by priority
        priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2, 'INFO': 3}
        recommendations.sort(key=lambda x: priority_order.get(x['priority'], 3))

        logger.info("🧠 Generated %d improvement recommendations", len(recommendations))

        return recommendations

    async def generate_daily_summary(self, session: PaperTradingSession) -> Dict:
        """
        Generate complete daily summary

        Args:
            session: Paper trading session

        Returns:
            Daily summary dictionary
        """
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        analytics = self.calculate_daily_analytics(session, today)

        winners_analysis = self.analyze_winning_trades(session)
        losers_analysis = self.analyze_losing_trades(session)

        return {
            'date': today,
            'analytics': analytics,
            'winners_analysis': winners_analysis,
            'losers_analysis': losers_analysis
        }

    async def generate_weekly_summary(self, session: PaperTradingSession) -> Dict:
        """
        Generate comprehensive weekly summary

        Args:
            session: Paper trading session

        Returns:
            Weekly summary dictionary
        """
        # Get Monday of current week
        today = datetime.utcnow()
        week_start = today - timedelta(days=today.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        analytics = self.calculate_weekly_analytics(session, week_start)

        winners_analysis = self.analyze_winning_trades(session)
        losers_analysis = self.analyze_losing_trades(session)
        recommendations = self.generate_improvement_recommendations(session)

        return {
            'week_start': week_start,
            'analytics': analytics,
            'winners_analysis': winners_analysis,
            'losers_analysis': losers_analysis,
            'recommendations': recommendations
        }

    def _dict_to_json(self, data: dict) -> str:
        """Convert dictionary to JSON string"""
        import json
        return json.dumps(data)


def get_paper_trade_analysis_service(db_session: Session) -> PaperTradeAnalysisService:
    """
    Factory function to create analysis service

    Args:
        db_session: Database session

    Returns:
        PaperTradeAnalysisService instance
    """
    return PaperTradeAnalysisService(db_session)
