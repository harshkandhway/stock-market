"""
Telegram Handler for On-Demand BUY Signals
Comprehensive filter menu and market scanning

Commands:
- /scanmarket - Scan market with filters
- Main menu button: "📊 Scan Market"

Author: Harsh Kandhway
Date: January 19, 2026
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from src.bot.database.db import get_db_context
from src.bot.services.on_demand_analysis_service import get_on_demand_analysis_service
from src.bot.services.export_service import export_to_csv, export_to_pdf

logger = logging.getLogger(__name__)

# Available sectors
SECTORS = [
    "Information Technology", "Financial Services", "Oil & Gas",
    "Consumer Goods", "Healthcare", "Automobile",
    "Metals & Mining", "Infrastructure", "Telecom",
    "Power", "Chemicals", "Media & Entertainment",
    "Textiles", "Retail"
]

# Market caps
MARKET_CAPS = ["Large Cap", "Mid Cap", "Small Cap"]


def format_current_filters(filters: dict) -> str:
    """Format current filters for display"""
    if not filters:
        return "_None (will analyze all stocks)_"
    
    parts = []
    if filters.get('sectors'):
        sector_list = filters['sectors'][:3]
        sector_str = ', '.join(sector_list)
        if len(filters['sectors']) > 3:
            sector_str += f" +{len(filters['sectors'])-3} more"
        parts.append(f"✓ Sectors: {sector_str}")
    
    if filters.get('market_caps'):
        parts.append(f"✓ Market Cap: {', '.join(filters['market_caps'])}")
    
    if filters.get('etf_mode'):
        parts.append(f"✓ Mode: {filters['etf_mode']}")
    
    if filters.get('min_confidence') and filters.get('min_confidence') != 70.0:
        parts.append(f"✓ Min Confidence: {filters['min_confidence']}%")
    
    if filters.get('min_rr') and filters.get('min_rr') != 2.0:
        parts.append(f"✓ Min R:R: {filters['min_rr']}")
    
    return "\n".join(parts) if parts else "_None_"


async def scan_market_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /scanmarket command and main menu button"""
    user_id = update.effective_user.id
    
    # Initialize filters if not exists
    if 'scan_filters' not in context.user_data:
        context.user_data['scan_filters'] = {}
    
    # Get current filters FIRST
    current_filters = context.user_data.get('scan_filters', {})
    filters_text = format_current_filters(current_filters)
    
    # Count active filters
    filter_count = sum([
        len(current_filters.get('sectors', [])),
        len(current_filters.get('market_caps', [])),
        1 if current_filters.get('etf_mode') else 0
    ])
    
    # Make analyze button text more prominent
    analyze_text = "🚀 START ANALYSIS"
    if filter_count > 0:
        analyze_text = f"🚀 START ANALYSIS ({filter_count} filter{'' if filter_count == 1 else 's'} active)"
    
    # USER FEEDBACK: Show ALL filters in one comprehensive menu + "ANALYZE ALL" option
    keyboard = [
        [
            InlineKeyboardButton("🏭 Sectors", callback_data="scan_filter_sectors"),
            InlineKeyboardButton("📊 Market Cap", callback_data="scan_filter_marketcap")
        ],
        [
            InlineKeyboardButton("📈 ETF Only", callback_data="scan_etf_only"),
            InlineKeyboardButton("📉 Stocks Only", callback_data="scan_stocks_only")
        ],
        [
            InlineKeyboardButton("⚙️ Advanced", callback_data="scan_advanced"),
            InlineKeyboardButton("🔍 View Filters", callback_data="scan_view_filters")
        ],
        [InlineKeyboardButton("✅ Clear All Filters", callback_data="scan_clear_filters")],
        [InlineKeyboardButton(analyze_text, callback_data="scan_analyze")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = (
        f"🔍 *Market Scanner*\n\n"
        f"Scan all 4,426 stocks for BUY signals\n\n"
        f"*Current Filters:*\n{filters_text}\n\n"
        f"Select filter options or tap the button below to start:"
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )


async def scan_filter_sectors_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle sector filter selection"""
    query = update.callback_query
    await query.answer()
    
    # Show sector selection (3 per row)
    keyboard = []
    for i in range(0, len(SECTORS), 3):
        row = []
        for j in range(3):
            if i + j < len(SECTORS):
                sector = SECTORS[i + j]
                # Show checkmark if already selected
                current_sectors = context.user_data.get('scan_filters', {}).get('sectors', [])
                prefix = "✅ " if sector in current_sectors else ""
                row.append(InlineKeyboardButton(
                    f"{prefix}{sector[:12]}",
                    callback_data=f"sector_toggle_{i+j}"
                ))
        keyboard.append(row)
    
    keyboard.append([
        InlineKeyboardButton("✅ Done", callback_data="scan_market_confirm"),
        InlineKeyboardButton("❌ Cancel", callback_data="scan_market")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    selected = context.user_data.get('scan_filters', {}).get('sectors', [])
    selected_text = f"Selected: {', '.join(selected)}" if selected else "None selected"
    
    await query.edit_message_text(
        f"*Select Sectors*\n\n{selected_text}\n\nTap to select/deselect:\n\n_Tap Done when finished_",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def sector_toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle sector selection"""
    query = update.callback_query
    await query.answer()
    
    sector_idx = int(query.data.split('_')[-1])
    sector = SECTORS[sector_idx]
    
    # Toggle sector
    if 'scan_filters' not in context.user_data:
        context.user_data['scan_filters'] = {}
    
    if 'sectors' not in context.user_data['scan_filters']:
        context.user_data['scan_filters']['sectors'] = []
    
    if sector in context.user_data['scan_filters']['sectors']:
        context.user_data['scan_filters']['sectors'].remove(sector)
    else:
        context.user_data['scan_filters']['sectors'].append(sector)
    
    # Refresh UI
    await scan_filter_sectors_callback(update, context)


async def scan_filter_marketcap_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle market cap filter selection"""
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    for cap in MARKET_CAPS:
        current_caps = context.user_data.get('scan_filters', {}).get('market_caps', [])
        prefix = "✅ " if cap in current_caps else ""
        keyboard.append([InlineKeyboardButton(
            f"{prefix}{cap}",
            callback_data=f"cap_toggle_{cap.replace(' ', '_')}"
        )])
    
    keyboard.append([
        InlineKeyboardButton("✅ Done", callback_data="scan_market"),
        InlineKeyboardButton("❌ Cancel", callback_data="scan_market")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    selected = context.user_data.get('scan_filters', {}).get('market_caps', [])
    selected_text = f"Selected: {', '.join(selected)}" if selected else "All market caps"
    
    await query.edit_message_text(
        f"*Select Market Capitalization*\n\n{selected_text}:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def cap_toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle market cap selection"""
    query = update.callback_query
    await query.answer()
    
    cap = query.data.split('_', 2)[-1].replace('_', ' ')
    
    if 'scan_filters' not in context.user_data:
        context.user_data['scan_filters'] = {}
    
    if 'market_caps' not in context.user_data['scan_filters']:
        context.user_data['scan_filters']['market_caps'] = []
    
    if cap in context.user_data['scan_filters']['market_caps']:
        context.user_data['scan_filters']['market_caps'].remove(cap)
    else:
        context.user_data['scan_filters']['market_caps'].append(cap)
    
    await scan_filter_marketcap_callback(update, context)


async def scan_etf_only_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set ETF only mode"""
    query = update.callback_query
    await query.answer("ETF only mode selected")
    
    if 'scan_filters' not in context.user_data:
        context.user_data['scan_filters'] = {}
    
    context.user_data['scan_filters']['include_etf'] = True
    context.user_data['scan_filters']['etf_mode'] = "ETF Only"
    
    await scan_market_command(update, context)


async def scan_stocks_only_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set stocks only mode"""
    query = update.callback_query
    await query.answer("Stocks only mode selected")
    
    if 'scan_filters' not in context.user_data:
        context.user_data['scan_filters'] = {}
    
    context.user_data['scan_filters']['include_etf'] = False
    context.user_data['scan_filters']['etf_mode'] = "Stocks Only"
    
    await scan_market_command(update, context)


async def scan_clear_filters_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear all filters"""
    query = update.callback_query
    await query.answer("All filters cleared")
    
    context.user_data['scan_filters'] = {}
    
    await scan_market_command(update, context)


async def scan_market_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm filter selection and return to menu with clear next steps"""
    query = update.callback_query
    
    filters = context.user_data.get('scan_filters', {})
    filter_count = sum([
        len(filters.get('sectors', [])),
        len(filters.get('market_caps', [])),
        1 if filters.get('etf_mode') else 0
    ])
    
    if filter_count > 0:
        await query.answer(f"✅ {filter_count} filter(s) saved!", show_alert=False)
    else:
        await query.answer("✅ Filters saved", show_alert=False)
    
    await scan_market_command(update, context)


async def scan_clear_filters_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear all filters"""
    query = update.callback_query
    await query.answer("All filters cleared")
    
    context.user_data['scan_filters'] = {}
    
    await scan_market_command(update, context)


async def scan_view_filters_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View current filters in detail"""
    query = update.callback_query
    await query.answer()
    
    filters = context.user_data.get('scan_filters', {})
    
    if not filters or not any(filters.values()):
        message = "*Current Filters*\n\nNo filters applied. All stocks will be analyzed."
    else:
        message = "*Current Filters*\n\n"
        
        if filters.get('sectors'):
            message += f"✅ *Sectors:*\n"
            for sector in filters['sectors']:
                message += f"   • {sector}\n"
            message += "\n"
        
        if filters.get('market_caps'):
            message += f"✅ *Market Caps:*\n"
            for cap in filters['market_caps']:
                message += f"   • {cap}\n"
            message += "\n"
        
        if filters.get('etf_mode'):
            message += f"✅ *Mode:* {filters['etf_mode']}\n\n"
        
        if filters.get('min_confidence') and filters.get('min_confidence') != 70.0:
            message += f"✅ *Min Confidence:* {filters['min_confidence']}%\n\n"
        
        if filters.get('min_rr') and filters.get('min_rr') != 2.0:
            message += f"✅ *Min R:R:* {filters['min_rr']}\n\n"
    
    keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="scan_market")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def scan_advanced_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show advanced filter options"""
    query = update.callback_query
    await query.answer()
    
    filters = context.user_data.get('scan_filters', {})
    current_confidence = filters.get('min_confidence', 70.0)
    current_rr = filters.get('min_rr', 2.0)
    
    keyboard = [
        [InlineKeyboardButton(f"Min Confidence: {current_confidence}%", callback_data="adv_confidence")],
        [InlineKeyboardButton(f"Min Risk:Reward: {current_rr}", callback_data="adv_rr")],
        [InlineKeyboardButton("✅ Done", callback_data="scan_market")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "*Advanced Filters*\n\n"
        "Adjust minimum thresholds:\n\n"
        f"• Current Confidence: {current_confidence}%\n"
        f"• Current R:R: {current_rr}\n\n"
        "_Note: These will be adjustable via text input in a future update._",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def scan_clear_filters_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear all filters"""
    query = update.callback_query
    await query.answer("All filters cleared")
    
    context.user_data['scan_filters'] = {}
    
    await scan_market_command(update, context)


async def scan_analyze_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the analysis"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    filters = context.user_data.get('scan_filters', {})
    
    # Show progress
    await query.edit_message_text("🔄 Analyzing market... This may take a moment.")
    
    try:
        with get_db_context() as db:
            service = get_on_demand_analysis_service(db)
            result = await service.analyze_on_demand(
                user_id=user_id,
                sectors=filters.get('sectors'),
                market_caps=filters.get('market_caps'),
                include_etf=filters.get('include_etf', False),
                min_confidence=filters.get('min_confidence', 70.0),
                min_risk_reward=filters.get('min_rr', 2.0)
            )
        
        signals = result['signals']
        
        if len(signals) == 0:
            await query.edit_message_text(
                "❌ No BUY signals found matching your criteria.\n"
                "Try adjusting filters or check back later.",
                parse_mode='Markdown'
            )
            return
        
        # USER FEEDBACK: Add CSV and PDF export buttons
        export_keyboard = [
            [
                InlineKeyboardButton("📄 Export CSV", callback_data=f"export_csv_{result['request_id']}"),
                InlineKeyboardButton("📑 Export PDF", callback_data=f"export_pdf_{result['request_id']}")
            ],
            [InlineKeyboardButton("🔍 New Scan", callback_data="scan_market")]
        ]
        export_markup = InlineKeyboardMarkup(export_keyboard)
        
        # Send results
        message = format_signals_message(result, signals[:10])
        
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=export_markup
        )
        
        # Send additional batches if > 10
        if len(signals) > 10:
            for i in range(10, len(signals), 10):
                batch = signals[i:i+10]
                await context.bot.send_message(
                    chat_id=user_id,
                    text=format_signals_batch(batch, i+1),
                    parse_mode='Markdown'
                )
    
    except ValueError as e:
        await query.edit_message_text(f"❌ Error: {str(e)}")
    except Exception as e:
        logger.error(f"Error in scan_analyze: {e}", exc_info=True)
        await query.edit_message_text("❌ An error occurred. Please try again later.")


