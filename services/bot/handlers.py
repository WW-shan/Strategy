from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from services import api_client

router = Router()

# --- Keyboards ---
def get_main_reply_keyboard():
    """常驻菜单按钮（显示在输入框位置）"""
    kb = [
        [KeyboardButton(text="📈 策略市场"), KeyboardButton(text="👤 我的账户")],
        [KeyboardButton(text="💳 充值中心"), KeyboardButton(text="ℹ️ 帮助")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def main_menu_kb():
    kb = [
        [InlineKeyboardButton(text="📈 查看策略", callback_data="view_strategies")],
        [InlineKeyboardButton(text="👤 我的账户", callback_data="my_account")],
        [InlineKeyboardButton(text="💳 充值 / 支付", callback_data="payment_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def back_to_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 返回主菜单", callback_data="main_menu")]])

# --- Handlers ---

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    # Register user in background
    user = message.from_user
    await api_client.register_user(user.id, user.username, user.full_name)
    
    welcome_text = (
        f"👋 <b>你好，{user.first_name}！</b>\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"欢迎来到 <b>SW² WAVE策略交易平台</b>\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"💡 <i>实时信号 · 智能策略 · 专业交易</i>\n\n"
        f"请使用下方菜单按钮开始使用："
    )
    
    await message.answer(welcome_text, reply_markup=get_main_reply_keyboard(), parse_mode="HTML")

# --- 处理常驻菜单按钮 ---
@router.message(F.text == "📈 策略市场")
async def msg_view_strategies(message: types.Message):
    loading_msg = await message.answer("⏳ 加载中...")
    
    try:
        strategies = await api_client.get_strategies()
    except Exception:
        await loading_msg.edit_text("❌ 网络错误，请稍后再试")
        return
    
    if not strategies:
        await loading_msg.edit_text("暂无可用策略。")
        return

    text = (
        "📈 <b>策略市场</b>\n\n"
        "━━━━━━━━━━━━━━━━\n\n"
    )
    kb = []
    
    for s in strategies:
        price = f"💰 ${s['price_monthly']}/月"
        desc = s['description'] or '专业量化交易策略'
        text += (
            f"▫️ <b>{s['name']}</b>\n"
            f"   {desc}\n"
            f"   {price}\n\n"
        )
        # Add detail button and subscribe button
        kb.append([
            InlineKeyboardButton(text=f"📊 {s['name']} 详情", callback_data=f"detail_{s['id']}"),
            InlineKeyboardButton(text=f"✅ 订阅", callback_data=f"sub_{s['id']}")
        ])
    
    await loading_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@router.message(F.text == "👤 我的账户")
async def msg_my_account(message: types.Message):
    loading_msg = await message.answer("⏳ 加载中...")
    
    try:
        user_info = await api_client.get_user_info(message.from_user.id)
        subs = await api_client.get_user_subscriptions(message.from_user.id)
    except Exception:
        await loading_msg.edit_text("❌ 网络错误，请稍后再试")
        return
    
    balance = user_info.get('balance', 0.0) if user_info else 0.0
    
    text = (
        f"👤 <b>我的账户</b>\n\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"🆔 用户ID: <code>{message.from_user.id}</code>\n"
        f"💰 账户余额: <b>${balance:.2f}</b>\n\n"
    )
    
    kb = []
    if subs:
        text += "📋 <b>我的订阅</b>\n\n"
        for sub in subs:
            text += f"  ✅ <b>{sub['strategy_name']}</b>\n     ⏰ 到期: {sub['end_date']}\n\n"
        kb.append([InlineKeyboardButton(text="🔄 续订策略", callback_data="renew_menu")])
        kb.append([InlineKeyboardButton(text="📊 信号历史", callback_data="signal_history")])
    else:
        text += "📋 <b>我的订阅</b>\n\n暂无活跃订阅，去策略市场看看吧！"
    
    await loading_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb) if kb else None, parse_mode="HTML")

