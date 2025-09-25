from aiogram.fsm.context import FSMContext
import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
import secrets
from aiogram.filters import CommandStart
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, FSInputFile, InputMediaPhoto
from aiogram.exceptions import TelegramBadRequest
from database import SessionLocal, User, Deal, init_db

BOT_TOKEN = "8229893992:AAH1zr7PTajg7uKdPlSB1kI0k3-om-6i8Tc"
PHOTO_PATH = "photo_2025-09-12_18-04-44.jpg"

WELCOME_TEXT = (
    "Добро пожаловать в ELF OTC – надежный P2P-гарант\n\n"
    "💼 Покупайте и продавайте всё, что угодно – безопасно!\n"
    "От Telegram-подарков и NFT до токенов и фиата сделки проходят легко и без риска.\n\n"
    "🔹 Удобное управление кошельками\n"
    "🔹 Реферальная система\n"
    "🔹 Безопасные сделки с гарантией\n\n"
    "Выберите нужный раздел ниже:"
)

class WalletManagement(StatesGroup):
    enter_ton_wallet = State()
    enter_card_number = State()

class DealCreation(StatesGroup):
    enter_amount = State()
    enter_description = State()

def get_main_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Управление реквизитами", callback_data="add_wallet")],
        [InlineKeyboardButton(text="📄 Создать сделку", callback_data="create_deal")],
        [InlineKeyboardButton(text="🧷 Реферальная ссылка", callback_data="referral_link")],
        [InlineKeyboardButton(text="🌐 Change language", callback_data="change_language")]
    ])
    return keyboard

def get_language_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang_en")],
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang_ru")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ])
    return keyboard

def get_payment_method_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🪙 TON кошелек", callback_data="payment_ton")],
        [InlineKeyboardButton(text="💳 Банковская карта", callback_data="payment_card")],
        [InlineKeyboardButton(text="🌟 Telegram Stars", callback_data="payment_stars")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ])
    return keyboard

def get_deal_amount_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💱 Изменить валюту", callback_data="change_currency"),
            InlineKeyboardButton(text="⬅️ Назад", callback_data="create_deal")
        ]
    ])
    return keyboard

def get_currency_selection_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="RUB 🇷🇺", callback_data="set_currency_RUB"),
            InlineKeyboardButton(text="UAH 🇺🇦", callback_data="set_currency_UAH")
        ],
        [
            InlineKeyboardButton(text="KZT 🇰🇿", callback_data="set_currency_KZT"),
            InlineKeyboardButton(text="BYN 🇧🇾", callback_data="set_currency_BYN")
        ],
        [
            InlineKeyboardButton(text="UZS 🇺🇿", callback_data="set_currency_UZS"),
            InlineKeyboardButton(text="KGS 🇰🇬", callback_data="set_currency_KGS")
        ],
        [
            InlineKeyboardButton(text="AZN 🇦🇿", callback_data="set_currency_AZN"),
            InlineKeyboardButton(text="TON 💎", callback_data="set_currency_TON")
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="create_deal")]
    ])
    return keyboard

def get_back_to_main_menu_button():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⬅️ В главное меню", callback_data="main_menu")
        ]
    ])
    return keyboard

def get_buyer_deal_menu(deal_code: str, tonkeeper_link: str = None):
    buttons = []
    if tonkeeper_link:
        buttons.append([
            InlineKeyboardButton(text="Открыть в Tonkeeper", url=tonkeeper_link)
        ])
    buttons.extend([
        [
            InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"confirm_payment_{deal_code}")
        ],
        [
            InlineKeyboardButton(text="❌ Выйти из сделки", callback_data=f"leave_deal_{deal_code}")
        ]
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_seller_gift_sent_menu(deal_code: str):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📤 Я отправил подарок", callback_data=f"gift_sent_{deal_code}")
        ]
    ])
    return keyboard

def get_wallet_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🪙 Добавить/изменить TON-кошелек", callback_data="edit_ton_wallet")],
        [InlineKeyboardButton(text="💳 Добавить/изменить карту", callback_data="edit_card")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ])
    return keyboard

