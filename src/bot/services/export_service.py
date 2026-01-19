"""
Export Service for BUY Signals
Generate CSV and PDF reports from scan results

Author: Harsh Kandhway
Date: January 19, 2026
"""

import logging
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import json

import pandas as pd
from sqlalchemy.orm import Session

from src.bot.database.models import UserSignalRequest, UserSignalResponse

logger = logging.getLogger(__name__)


async def export_to_csv(db: Session, request_id: int, user_id: int) -> str:
    """
    Export scan results to CSV
    
    Args:
        db: Database session
        request_id: Request ID to export
        user_id: User ID (for validation)
    
    Returns:
        Path to generated CSV file
    """
    # Get request and signals
    request = db.query(UserSignalRequest).filter(
        UserSignalRequest.id == request_id,
        UserSignalRequest.user_id == user_id
    ).first()
    
    if not request:
        raise ValueError("Request not found or unauthorized")
    
    signals = db.query(UserSignalResponse).filter(
        UserSignalResponse.request_id == request_id
    ).order_by(UserSignalResponse.confidence.desc()).all()
    
    # Convert to DataFrame
    data = []
    for signal in signals:
        upside_pct = ((signal.target / signal.current_price - 1) * 100) if signal.target else 0
        risk_pct = ((signal.current_price / signal.stop_loss - 1) * 100) if signal.stop_loss else 0
        
        data.append({
            'Symbol': signal.ticker,
            'Sector': signal.sector or 'Unknown',
            'Market Cap': signal.market_cap or 'Unknown',
            'Recommendation': signal.recommendation_type,
            'Confidence (%)': round(signal.confidence, 2),
            'Risk:Reward': round(signal.risk_reward, 2),
            'Current Price (₹)': round(signal.current_price, 2),
            'Target Price (₹)': round(signal.target, 2) if signal.target else '',
            'Stop Loss (₹)': round(signal.stop_loss, 2) if signal.stop_loss else '',
            'Upside (%)': round(upside_pct, 2),
            'Risk (%)': round(risk_pct, 2),
            'ETF': 'Yes' if signal.is_etf else 'No',
            'Timestamp': signal.sent_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    df = pd.DataFrame(data)
    
    # Create exports directory
    export_dir = Path('exports') / str(user_id)
    export_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"buy_signals_{request_id}_{timestamp}.csv"
    filepath = export_dir / filename
    
    # Save CSV
    df.to_csv(filepath, index=False)
    
    logger.info(f"CSV exported: {filepath} ({len(signals)} signals)")
    
    return str(filepath)


async def export_to_pdf(db: Session, request_id: int, user_id: int) -> str:
    """
    Export scan results to PDF
    
    Note: Requires fpdf2 library
    Install: pip install fpdf2
    
    Args:
        db: Database session
        request_id: Request ID to export
        user_id: User ID (for validation)
    
    Returns:
        Path to generated PDF file
    """
    try:
        from fpdf import FPDF
    except ImportError:
        raise ImportError("fpdf2 not installed. Run: pip install fpdf2")
    
    # Get request and signals
    request = db.query(UserSignalRequest).filter(
        UserSignalRequest.id == request_id,
        UserSignalRequest.user_id == user_id
    ).first()
    
    if not request:
        raise ValueError("Request not found or unauthorized")
    
    signals = db.query(UserSignalResponse).filter(
        UserSignalResponse.request_id == request_id
    ).order_by(UserSignalResponse.confidence.desc()).all()
    
    # Create PDF
    pdf = FPDF()
    pdf.add_page()
    
    # Title
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'BUY Signals Market Scan Report', ln=True, align='C')
    pdf.ln(5)
    
    # Metadata
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}", ln=True)
    pdf.cell(0, 6, f"Request ID: {request.id}", ln=True)
    pdf.cell(0, 6, f"Total Stocks Analyzed: {request.total_stocks_analyzed:,}", ln=True)
    pdf.cell(0, 6, f"BUY Signals Found: {request.total_signals_found}", ln=True)
    pdf.cell(0, 6, f"Analysis Duration: {request.analysis_duration_seconds:.1f}s", ln=True)
    pdf.ln(5)
    
    # Filters
    if request.sectors or request.market_caps:
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 6, 'Filters Applied:', ln=True)
        pdf.set_font('Arial', '', 10)
        
        if request.sectors:
            sectors = json.loads(request.sectors)
            pdf.cell(0, 6, f"  Sectors: {', '.join(sectors)}", ln=True)
        
        if request.market_caps:
            caps = json.loads(request.market_caps)
            pdf.cell(0, 6, f"  Market Cap: {', '.join(caps)}", ln=True)
        
        pdf.ln(5)
    
    # Table header
    pdf.set_font('Arial', 'B', 8)
    pdf.cell(30, 6, 'Symbol', 1)
    pdf.cell(35, 6, 'Sector', 1)
    pdf.cell(20, 6, 'Rec.', 1)
    pdf.cell(15, 6, 'Conf.', 1)
    pdf.cell(12, 6, 'R:R', 1)
    pdf.cell(22, 6, 'Price', 1)
    pdf.cell(22, 6, 'Target', 1)
    pdf.cell(15, 6, 'Cap', 1)
    pdf.ln()
    
    # Table rows
    pdf.set_font('Arial', '', 7)
    for idx, signal in enumerate(signals[:50], 1):  # Limit to 50 for PDF
        pdf.cell(30, 5, signal.ticker[:18], 1)
        pdf.cell(35, 5, (signal.sector or 'Others')[:18], 1)
        pdf.cell(20, 5, signal.recommendation_type[:8], 1)
        pdf.cell(15, 5, f"{signal.confidence:.1f}%", 1)
        pdf.cell(12, 5, f"{signal.risk_reward:.2f}", 1)
        pdf.cell(22, 5, f"Rs.{signal.current_price:.2f}", 1)
        pdf.cell(22, 5, f"Rs.{signal.target:.2f}" if signal.target else "-", 1)
        pdf.cell(15, 5, (signal.market_cap or 'Unknown')[:5], 1)
        pdf.ln()
    
    if len(signals) > 50:
        pdf.ln(5)
        pdf.set_font('Arial', 'I', 8)
        pdf.cell(0, 6, f"Note: Showing top 50 of {len(signals)} signals", ln=True)
    
    # Footer
    pdf.ln(10)
    pdf.set_font('Arial', 'I', 8)
    pdf.cell(0, 6, 'Disclaimer: This is for informational purposes only. Not investment advice.', ln=True, align='C')
    
    # Create exports directory
    export_dir = Path('exports') / str(user_id)
    export_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"buy_signals_{request_id}_{timestamp}.pdf"
    filepath = export_dir / filename
    
    # Save PDF
    pdf.output(str(filepath))
    
    logger.info(f"PDF exported: {filepath} ({len(signals)} signals)")
    
    return str(filepath)