@router.message(F.text == "💳 充值中心")
async def msg_payment(message: types.Message):
    user_info = await api_client.get_user_info(message.from_user.id)
    balance = user_info.get('balance', 0.0) if user_info else 0.0

    text = (
        f"💳 <b>充值中心</b>\n\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"💰 当前余额: <b>${balance:.2f}</b>\n\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"💎 支持的充值方式：\n"
        f"   • USDT (TRC20)\n\n"
        f"<i>快速到账 · 安全可靠</i>"
    )
    
    kb = [[InlineKeyboardButton(text="➕ 立即充值", callback_data="deposit_usdt")]]
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@router.message(F.text == "ℹ️ 帮助")
async def msg_help(message: types.Message):
    help_text = (
        "ℹ️ <b>帮助中心</b>\n\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "📱 <b>如何使用</b>\n"
        "1️⃣ 在策略市场浏览可用策略\n"
        "2️⃣ 充值账户余额\n"
        "3️⃣ 订阅您喜欢的策略\n"
        "4️⃣ 接收实时交易信号\n\n"
        "💬 <b>联系客服</b>\n"
        "如有问题，请联系客服\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "<i>祝您交易顺利！</i>"
    )
    await message.answer(help_text, parse_mode="HTML")

@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: types.CallbackQuery):
    main_text = (
        "🏠 <b>主菜单</b>\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "请选择您需要的功能："
    )
    await callback.message.edit_text(main_text, reply_markup=main_menu_kb(), parse_mode="HTML")