dp = Dispatcher()

@dp.callback_query(F.data.startswith("confirm_payment_"))
async def confirm_payment_handler(callback: types.CallbackQuery, bot: Bot):
    deal_code = callback.data.split("_")[2]
    db = SessionLocal()
    try:
        deal = db.query(Deal).filter(Deal.deal_code == deal_code).first()

        if not deal:
            await callback.answer("❌ Сделка с таким кодом не найдена.", show_alert=True)
            return

        if deal.buyer_id != callback.from_user.id:
            await callback.answer("❌ Это не ваша сделка.", show_alert=True)
            return

        if deal.status != 'awaiting_buyer':
            await callback.answer("❌ Эту сделку уже нельзя оплатить.", show_alert=True)
            return

        deal.status = 'pending_confirmation'
        db.commit()

        buyer_caption = (
            f"✅ Оплата подтверждена для сделки #{deal.deal_code}\n\n"
            "Пожалуйста, дождитесь подтверждения администратора получения товара."
        )
        media = InputMediaPhoto(media=FSInputFile(PHOTO_PATH), caption=buyer_caption)
        await callback.message.edit_media(media=media, reply_markup=None)

        seller_caption = (
            f"✅ Покупатель подтвердил оплату по сделке #{deal.deal_code}\n\n"
            f"📜 Описание: {deal.description}\n"
            f"👤 Отправьте товар/услугу Покупателю: @{callback.from_user.username}\n\n"
            "После отправки, нажмите кнопку ниже."
        )
        await bot.send_photo(
            chat_id=deal.seller_id,
            photo=FSInputFile(PHOTO_PATH),
            caption=seller_caption,
            reply_markup=get_seller_gift_sent_menu(deal.deal_code)
        )
        await callback.answer()

    finally:
        db.close()

@dp.callback_query(F.data.startswith("gift_sent_"))
async def gift_sent_handler(callback: types.CallbackQuery):
    deal_code = callback.data.split("_")[2]
    db = SessionLocal()
    try:
        deal = db.query(Deal).filter(Deal.deal_code == deal_code).first()
        if not deal or deal.seller_id != callback.from_user.id:
            await callback.answer("❌ Ошибка: сделка не найдена или у вас нет доступа.", show_alert=True)
            return

        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer(
            "Спасибо! Ожидайте подтверждения от администратора.",
            show_alert=True
        )
    finally:
        db.close()