async def export_csv_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle CSV export"""
    query = update.callback_query
    await query.answer("Generating CSV...")
    
    request_id = int(query.data.split('_')[-1])
    user_id = query.from_user.id
    
    try:
        with get_db_context() as db:
            csv_path = await export_to_csv(db, request_id, user_id)
            
            # Send file
            with open(csv_path, 'rb') as f:
                await context.bot.send_document(
                    chat_id=user_id,
                    document=f,
                    filename=f"buy_signals_{request_id}.csv",
                    caption="📄 *BUY Signals - CSV Export*\n\nYour scan results in CSV format.",
                    parse_mode='Markdown'
                )
            
            await query.answer("✅ CSV sent!", show_alert=True)
    
    except Exception as e:
        logger.error(f"CSV export error: {e}", exc_info=True)
        await query.answer("❌ Export failed", show_alert=True)


async def export_pdf_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle PDF export"""
    query = update.callback_query
    await query.answer("Generating PDF...")
    
    request_id = int(query.data.split('_')[-1])
    user_id = query.from_user.id
    
    try:
        with get_db_context() as db:
            pdf_path = await export_to_pdf(db, request_id, user_id)
            
            # Send file
            with open(pdf_path, 'rb') as f:
                await context.bot.send_document(
                    chat_id=user_id,
                    document=f,
                    filename=f"buy_signals_{request_id}.pdf",
                    caption="📑 *BUY Signals - PDF Report*\n\nYour scan results in PDF format.",
                    parse_mode='Markdown'
                )
            
            await query.answer("✅ PDF sent!", show_alert=True)
    
    except Exception as e:
        logger.error(f"PDF export error: {e}", exc_info=True)
        await query.answer("❌ Export failed", show_alert=True)


