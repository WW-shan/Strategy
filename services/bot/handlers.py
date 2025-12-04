from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from services import api_client

router = Router()

# --- Keyboards ---
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
    
    await message.answer(
        f"👋 你好 {user.first_name}!\n\n欢迎来到加密货币策略平台。\n请选择下方功能：",
        reply_markup=main_menu_kb()
    )

@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: types.CallbackQuery):
    await callback.message.edit_text("请选择下方功能：", reply_markup=main_menu_kb())

@router.callback_query(F.data == "view_strategies")
async def cb_view_strategies(callback: types.CallbackQuery):
    strategies = await api_client.get_strategies()
    
    if not strategies:
        await callback.answer("暂无可用策略。", show_alert=True)
        return

    text = "<b>📈 可用策略列表:</b>\n\n"
    kb = []
    
    for s in strategies:
        price = f"${s['price_monthly']}/月" if s['price_monthly'] > 0 else "免费"
        text += f"🔹 <b>{s['name']}</b>\n{s['description'] or '暂无描述'}\n价格: {price}\n\n"
        kb.append([InlineKeyboardButton(text=f"订阅 {s['name']}", callback_data=f"sub_{s['id']}")])
    
    kb.append([InlineKeyboardButton(text="🔙 返回", callback_data="main_menu")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@router.callback_query(F.data == "my_account")
async def cb_my_account(callback: types.CallbackQuery):
    # Fetch user subs
    subs = await api_client.get_user_subscriptions(callback.from_user.id)
    
    text = f"👤 <b>账户信息</b>\nID: <code>{callback.from_user.id}</code>\n\n"
    
    if subs:
        text += "<b>您的订阅:</b>\n"
        for sub in subs:
            text += f"✅ {sub['strategy_name']} (到期日: {sub['end_date']})\n"
    else:
        text += "您当前没有任何活跃订阅。"

    await callback.message.edit_text(text, reply_markup=back_to_main_kb(), parse_mode="HTML")

@router.callback_query(F.data == "payment_menu")
async def cb_payment(callback: types.CallbackQuery):
    text = "💳 <b>充值与支付</b>\n\n目前我们支持 USDT (TRC20) 充值。\n\n您的余额: $0.00"
    
    kb = [
        [InlineKeyboardButton(text="➕ 充值 USDT", callback_data="deposit_usdt")],
        [InlineKeyboardButton(text="🔙 返回", callback_data="main_menu")]
    ]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@router.callback_query(F.data.startswith("sub_"))
async def cb_subscribe(callback: types.CallbackQuery):
    strategy_id = int(callback.data.split("_")[1])
    
    # Call API to subscribe
    result = await api_client.subscribe_strategy(callback.from_user.id, strategy_id)
    
    if result and result.get("status") in ["created", "exists"]:
        msg = "✅ 订阅成功！" if result.get("status") == "created" else "ℹ️ 您已订阅该策略。"
        await callback.answer(msg, show_alert=True)
    else:
        await callback.answer("❌ 订阅失败，请稍后再试。", show_alert=True)