@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.user_id == user_id).first()
        if not db_user:
            db_user = User(user_id=user_id, username=message.from_user.username)
            db.add(db_user)
        else:
            db_user.username = message.from_user.username
        db.commit()

        args = message.text.split()
        if len(args) > 1:
            deal_code = args[1]
            deal = db.query(Deal).filter(Deal.deal_code == deal_code).first()
            if deal and deal.status == 'awaiting_buyer':
                seller = db.query(User).filter(User.user_id == deal.seller_id).first()

                # Проверяем, указал ли продавец реквизиты для данного типа сделки
                if deal.payment_method == 'ton' and not (seller and seller.ton_wallet):
                    await message.answer("❌ Ошибка: Продавец не указал TON-кошелек для оплаты.")
                    return
                elif deal.payment_method == 'card' and not (seller and seller.card_number):
                    await message.answer("❌ Ошибка: Продавец не указал номер карты для оплаты.")
                    return
                elif not seller:
                    await message.answer("❌ Ошибка: Продавец не найден.")
                    return

                deal.buyer_id = user_id

                # Формируем сообщение и кнопки в зависимости от метода оплаты
                caption = ""
                reply_markup = None
                base_caption = (
                    f"💳 Информация о сделке #{deal.deal_code}\n\n"
                    f"👤 Вы покупатель в сделке.\n"
                    f"📌 Продавец: @{seller.username} ({seller.user_id})\n"
                    f"• Успешные сделки: 0\n\n"
                    f"• Вы покупаете: {deal.description}\n\n"
                )

                if deal.payment_method == 'ton':
                    amount = deal.amount / 100.0
                    currency = deal.currency or "TON" # Используем сохраненную валюту или TON по умолчанию
                    tonkeeper_link = f"ton://transfer/{seller.ton_wallet}?amount={int(amount * 1_000_000_000)}&text={deal.deal_code}"
                    caption = base_caption + (
                        f"🏦 Адрес для оплаты:\n`{seller.ton_wallet}`\n\n"
                        f"💰 Сумма к оплате: {amount} {currency}\n"
                        f"📝 Комментарий к платежу(мемо): `{deal.deal_code}`\n\n"
                        f"⚠️ Пожалуйста, убедитесь в правильности данных перед оплатой. Комментарий(мемо) обязателен!"
                    )
                    reply_markup = get_buyer_deal_menu(deal.deal_code, tonkeeper_link)
                elif deal.payment_method == 'card':
                    amount = deal.amount / 100.0
                    currency = deal.currency or "RUB" # Используем сохраненную валюту или RUB по умолчанию
                    caption = base_caption + (
                        f"🏦 Номер карты для оплаты:\n`{seller.card_number}`\n\n"
                        f"💰 Сумма к оплате: {amount} {currency}\n\n"
                        f"⚠️ Пожалуйста, убедитесь в правильности данных перед оплатой. После оплаты нажмите 'Подтвердить оплату'."
                    )
                    reply_markup = get_buyer_deal_menu(deal.deal_code)

                db.commit()
                await message.answer_photo(
                    photo=FSInputFile(PHOTO_PATH),
                    caption=caption,
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
                return
            elif deal:
                await message.answer("Эта сделка уже занята или завершена.")
                return
            else:
                await message.answer("❌ Сделка с таким кодом не найдена.")
                return

    finally:
        db.close()

    # Показываем главное меню, если не было deeplink
    await message.answer_photo(
        photo=FSInputFile(PHOTO_PATH),
        caption=WELCOME_TEXT,
        reply_markup=get_main_menu()
    )

@dp.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: types.CallbackQuery):
    media = InputMediaPhoto(media=FSInputFile(PHOTO_PATH), caption=WELCOME_TEXT)
    await callback.message.edit_media(
        media=media,
        reply_markup=get_main_menu()
    )
    await callback.answer()

@dp.callback_query(F.data == "add_wallet")
async def add_wallet_handler(callback: types.CallbackQuery):
    caption = (
        "📥 Управление реквизитами\n\n"
        "Используйте кнопки ниже чтобы добавить/изменить реквизиты👇"
    )
    media = InputMediaPhoto(media=FSInputFile(PHOTO_PATH), caption=caption)
    await callback.message.edit_media(
        media=media,
        reply_markup=get_wallet_menu()
    )
    await callback.answer()

@dp.callback_query(F.data == "edit_ton_wallet")
async def edit_ton_wallet_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(WalletManagement.enter_ton_wallet)
    await state.update_data(message_to_edit=callback.message.message_id)

    caption = ""
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.user_id == callback.from_user.id).first()
        if db_user and db_user.ton_wallet:
            caption = f"Ваш текущий кошелек TON:\n`{db_user.ton_wallet}`\n\nВведите новый адрес, если хотите его изменить."
        else:
            caption = "Введите адрес вашего TON кошелька:"
    finally:
        db.close()

    media = InputMediaPhoto(media=FSInputFile(PHOTO_PATH), caption=caption, parse_mode="Markdown")
    await callback.message.edit_media(media=media)
    await callback.answer()

@dp.message(WalletManagement.enter_ton_wallet)
async def process_ton_wallet(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    message_id_to_edit = data.get("message_to_edit")
    await state.clear()

    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.user_id == message.from_user.id).first()
        if db_user:
            db_user.ton_wallet = message.text
            db.commit()
    finally:
        db.close()

    await message.delete()

    caption = "✅ Ваш TON кошелек сохранен.\n\n📥 Управление реквизитами\n\nИспользуйте кнопки ниже чтобы добавить/изменить реквизиты👇"
    media = InputMediaPhoto(media=FSInputFile(PHOTO_PATH), caption=caption)
    if message_id_to_edit:
        await bot.edit_message_media(chat_id=message.chat.id, message_id=message_id_to_edit, media=media, reply_markup=get_wallet_menu())

