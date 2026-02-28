"""
👗 KIYIM DO'KONI TELEGRAM BOT
Aiogram 3.x bilan yozilgan professional bot

O'rnatish:
    pip install aiogram==3.x

Ishga tushirish:
    python clothes_shop_bot.py
"""

import asyncio
import logging
import json
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ===================== SOZLAMALAR =====================
BOT_TOKEN = "8749131471:AAGm3h3Bm-NzUTuQkRx7PqHjqONC9gTzzNQ"
ADMIN_ID = 8092370127
ADMIN_PASSWORD = "alibek2009"  # ← PAROLNI SHU YERDA O'ZGARTIRING

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===================== MA'LUMOTLAR BAZASI =====================
PRODUCTS = {
    "men": {
        "name": "👔 Erkaklar",
        "items": {
            "m1": {"name": "Klassik Ko'ylak", "price": 150000, "sizes": ["S", "M", "L", "XL", "XXL"], "emoji": "👔"},
            "m2": {"name": "Jins Shim", "price": 220000, "sizes": ["28", "30", "32", "34", "36"], "emoji": "👖"},
            "m3": {"name": "Futbolka", "price": 80000, "sizes": ["S", "M", "L", "XL"], "emoji": "👕"},
            "m4": {"name": "Kostyum", "price": 850000, "sizes": ["46", "48", "50", "52", "54"], "emoji": "🤵"},
        }
    },
    "women": {
        "name": "👗 Ayollar",
        "items": {
            "w1": {"name": "Ko'ylak (Libos)", "price": 180000, "sizes": ["XS", "S", "M", "L", "XL"], "emoji": "👗"},
            "w2": {"name": "Bluzka", "price": 120000, "sizes": ["XS", "S", "M", "L"], "emoji": "👚"},
            "w3": {"name": "Yubka", "price": 140000, "sizes": ["XS", "S", "M", "L", "XL"], "emoji": "🩱"},
            "w4": {"name": "Shim", "price": 160000, "sizes": ["XS", "S", "M", "L", "XL"], "emoji": "👖"},
        }
    },
    "kids": {
        "name": "👶 Bolalar",
        "items": {
            "k1": {"name": "Bolalar Futbolka", "price": 60000, "sizes": ["3-4", "5-6", "7-8", "9-10", "11-12"], "emoji": "👕"},
            "k2": {"name": "Bolalar Shim", "price": 90000, "sizes": ["3-4", "5-6", "7-8", "9-10"], "emoji": "👖"},
            "k3": {"name": "Bolalar Ko'ylak", "price": 110000, "sizes": ["3-4", "5-6", "7-8", "9-10", "11-12"], "emoji": "👗"},
        }
    }
}

DATA_FILE = "shop_data.json"

def load_data():
    global carts, orders, order_counter
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                carts.update({int(k): v for k, v in data.get("carts", {}).items()})
                orders.update({int(k): v for k, v in data.get("orders", {}).items()})
                order_counter = data.get("order_counter", 1000)
        except Exception as e:
            logger.error(f"Ma'lumotlarni yuklashda xato: {e}")

def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "carts": {str(k): v for k, v in carts.items()},
                "orders": {str(k): v for k, v in orders.items()},
                "order_counter": order_counter
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ma'lumotlarni saqlashda xato: {e}")

carts = {}
orders = {}
order_counter = 1000

# Parolni to'g'ri kiritgan adminlar
verified_admins = set()


# ===================== HOLATLAR =====================
class OrderState(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()
    waiting_for_size = State()


class AdminState(StatesGroup):
    waiting_for_password = State()   # ← YANGI: parol kutish holati
    waiting_for_broadcast = State()


# ===================== KLAVIATURALAR =====================
def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛍 Katalog"), KeyboardButton(text="🛒 Savatcha")],
            [KeyboardButton(text="📦 Buyurtmalarim"), KeyboardButton(text="ℹ️ Ma'lumot")],
            [KeyboardButton(text="📞 Aloqa"), KeyboardButton(text="⭐ Aksiyalar")]
        ],
        resize_keyboard=True
    )