def format_signals_message(result: dict, signals: list) -> str:
    """Format signals into Telegram message"""
    total = result['total_stocks_analyzed']
    found = result['signals_found']
    duration = result['analysis_duration_seconds']
    cached = result.get('cached', False)
    
    cache_indicator = " 📦 (from cache)" if cached else ""
    
    message = (
        f"✅ *Market Scan Complete*{cache_indicator}\n\n"
        f"📊 Analyzed: *{total:,}* stocks\n"
        f"🎯 Found: *{found}* BUY signals\n"
        f"⏱️ Time: {duration:.1f}s\n\n"
    )
    
    # Show applied filters
    filters = result.get('filters_applied', {})
    if any(filters.values()):
        message += "*Filters Applied:*\n"
        if filters.get('sectors'):
            sector_str = ', '.join(filters['sectors'][:3])
            if len(filters['sectors']) > 3:
                sector_str += f" +{len(filters['sectors'])-3} more"
            message += f"• Sectors: {sector_str}\n"
        if filters.get('market_caps'):
            message += f"• Market Cap: {', '.join(filters['market_caps'])}\n"
        if filters.get('include_etf'):
            message += f"• Include ETFs: Yes\n"
        message += "\n"
    
    message += f"*Top {min(10, found)} Signals:* (sorted by confidence)\n\n"
    
    for i, signal in enumerate(signals, 1):
        message += (
            f"{i}. *{signal['symbol']}* | {signal.get('sector', 'N/A')} | {signal.get('market_cap', 'N/A')}\n"
            f"   {signal['recommendation_type']} | Conf: {signal['confidence']:.1f}% | R:R: {signal['risk_reward']:.2f}\n"
            f"   Price: ₹{signal['current_price']:.2f} → Target: ₹{signal.get('target', 0):.2f}\n\n"
        )
    
    if found > 10:
        message += f"_Showing top 10 of {found} signals. More messages follow..._\n\n"
    
    message += "📥 *Export:* Use buttons below to download CSV or PDF"
    
    return message