@dp.callback_query(F.data == "edit_card")
async def edit_card_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(WalletManagement.enter_card_number)
    await state.update_data(message_to_edit=callback.message.message_id)
    media = InputMediaPhoto(media=FSInputFile(PHOTO_PATH), caption="Введите номер вашей банковской карты:")
    await callback.message.edit_media(media=media)
    await callback.answer()

@dp.message(WalletManagement.enter_card_number)
async def process_card_number(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    message_id_to_edit = data.get("message_to_edit")
    await state.clear()

    await message.delete()

    caption = ""
    db = SessionLocal()
    try:
        if message.text and message.text.replace(" ", "").isdigit():
            db_user = db.query(User).filter(User.user_id == message.from_user.id).first()
            if db_user:
                db_user.card_number = message.text
                db.commit()
            caption = "✅ Номер вашей карты сохранен.\n\n📥 Управление реквизитами\n\nИспользуйте кнопки ниже чтобы добавить/изменить реквизиты👇"
        else:
            caption = "❌ Неверный формат номера карты. Попробуйте еще раз.\n\n📥 Управление реквизитами\n\nИспользуйте кнопки ниже чтобы добавить/изменить реквизиты👇"
    finally:
        db.close()

    media = InputMediaPhoto(media=FSInputFile(PHOTO_PATH), caption=caption)
    if message_id_to_edit:
        await bot.edit_message_media(chat_id=message.chat.id, message_id=message_id_to_edit, media=media, reply_markup=get_wallet_menu())

@dp.callback_query(F.data == "create_deal")
async def create_deal_handler(callback: types.CallbackQuery):
    media = InputMediaPhoto(
        media=FSInputFile(PHOTO_PATH),
        caption="💰Выберите метод получения оплаты:"
    )
    await callback.message.edit_media(
        media=media,
        reply_markup=get_payment_method_menu()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("payment_"))
async def handle_payment_method(callback: types.CallbackQuery, state: FSMContext):
    payment_method = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.user_id == user_id).first()
        if not db_user:
            await callback.answer("Произошла ошибка. Пожалуйста, перезапустите бота: /start", show_alert=True)
            return

        if payment_method == "card":
            if not db_user.card_number:
                back_button = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
                ])
                media = InputMediaPhoto(
                    media=FSInputFile(PHOTO_PATH),
                    caption="❌ Сначала добавьте ваш номер карты перед созданием сделки."
                )
                await callback.message.edit_media(media=media, reply_markup=back_button)
                await callback.answer()
                return
        elif payment_method == "ton":
            if not db_user.ton_wallet:
                back_button = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
                ])
                media = InputMediaPhoto(
                    media=FSInputFile(PHOTO_PATH),
                    caption="❌ Сначала добавьте ваш TON-кошелек перед созданием сделки."
                )
                await callback.message.edit_media(media=media, reply_markup=back_button)
                await callback.answer()
                return
    finally:
        db.close()

    await state.set_state(DealCreation.enter_amount)
    
    currency_name = ""
    if payment_method == "ton":
        currency_name = "TON"
    elif payment_method == "card":
        currency_name = "RUB"
    elif payment_method == "stars":
        currency_name = "Stars"

    await state.update_data(currency=currency_name, message_to_edit=callback.message.message_id)

    caption = (
        f"💼 Создание сделки\n\n"
        f"Введите сумму {currency_name} сделки в формате: 100.5"
    )
    media = InputMediaPhoto(
        media=FSInputFile(PHOTO_PATH),
        caption=caption
    )
    await callback.message.edit_media(media=media, reply_markup=get_deal_amount_menu())
    await callback.answer()