def categories_keyboard():
    buttons = []
    for cat_id, cat in PRODUCTS.items():
        buttons.append([InlineKeyboardButton(text=cat["name"], callback_data=f"cat_{cat_id}")])
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def products_keyboard(category_id):
    cat = PRODUCTS[category_id]
    buttons = []
    for item_id, item in cat["items"].items():
        text = f"{item['emoji']} {item['name']} - {item['price']:,} so'm"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"prod_{item_id}")])
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_categories")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def product_detail_keyboard(item_id, category_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Savatga qo'shish", callback_data=f"add_{item_id}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"cat_{category_id}")]
    ])

def size_keyboard(item_id, sizes):
    buttons = []
    row = []
    for size in sizes:
        row.append(InlineKeyboardButton(text=size, callback_data=f"size_{item_id}_{size}"))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_size")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def cart_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Buyurtma berish", callback_data="checkout")],
        [InlineKeyboardButton(text="🗑 Savatni tozalash", callback_data="clear_cart")],
        [InlineKeyboardButton(text="🛍 Davom ettirish", callback_data="back_categories")]
    ])

def confirm_order_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="confirm_order")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_order")]
    ])

def admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="📋 Barcha buyurtmalar")],
            [KeyboardButton(text="📣 Xabar yuborish"), KeyboardButton(text="🔙 Foydalanuvchi rejimi")]
        ],
        resize_keyboard=True
    )


# ===================== YORDAMCHI FUNKSIYALAR =====================
def find_product(item_id):
    for cat_id, cat in PRODUCTS.items():
        if item_id in cat["items"]:
            return cat["items"][item_id], cat_id
    return None, None

def get_cart_text(user_id):
    cart = carts.get(user_id, {})
    if not cart:
        return "🛒 Savatchingiz bo'sh!"
    text = "🛒 *Sizning savatchingiz:*\n\n"
    total = 0
    for item_key, item_data in cart.items():
        item, _ = find_product(item_data["item_id"])
        if item:
            subtotal = item["price"] * item_data["quantity"]
            total += subtotal
            text += f"{item['emoji']} {item['name']}\n"
            text += f"   Razmer: *{item_data['size']}* | Soni: *{item_data['quantity']}*\n"
            text += f"   Narxi: {subtotal:,} so'm\n\n"
    text += f"━━━━━━━━━━━━━━━\n"
    text += f"💰 *Jami: {total:,} so'm*"
    return text

def format_price(price):
    return f"{price:,} so'm"


# ===================== HANDLERLAR =====================
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    text = (
        f"👋 Xush kelibsiz, *{user.first_name}*!\n\n"
        f"🏪 *FashionShop* ga xush kelibsiz!\n"
        f"Bizda eng sifatli kiyimlar mavjud.\n\n"
        f"📱 Pastdagi tugmalardan foydalaning:"
    )
    await message.answer(text, reply_markup=main_keyboard(), parse_mode="Markdown")