@router.callback_query(F.data == "view_strategies")
async def cb_view_strategies(callback: types.CallbackQuery):
    strategies = await api_client.get_strategies()
    
    if not strategies:
        await callback.answer("暂无可用策略。", show_alert=True)
        return

    text = (
        "📈 <b>策略市场</b>\n\n"
        "━━━━━━━━━━━━━━━━\n\n"
    )
    kb = []
    
    for s in strategies:
        price = f"💰 ${s['price_monthly']}/月"
        desc = s['description'] or '专业量化交易策略'
        text += (
            f"▫️ <b>{s['name']}</b>\n"
            f"   {desc}\n"
            f"   {price}\n\n"
        )
        kb.append([InlineKeyboardButton(text=f"✅ 订阅 {s['name']}", callback_data=f"sub_{s['id']}")])
    
    kb.append([InlineKeyboardButton(text="🔙 返回主菜单", callback_data="main_menu")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@router.callback_query(F.data == "my_account")
async def cb_my_account(callback: types.CallbackQuery):
    # Fetch user info and subs
    user_info = await api_client.get_user_info(callback.from_user.id)
    subs = await api_client.get_user_subscriptions(callback.from_user.id)
    
    balance = user_info.get('balance', 0.0) if user_info else 0.0
    
    text = (
        f"👤 <b>我的账户</b>\n\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"🆔 用户ID: <code>{callback.from_user.id}</code>\n"
        f"💰 账户余额: <b>${balance:.2f}</b>\n\n"
    )
    
    kb = []
    if subs:
        text += "📋 <b>我的订阅</b>\n\n"
        for sub in subs:
            text += f"  ✅ <b>{sub['strategy_name']}</b>\n     ⏰ 到期: {sub['end_date']}\n\n"
        kb.append([InlineKeyboardButton(text="🔄 续订策略", callback_data="renew_menu")])
    else:
        text += "📋 <b>我的订阅</b>\n\n暂无活跃订阅，去策略市场看看吧！"
    
    kb.append([InlineKeyboardButton(text="🔙 返回主菜单", callback_data="main_menu")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@router.callback_query(F.data == "payment_menu")
async def cb_payment(callback: types.CallbackQuery):
    user_info = await api_client.get_user_info(callback.from_user.id)
    balance = user_info.get('balance', 0.0) if user_info else 0.0

    text = (
        f"💳 <b>充值中心</b>\n\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"💰 当前余额: <b>${balance:.2f}</b>\n\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"💎 支持的充值方式：\n"
        f"   • USDT (TRC20)\n\n"
    )
    
    kb = [
        [InlineKeyboardButton(text="➕ 立即充值", callback_data="deposit_usdt")],
        [InlineKeyboardButton(text="🔙 返回主菜单", callback_data="main_menu")]
    ]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@router.callback_query(F.data.startswith("sub_"))
async def cb_subscribe(callback: types.CallbackQuery):
    strategy_id = int(callback.data.split("_")[1])
    
    # Show loading indicator
    await callback.answer("⏳ 正在处理订阅...", show_alert=False)
    
    # Call API to subscribe
    try:
        result = await api_client.subscribe_strategy(callback.from_user.id, strategy_id)
    except Exception as e:
        await callback.answer("❌ 网络错误，请稍后再试", show_alert=True)
        return
    
    if result:
        status = result.get("status")
        if status == "created":
            remaining = result.get("remaining_balance", 0)
            end_date = result.get("end_date", "")
            msg = (
                f"✅ 订阅成功！\n\n"
                f"📅 有效期至: {end_date}\n"
                f"💰 剩余余额: ${remaining:.2f}\n\n"
                f"祝您交易顺利！"
            )
            await callback.answer(msg, show_alert=True)
        elif status == "exists":
            await callback.answer("ℹ️ 您已订阅该策略", show_alert=True)
        elif status == "insufficient_balance":
            msg = (
                f"❌ 余额不足\n\n"
                f"所需金额: ${result.get('required', 0):.2f}\n"
                f"当前余额: ${result.get('available', 0):.2f}\n\n"
                f"请先充值后再订阅"
            )
            await callback.answer(msg, show_alert=True)
        else:
            await callback.answer(f"❌ {result.get('message', '订阅失败')}", show_alert=True)
    else:
        await callback.answer("❌ 网络错误，请稍后再试", show_alert=True)

@router.callback_query(F.data == "renew_menu")
async def cb_renew_menu(callback: types.CallbackQuery):
    """Show renewal menu with user's subscriptions"""
    subs = await api_client.get_user_subscriptions(callback.from_user.id)
    strategies = await api_client.get_strategies()
    
    if not subs:
        await callback.answer("您当前没有任何活跃订阅", show_alert=True)
        return
    
    text = (
        "🔄 <b>续订中心</b>\n\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "<i>选择要续订的策略（延长30天）</i>\n\n"
    )
    kb = []
    
    for sub in subs:
        strategy_name = sub['strategy_name']
        matching_strategy = next((s for s in strategies if s['name'] == strategy_name), None)
        if matching_strategy:
            price = matching_strategy['price_monthly']
            kb.append([InlineKeyboardButton(
                text=f"🔄 {strategy_name} - ${price}/月", 
                callback_data=f"renew_{matching_strategy['id']}"
            )])
            text += f"📅 <b>{strategy_name}</b>\n   ⏰ 到期: {sub['end_date']}\n\n"
    
    kb.append([InlineKeyboardButton(text="🔙 返回我的账户", callback_data="my_account")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@router.callback_query(F.data.startswith("renew_"))
async def cb_renew(callback: types.CallbackQuery):
    """Process subscription renewal"""
    strategy_id = int(callback.data.split("_")[1])
    
    await callback.answer("⏳ 正在处理续订...", show_alert=False)
    
    # Call API to renew subscription
    try:
        result = await api_client.renew_subscription(callback.from_user.id, strategy_id)
    except Exception:
        await callback.answer("❌ 网络错误，请稍后再试", show_alert=True)
        return
    
    if result:
        status = result.get("status")
        if status == "renewed":
            remaining = result.get("remaining_balance", 0)
            new_end = result.get("new_end_date", "N/A")
            msg = (
                f"✅ 续订成功！\n\n"
                f"📅 新到期日: {new_end}\n"
                f"💰 剩余余额: ${remaining:.2f}\n\n"
                f"感谢您的支持！"
            )
            await callback.answer(msg, show_alert=True)
        elif status == "insufficient_balance":
            msg = (
                f"❌ 余额不足\n\n"
                f"所需金额: ${result.get('required', 0):.2f}\n"
                f"当前余额: ${result.get('available', 0):.2f}\n\n"
                f"请先充值后再续订"
            )
            await callback.answer(msg, show_alert=True)
        else:
            await callback.answer(f"❌ {result.get('message', '续订失败')}", show_alert=True)
    else:
        await callback.answer("❌ 网络错误，请稍后再试", show_alert=True)

@router.callback_query(F.data.startswith("detail_"))
async def cb_strategy_detail(callback: types.CallbackQuery):
    """Show strategy details with subscription confirmation"""
    strategy_id = int(callback.data.split("_")[1])
    
    try:
        strategies = await api_client.get_strategies()
        strategy = next((s for s in strategies if s['id'] == strategy_id), None)
    except Exception:
        await callback.answer("❌ 加载失败", show_alert=True)
        return
    
    if not strategy:
        await callback.answer("❌ 策略不存在", show_alert=True)
        return
    
    text = (
        f"📊 <b>{strategy['name']}</b>\n\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"📝 <b>策略说明</b>\n"
        f"{strategy['description'] or '专业量化交易策略'}\n\n"
        f"💰 <b>订阅价格</b>\n"
        f"${strategy['price_monthly']}/月 (30天)\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"<i>点击下方按钮确认订阅</i>"
    )
    
    kb = [
        [InlineKeyboardButton(text="✅ 确认订阅", callback_data=f"confirm_sub_{strategy_id}")],
        [InlineKeyboardButton(text="🔙 返回", callback_data="view_strategies")]
    ]
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@router.callback_query(F.data.startswith("confirm_sub_"))
async def cb_confirm_subscribe(callback: types.CallbackQuery):
    """Confirm and process subscription"""
    strategy_id = int(callback.data.split("_")[2])
    
    await callback.answer("⏳ 正在处理订阅...", show_alert=False)
    
    try:
        result = await api_client.subscribe_strategy(callback.from_user.id, strategy_id)
    except Exception:
        await callback.answer("❌ 网络错误，请稍后再试", show_alert=True)
        return
    
    if result:
        status = result.get("status")
        if status == "created":
            remaining = result.get("remaining_balance", 0)
            end_date = result.get("end_date", "")
            msg = (
                f"✅ 订阅成功！\n\n"
                f"📅 有效期至: {end_date}\n"
                f"💰 剩余余额: ${remaining:.2f}\n\n"
                f"您将实时收到交易信号！"
            )
            await callback.answer(msg, show_alert=True)
            # Return to strategy list
            await cb_view_strategies(callback)
        elif status == "exists":
            await callback.answer("ℹ️ 您已订阅该策略", show_alert=True)
        elif status == "insufficient_balance":
            msg = (
                f"❌ 余额不足\n\n"
                f"所需金额: ${result.get('required', 0):.2f}\n"
                f"当前余额: ${result.get('available', 0):.2f}\n\n"
                f"请先充值后再订阅"
            )
            await callback.answer(msg, show_alert=True)
        else:
            await callback.answer(f"❌ {result.get('message', '订阅失败')}", show_alert=True)
    else:
        await callback.answer("❌ 网络错误，请稍后再试", show_alert=True)

@router.callback_query(F.data == "signal_history")
async def cb_signal_history(callback: types.CallbackQuery):
    """Show user's signal history (placeholder for now)"""
    text = (
        "📊 <b>信号历史</b>\n\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "<i>此功能正在开发中...</i>\n\n"
        "您可以在聊天记录中查看\n"
        "历史收到的交易信号。\n\n"
        "━━━━━━━━━━━━━━━━"
    )
    
    kb = [[InlineKeyboardButton(text="🔙 返回我的账户", callback_data="my_account")]]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