@dp.message(DealCreation.enter_amount)
async def process_deal_amount(message: Message, state: FSMContext, bot: Bot):
    try:
        amount = float(message.text.replace(',', '.'))
    except ValueError:
        await message.delete()
        return

    await state.update_data(amount=amount)
    data = await state.get_data()
    currency = data.get("currency", "")
    message_id_to_edit = data.get("message_to_edit")

    await message.delete()
    await state.set_state(DealCreation.enter_description)

    caption = (
        f"📝 Укажите, что вы предлагаете в этой сделке за {amount} {currency}:\n\n"
        "Пример: 10 Кепок и Пепе..."
    )
    media = InputMediaPhoto(media=FSInputFile(PHOTO_PATH), caption=caption)
    if message_id_to_edit:
        await bot.edit_message_media(chat_id=message.chat.id, message_id=message_id_to_edit, media=media, reply_markup=None)

@dp.message(DealCreation.enter_description)
async def process_deal_description(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    message_id_to_edit = data.get("message_to_edit")
    amount = data.get("amount")
    currency = data.get("currency")
    payment_method = data.get("payment_method")
    description = message.text

    await state.clear()
    await message.delete()

    deal_code = secrets.token_urlsafe(8)

    db = SessionLocal()
    try:
        new_deal = Deal(
            seller_id=message.from_user.id,
            amount=int(amount * 100),
            description=description,
            currency=currency,
            payment_method=payment_method,
            deal_code=deal_code
        )
        db.add(new_deal)
        db.commit()
    finally:
        db.close()

    bot_info = await bot.get_me()
    deal_link = f"https://t.me/{bot_info.username}?start={deal_code}"

    caption = (
        f"✅ Сделка успешно создана!\n\n"
        f"💰 Сумма: {amount} {currency}\n"
        f"📜 Описание: {description}\n"
        f"🔗 Ссылка для покупателя: `{deal_link}`"
    )

    media = InputMediaPhoto(media=FSInputFile(PHOTO_PATH), caption=caption, parse_mode="Markdown")
    if message_id_to_edit:
        await bot.edit_message_media(chat_id=message.chat.id, message_id=message_id_to_edit, media=media, reply_markup=get_back_to_main_menu_button())

@dp.callback_query(F.data == "change_currency")
async def change_currency_handler(callback: types.CallbackQuery):
    caption = "💱 Выберите валюту для сделки:"
    media = InputMediaPhoto(
        media=FSInputFile(PHOTO_PATH),
        caption=caption
    )
    await callback.message.edit_media(media=media, reply_markup=get_currency_selection_menu())
    await callback.answer()

@dp.callback_query(F.data.startswith("set_currency_"))
async def set_currency_handler(callback: types.CallbackQuery, state: FSMContext):
    currency_name = callback.data.split("_")[2]
    await state.update_data(currency=currency_name)

    caption = (
        f"💼 Создание сделки\n\n"
        f"Введите сумму {currency_name} сделки в формате: 100.5"
    )
    media = InputMediaPhoto(
        media=FSInputFile(PHOTO_PATH),
        caption=caption
    )
    await callback.message.edit_media(media=media, reply_markup=get_deal_amount_menu())
    await callback.answer()
@dp.callback_query(F.data == "referral_link")
async def referral_link_handler(callback: types.CallbackQuery):
    await callback.answer("Этот раздел в разработке.", show_alert=True)

@dp.callback_query(F.data == "change_language")
async def change_language_handler(callback: types.CallbackQuery):
    media = InputMediaPhoto(media=FSInputFile(PHOTO_PATH), caption="Please select your language:")
    await callback.message.edit_media(
        media=media,
        reply_markup=get_language_menu()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("set_lang_"))
async def set_language_handler(callback: types.CallbackQuery):
    lang = callback.data.split("_")[2]
    lang_name = "Английский" if lang == "en" else "Русский"
    await callback.answer(f"Язык изменен на: {lang_name}", show_alert=True)

    media = InputMediaPhoto(media=FSInputFile(PHOTO_PATH), caption=WELCOME_TEXT)
    await callback.message.edit_media(
        media=media,
        reply_markup=get_main_menu()
    )

async def main():
    init_db()
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