# ==================== ADMIN PAROL TIZIMI ====================
async def cmd_admin(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id != ADMIN_ID:
        await message.answer(
            f"❌ Sizda admin huquqlari yo'q!\n\n"
            f"🆔 Sizning ID'ingiz: <code>{user_id}</code>",
            parse_mode="HTML"
        )
        return

    if user_id in verified_admins:
        # Allaqachon parol kiritilgan — to'g'ridan panel
        await message.answer("👨‍💼 Admin panelga xush kelibsiz!", reply_markup=admin_keyboard())
    else:
        # Parol so'raymiz
        await state.set_state(AdminState.waiting_for_password)
        await message.answer(
            "🔐 *Admin panelga kirish*\n\n"
            "Iltimos, admin parolini kiriting:",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )


async def process_admin_password(message: Message, state: FSMContext):
    user_id = message.from_user.id

    # Xavfsizlik: parol xabarini o'chiramiz
    try:
        await message.delete()
    except Exception:
        pass

    if message.text == ADMIN_PASSWORD:
        verified_admins.add(user_id)
        await state.clear()
        await message.answer(
            "✅ *Parol to'g'ri!*\n\nAdmin panelga xush kelibsiz! 👨‍💼",
            parse_mode="Markdown",
            reply_markup=admin_keyboard()
        )
        logger.info(f"Admin {user_id} muvaffaqiyatli kirdi.")
    else:
        data = await state.get_data()
        attempts = data.get("attempts", 0) + 1
        await state.update_data(attempts=attempts)

        if attempts >= 3:
            await state.clear()
            await message.answer(
                "🚫 *3 marta noto'g'ri parol!*\n\n"
                "Kirish bloklandi. Qayta urinish uchun /admin bosing.",
                parse_mode="Markdown",
                reply_markup=main_keyboard()
            )
            logger.warning(f"Admin {user_id} — 3x noto'g'ri parol, bloklandi.")
        else:
            remaining = 3 - attempts
            await message.answer(
                f"❌ *Parol noto'g'ri!*\n\n"
                f"Qayta urinib ko'ring. Qolgan urinish: *{remaining}* ta",
                parse_mode="Markdown"
            )
# ============================================================


async def show_catalog(message: Message):
    await message.answer("🛍 *Kategoriyalarni tanlang:*", reply_markup=categories_keyboard(), parse_mode="Markdown")

async def show_cart(message: Message):
    user_id = message.from_user.id
    cart = carts.get(user_id, {})
    text = get_cart_text(user_id)
    if cart:
        await message.answer(text, reply_markup=cart_keyboard(), parse_mode="Markdown")
    else:
        await message.answer(text, reply_markup=categories_keyboard(), parse_mode="Markdown")

async def show_orders(message: Message):
    user_id = message.from_user.id
    user_orders = {k: v for k, v in orders.items() if v["user_id"] == user_id}
    if not user_orders:
        await message.answer("📦 Sizda hech qanday buyurtma yo'q.")
        return
    text = "📦 *Buyurtmalaringiz:*\n\n"
    for order_id, order in list(user_orders.items())[-5:]:
        status_emoji = {"pending": "⏳", "processing": "🔄", "delivered": "✅", "cancelled": "❌"}.get(order["status"], "❓")
        text += f"🆔 #{order_id}\n📅 {order['date']}\n{status_emoji} Status: {order['status']}\n💰 {format_price(order['total'])}\n\n"
    await message.answer(text, parse_mode="Markdown")

async def show_info(message: Message):
    text = (
        "ℹ️ *FashionShop haqida:*\n\n"
        "🏪 Biz 2020-yildan beri faoliyat yuritamiz\n"
        "👗 10,000+ mahsulot assortimenti\n"
        "🚚 Toshkent bo'ylab yetkazib berish\n"
        "💯 100% sifat kafolati\n\n"
        "⏰ *Ish vaqti:* 9:00 - 21:00\n"
        "📍 *Manzil:* Toshkent, Chilonzor tumani\n"
    )
    await message.answer(text, parse_mode="Markdown")

async def show_contact(message: Message):
    text = (
        "📞 *Aloqa:*\n\n"
        "📱 Telefon: +998 90 123 45 67\n"
        "📱 Telefon: +998 91 234 56 78\n"
        "📧 Email: info@fashionshop.uz\n"
        "📸 Instagram: @fashionshop_uz\n"
        "💬 Telegram: @fashionshop_support\n"
    )
    await message.answer(text, parse_mode="Markdown")

async def show_sales(message: Message):
    text = (
        "⭐ *Aksiyalar va chegirmalar:*\n\n"
        "🔥 *Bugungi aksiya:*\nBarcha erkaklar kiyimlariga 20% chegirma!\n\n"
        "💥 *Haftalik offer:*\n2 ta mahsulot olsangiz - 3-chi 50% chegirma!\n\n"
        "🎁 *Yangi mijozlar uchun:*\nBirinchi buyurtmada 10% chegirma!\n\n"
        "📱 Promo-kod: `YANGI10`"
    )
    await message.answer(text, parse_mode="Markdown")


# --- CALLBACK HANDLERLAR ---
async def callback_category(callback: CallbackQuery):
    cat_id = callback.data.replace("cat_", "")
    cat = PRODUCTS.get(cat_id)
    if not cat:
        await callback.answer("Kategoriya topilmadi!")
        return
    await callback.message.edit_text(
        f"{cat['name']} *bo'limi:*\n\nMahsulotni tanlang:",
        reply_markup=products_keyboard(cat_id), parse_mode="Markdown"
    )
    await callback.answer()

async def callback_product(callback: CallbackQuery):
    item_id = callback.data.replace("prod_", "")
    item, cat_id = find_product(item_id)
    if not item:
        await callback.answer("Mahsulot topilmadi!")
        return
    text = (
        f"{item['emoji']} *{item['name']}*\n\n"
        f"💰 Narxi: *{format_price(item['price'])}*\n"
        f"📏 Mavjud razmерlar: {', '.join(item['sizes'])}\n\n"
        f"✅ Sifatli material\n🚚 Yetkazib berish mavjud\n↩️ Qaytarish mumkin (7 kun)"
    )
    await callback.message.edit_text(text, reply_markup=product_detail_keyboard(item_id, cat_id), parse_mode="Markdown")
    await callback.answer()

async def callback_add_to_cart(callback: CallbackQuery, state: FSMContext):
    item_id = callback.data.replace("add_", "")
    item, _ = find_product(item_id)
    if not item:
        await callback.answer("Mahsulot topilmadi!")
        return
    await state.set_state(OrderState.waiting_for_size)
    await state.update_data(pending_item_id=item_id)
    await callback.message.edit_text(
        f"📏 *{item['name']}* uchun razmer tanlang:",
        reply_markup=size_keyboard(item_id, item["sizes"]), parse_mode="Markdown"
    )
    await callback.answer()

async def callback_size_selected(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.replace("size_", "").rsplit("_", 1)
    item_id = parts[0]
    size = parts[1]
    item, _ = find_product(item_id)
    user_id = callback.from_user.id
    if user_id not in carts:
        carts[user_id] = {}
    cart_key = f"{item_id}_{size}"
    if cart_key in carts[user_id]:
        carts[user_id][cart_key]["quantity"] += 1
    else:
        carts[user_id][cart_key] = {"item_id": item_id, "size": size, "quantity": 1}
    await state.clear()
    save_data()
    total_items = sum(v["quantity"] for v in carts[user_id].values())
    await callback.message.edit_text(
        f"✅ *{item['name']}* (razmer: {size}) savatga qo'shildi!\n\n"
        f"🛒 Savatchada jami: *{total_items}* ta mahsulot",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Savatni ko'rish", callback_data="view_cart")],
            [InlineKeyboardButton(text="🛍 Xarid qilishni davom ettirish", callback_data="back_categories")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer("✅ Savatga qo'shildi!")

async def callback_view_cart(callback: CallbackQuery):
    user_id = callback.from_user.id
    cart = carts.get(user_id, {})
    text = get_cart_text(user_id)
    if cart:
        await callback.message.edit_text(text, reply_markup=cart_keyboard(), parse_mode="Markdown")
    else:
        await callback.message.edit_text(text, reply_markup=categories_keyboard(), parse_mode="Markdown")
    await callback.answer()

async def callback_clear_cart(callback: CallbackQuery):
    user_id = callback.from_user.id
    carts[user_id] = {}
    save_data()
    await callback.message.edit_text(
        "🗑 Savatcha tozalandi!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛍 Xarid qilish", callback_data="back_categories")]
        ])
    )
    await callback.answer("Savatcha tozalandi!")