def format_signals_batch(signals: list, start_num: int) -> str:
    """Format additional signals batch"""
    message = f"*Signals {start_num}-{start_num+len(signals)-1}:*\n\n"
    
    for i, signal in enumerate(signals, start_num):
        message += (
            f"{i}. *{signal['symbol']}* | {signal['recommendation_type']}\n"
            f"   {signal.get('sector', 'N/A')} | {signal.get('market_cap', 'N/A')} | "
            f"Conf: {signal['confidence']:.1f}% | R:R: {signal['risk_reward']:.2f}\n"
            f"   ₹{signal['current_price']:.2f} → ₹{signal.get('target', 0):.2f}\n\n"
        )
    
    return message


def register_on_demand_handlers(application):
    """Register all on-demand signal handlers"""
    application.add_handler(CommandHandler("scanmarket", scan_market_command))
    application.add_handler(CallbackQueryHandler(scan_market_command, pattern="^scan_market$"))
    application.add_handler(CallbackQueryHandler(scan_market_confirm_callback, pattern="^scan_market_confirm$"))
    application.add_handler(CallbackQueryHandler(scan_filter_sectors_callback, pattern="^scan_filter_sectors$"))
    application.add_handler(CallbackQueryHandler(scan_filter_marketcap_callback, pattern="^scan_filter_marketcap$"))
    application.add_handler(CallbackQueryHandler(sector_toggle_callback, pattern="^sector_toggle_"))
    application.add_handler(CallbackQueryHandler(cap_toggle_callback, pattern="^cap_toggle_"))
    application.add_handler(CallbackQueryHandler(scan_etf_only_callback, pattern="^scan_etf_only$"))
    application.add_handler(CallbackQueryHandler(scan_stocks_only_callback, pattern="^scan_stocks_only$"))
    application.add_handler(CallbackQueryHandler(scan_view_filters_callback, pattern="^scan_view_filters$"))
    application.add_handler(CallbackQueryHandler(scan_advanced_callback, pattern="^scan_advanced$"))
    application.add_handler(CallbackQueryHandler(scan_clear_filters_callback, pattern="^scan_clear_filters$"))
    application.add_handler(CallbackQueryHandler(scan_analyze_callback, pattern="^scan_analyze$"))
    application.add_handler(CallbackQueryHandler(export_csv_callback, pattern="^export_csv_"))
    application.add_handler(CallbackQueryHandler(export_pdf_callback, pattern="^export_pdf_"))