async def callback_checkout(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    cart = carts.get(user_id, {})
    if not cart:
        await callback.answer("Savatchingiz bo'sh!", show_alert=True)
        return
    await state.set_state(OrderState.waiting_for_name)
    await callback.message.answer(
        "📝 *Buyurtma rasmiylashtirish*\n\nIsmingizni kiriting (To'liq ism):",
        parse_mode="Markdown", reply_markup=ReplyKeyboardRemove()
    )
    await callback.answer()

async def process_name(message: Message, state: FSMContext):
    await state.update_data(customer_name=message.text)
    await state.set_state(OrderState.waiting_for_phone)
    await message.answer(
        "📱 Telefon raqamingizni kiriting:\n(Masalan: +998901234567)",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📱 Raqamni yuborish", request_contact=True)]],
            resize_keyboard=True, one_time_keyboard=True
        )
    )

async def process_phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    await state.update_data(customer_phone=phone)
    await state.set_state(OrderState.waiting_for_address)
    await message.answer("📍 Yetkazib berish manzilingizni kiriting:", reply_markup=ReplyKeyboardRemove())

async def process_address(message: Message, state: FSMContext):
    global order_counter
    data = await state.get_data()
    user_id = message.from_user.id
    cart = carts.get(user_id, {})
    total = 0
    order_text = "📦 *Buyurtma tafsiloti:*\n\n"
    for item_key, item_data in cart.items():
        item, _ = find_product(item_data["item_id"])
        if item:
            subtotal = item["price"] * item_data["quantity"]
            total += subtotal
            order_text += f"• {item['name']} (razmer: {item_data['size']}) x{item_data['quantity']} = {format_price(subtotal)}\n"
    order_text += f"\n💰 *Jami: {format_price(total)}*\n"
    order_text += f"👤 Ism: {data['customer_name']}\n"
    order_text += f"📱 Tel: {data['customer_phone']}\n"
    order_text += f"📍 Manzil: {message.text}"
    await state.update_data(address=message.text, total=total, order_text=order_text)
    await message.answer(order_text + "\n\n✅ Buyurtmani tasdiqlaysizmi?", reply_markup=confirm_order_keyboard(), parse_mode="Markdown")

async def callback_confirm_order(callback: CallbackQuery, state: FSMContext):
    global order_counter
    data = await state.get_data()
    user_id = callback.from_user.id
    order_counter += 1
    order_id = order_counter
    from datetime import datetime
    orders[order_id] = {
        "user_id": user_id,
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "status": "pending",
        "total": data.get("total", 0),
        "customer_name": data.get("customer_name"),
        "customer_phone": data.get("customer_phone"),
        "address": data.get("address"),
        "cart": dict(carts.get(user_id, {}))
    }
    carts[user_id] = {}
    await state.clear()
    save_data()
    await callback.message.edit_text(
        f"🎉 *Buyurtmangiz qabul qilindi!*\n\n"
        f"🆔 Buyurtma raqami: *#{order_id}*\n"
        f"⏳ Holat: Ko'rib chiqilmoqda\n\n"
        f"📞 Tez orada operatorimiz siz bilan bog'lanadi.\n"
        f"Xarid uchun rahmat! 🛍",
        parse_mode="Markdown"
    )
    try:
        admin_text = (
            f"🔔 *YANGI BUYURTMA #{order_id}*\n\n"
            f"{data.get('order_text', '')}\n\n"
            f"👤 Telegram: @{callback.from_user.username or 'yoq'}\n"
            f"🆔 User ID: {user_id}"
        )
        await callback.bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Qabul qilindi", callback_data=f"order_accept_{order_id}")],
                [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"order_cancel_{order_id}")]
            ])
        )
    except Exception as e:
        logger.error(f"Admin ga xabar yuborishda xato: {e}")
    await callback.message.answer("Bosh menyuga qaytish:", reply_markup=main_keyboard())
    await callback.answer()

async def callback_cancel_order(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Buyurtma bekor qilindi.")
    await callback.message.answer("Bosh menyu:", reply_markup=main_keyboard())
    await callback.answer()

async def callback_cancel_size(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor qilindi. Kategoriyani tanlang:", reply_markup=categories_keyboard())
    await callback.answer()

async def callback_back_categories(callback: CallbackQuery):
    await callback.message.edit_text("🛍 *Kategoriyalarni tanlang:*", reply_markup=categories_keyboard(), parse_mode="Markdown")
    await callback.answer()

async def callback_back_main(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("🏠 Bosh menyu:", reply_markup=main_keyboard())
    await callback.answer()


# --- ADMIN HANDLERLAR ---
async def admin_statistics(message: Message):
    if message.from_user.id != ADMIN_ID or message.from_user.id not in verified_admins:
        return
    total_orders = len(orders)
    total_revenue = sum(o.get("total", 0) for o in orders.values())
    pending = sum(1 for o in orders.values() if o["status"] == "pending")
    text = (
        f"📊 *Statistika:*\n\n"
        f"📦 Jami buyurtmalar: *{total_orders}*\n"
        f"⏳ Kutilayotgan: *{pending}*\n"
        f"💰 Jami daromad: *{format_price(total_revenue)}*\n"
        f"👥 Foydalanuvchilar: *{len(set(o['user_id'] for o in orders.values()))}*"
    )
    await message.answer(text, parse_mode="Markdown")

async def admin_all_orders(message: Message):
    if message.from_user.id != ADMIN_ID or message.from_user.id not in verified_admins:
        return
    if not orders:
        await message.answer("Buyurtmalar yo'q.")
        return
    text = "📋 *Barcha buyurtmalar:*\n\n"
    for order_id, order in list(orders.items())[-10:]:
        text += f"#{order_id} | {order['date']} | {format_price(order['total'])} | {order['status']}\n"
    await message.answer(text, parse_mode="Markdown")

async def admin_broadcast_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID or message.from_user.id not in verified_admins:
        return
    await state.set_state(AdminState.waiting_for_broadcast)
    await message.answer("📣 Yubormoqchi bo'lgan xabaringizni kiriting:", reply_markup=ReplyKeyboardRemove())

async def admin_broadcast_send(message: Message, state: FSMContext):
    await state.clear()
    user_ids = set(o["user_id"] for o in orders.values())
    sent = 0
    for uid in user_ids:
        try:
            await message.bot.send_message(uid, f"📣 *FashionShop xabari:*\n\n{message.text}", parse_mode="Markdown")
            sent += 1
        except:
            pass
    await message.answer(f"✅ Xabar {sent} ta foydalanuvchiga yuborildi!", reply_markup=admin_keyboard())

async def admin_user_mode(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Foydalanuvchi rejimi:", reply_markup=main_keyboard())

async def admin_order_action(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Ruxsat yo'q!")
        return
    parts = callback.data.split("_")
    action = parts[1]
    order_id = int(parts[2])
    if order_id in orders:
        if action == "accept":
            orders[order_id]["status"] = "processing"
            status_text = "✅ Qabul qilindi"
            user_msg = f"🎉 #{order_id} buyurtmangiz qabul qilindi va tayyorlanmoqda!"
        else:
            orders[order_id]["status"] = "cancelled"
            status_text = "❌ Bekor qilindi"
            user_msg = f"😔 #{order_id} buyurtmangiz bekor qilindi. Iltimos qayta bog'laning."
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer(status_text)
        try:
            await callback.bot.send_message(orders[order_id]["user_id"], user_msg)
        except:
            pass


# ===================== BOTNI ISHGA TUSHIRISH =====================
async def main():
    load_data()
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_admin, Command("admin"))

    # ← MUHIM: Parol holati eng yuqorida ro'yxatdan o'tishi kerak
    dp.message.register(process_admin_password, AdminState.waiting_for_password)

    dp.message.register(show_catalog, F.text == "🛍 Katalog")
    dp.message.register(show_cart, F.text == "🛒 Savatcha")
    dp.message.register(show_orders, F.text == "📦 Buyurtmalarim")
    dp.message.register(show_info, F.text == "ℹ️ Ma'lumot")
    dp.message.register(show_contact, F.text == "📞 Aloqa")
    dp.message.register(show_sales, F.text == "⭐ Aksiyalar")

    dp.message.register(admin_statistics, F.text == "📊 Statistika")
    dp.message.register(admin_all_orders, F.text == "📋 Barcha buyurtmalar")
    dp.message.register(admin_broadcast_start, F.text == "📣 Xabar yuborish")
    dp.message.register(admin_user_mode, F.text == "🔙 Foydalanuvchi rejimi")
    dp.message.register(admin_broadcast_send, AdminState.waiting_for_broadcast)

    dp.message.register(process_name, OrderState.waiting_for_name)
    dp.message.register(process_phone, OrderState.waiting_for_phone)
    dp.message.register(process_address, OrderState.waiting_for_address)

    dp.callback_query.register(callback_category, F.data.startswith("cat_"))
    dp.callback_query.register(callback_product, F.data.startswith("prod_"))
    dp.callback_query.register(callback_add_to_cart, F.data.startswith("add_"))
    dp.callback_query.register(callback_size_selected, F.data.startswith("size_"))
    dp.callback_query.register(callback_view_cart, F.data == "view_cart")
    dp.callback_query.register(callback_clear_cart, F.data == "clear_cart")
    dp.callback_query.register(callback_checkout, F.data == "checkout")
    dp.callback_query.register(callback_confirm_order, F.data == "confirm_order")
    dp.callback_query.register(callback_cancel_order, F.data == "cancel_order")
    dp.callback_query.register(callback_cancel_size, F.data == "cancel_size")
    dp.callback_query.register(callback_back_categories, F.data == "back_categories")
    dp.callback_query.register(callback_back_main, F.data == "back_main")
    dp.callback_query.register(admin_order_action, F.data.startswith("order_"))

    logger.info("🚀 Bot ishga tushdi!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
