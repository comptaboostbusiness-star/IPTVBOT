import os
import random
import logging
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
from io import BytesIO

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics import renderPDF

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

(
    PACK_SELECTION,
    FIRST_NAME,
    LAST_NAME,
    EMAIL,
    PHONE,
    M3U_LINK,
    CONFIRMATION,
) = range(7)

PACKS = {
    "1mois": {"label": "1 mois", "price": "10$", "price_pln": "10 USD", "days": 30},
    "3mois": {"label": "3 mois", "price": "20$", "price_pln": "20 USD", "days": 90},
    "6mois": {"label": "6 mois", "price": "30$", "price_pln": "30 USD", "days": 180},
    "1an":   {"label": "1 an ⭐", "price": "37$", "price_pln": "37 USD", "days": 365},
}

COLOR_PINK    = colors.HexColor("#ff00aa")
COLOR_PURPLE  = colors.HexColor("#9c27ff")
COLOR_PURPLE2 = colors.HexColor("#7b2cff")
COLOR_NAVY    = colors.HexColor("#0d1b3e")
COLOR_DARK    = colors.HexColor("#1a1a2e")
COLOR_WHITE   = colors.white
COLOR_LIGHT   = colors.HexColor("#f8f5ff")
COLOR_GREY    = colors.HexColor("#e8e0f5")
COLOR_MID     = colors.HexColor("#c9b8f0")
COLOR_ACCENT  = colors.HexColor("#ff00aa")
COLOR_SUCCESS = colors.HexColor("#7b2cff")


def parse_m3u(url: str) -> dict | None:
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        username = params.get("username", [None])[0]
        password = params.get("password", [None])[0]
        host = parsed.hostname
        port = str(parsed.port) if parsed.port else "80"
        if not all([username, password, host]):
            return None
        return {
            "username": username,
            "password": password,
            "host": host,
            "port": port,
        }
    except Exception:
        return None


def generate_invoice_number() -> str:
    today = datetime.now().strftime("%Y%m%d")
    rand = random.randint(1000, 9999)
    return f"ST-{today}-{rand}"


def draw_gradient_rect(canvas_obj, x, y, width, height, color1, color2, steps=40):
    r1, g1, b1 = color1.red, color1.green, color1.blue
    r2, g2, b2 = color2.red, color2.green, color2.blue
    step_h = height / steps
    for i in range(steps):
        t = i / steps
        r = r1 + (r2 - r1) * t
        g = g1 + (g2 - g1) * t
        b = b1 + (b2 - b1) * t
        canvas_obj.setFillColorRGB(r, g, b)
        canvas_obj.rect(x, y + i * step_h, width, step_h + 0.5, fill=1, stroke=0)


def generate_invoice_pdf(data: dict) -> BytesIO:
    buffer = BytesIO()
    page_w, page_h = A4
    margin = 18 * mm

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=8 * mm,
        bottomMargin=12 * mm,
    )

    pack_info = PACKS[data["pack_key"]]
    invoice_number = generate_invoice_number()
    activation_date = datetime.now()
    expiry_date = activation_date + timedelta(days=pack_info["days"])
    activation_str = activation_date.strftime("%d.%m.%Y")
    expiry_str = expiry_date.strftime("%d.%m.%Y")
    issue_date_str = activation_date.strftime("%d.%m.%Y")

    usable_width = page_w - 2 * margin

    def make_style(name, font="Helvetica", size=10, color=COLOR_NAVY,
                   align=TA_LEFT, bold=False, leading=None):
        f = "Helvetica-Bold" if bold else font
        return ParagraphStyle(
            name=name,
            fontName=f,
            fontSize=size,
            textColor=color,
            alignment=align,
            leading=leading or (size * 1.35),
            spaceAfter=0,
            spaceBefore=0,
        )

    s_title      = make_style("title",      size=22, bold=True,  color=COLOR_WHITE, align=TA_CENTER)
    s_subtitle   = make_style("subtitle",   size=11, bold=False, color=colors.HexColor("#e8d5ff"), align=TA_CENTER)
    s_inv_label  = make_style("inv_label",  size=9,  bold=False, color=colors.HexColor("#c9b8f0"), align=TA_RIGHT)
    s_inv_val    = make_style("inv_val",    size=9,  bold=True,  color=COLOR_WHITE, align=TA_RIGHT)
    s_section    = make_style("section",    size=11, bold=True,  color=COLOR_WHITE)
    s_label      = make_style("label",      size=9,  bold=False, color=colors.HexColor("#7b5ea7"))
    s_value      = make_style("value",      size=10, bold=True,  color=COLOR_NAVY)
    s_feat       = make_style("feat",       size=9,  bold=False, color=COLOR_NAVY)
    s_footer_h   = make_style("footer_h",  size=10, bold=True,  color=COLOR_PURPLE, align=TA_CENTER)
    s_footer_s   = make_style("footer_s",  size=8,  bold=False, color=colors.HexColor("#9c7ec4"), align=TA_CENTER)
    s_pack_name  = make_style("pack_name", size=13, bold=True,  color=COLOR_WHITE, align=TA_CENTER)
    s_pack_price = make_style("pack_price",size=22, bold=True,  color=COLOR_WHITE, align=TA_CENTER)
    s_pack_sub   = make_style("pack_sub",  size=9,  bold=False, color=colors.HexColor("#e8d5ff"), align=TA_CENTER)
    s_access_l   = make_style("access_l",  size=8,  bold=False, color=colors.HexColor("#9c7ec4"))
    s_access_v   = make_style("access_v",  size=9,  bold=True,  color=COLOR_NAVY)

    story = []

    HEADER_H = 46 * mm

    class HeaderCanvas:
        pass

    def header_flowable():
        class _Header(object):
            def __init__(self):
                self.width = usable_width
                self.height = HEADER_H
                self._fixedWidth = usable_width
                self._fixedHeight = HEADER_H

            def wrap(self, aw, ah):
                return self.width, self.height

            def drawOn(self, canvas_obj, x, y):
                canvas_obj.saveState()
                p = canvas_obj.beginPath()
                r = 8 * mm
                rx, ry, rw, rh = x, y, self.width, self.height
                p.moveTo(rx + r, ry)
                p.lineTo(rx + rw - r, ry)
                p.arcTo(rx + rw - 2*r, ry, rx + rw, ry + 2*r, -90, 90)
                p.lineTo(rx + rw, ry + rh - r)
                p.arcTo(rx + rw - 2*r, ry + rh - 2*r, rx + rw, ry + rh, 0, 90)
                p.lineTo(rx + r, ry + rh)
                p.arcTo(rx, ry + rh - 2*r, rx + 2*r, ry + rh, 90, 90)
                p.lineTo(rx, ry + r)
                p.arcTo(rx, ry, rx + 2*r, ry + 2*r, 180, 90)
                p.close()
                canvas_obj.clipPath(p, stroke=0, fill=0)

                steps = 60
                c1 = COLOR_PURPLE2
                c2 = COLOR_PINK
                for i in range(steps):
                    t = i / steps
                    r_c = c1.red + (c2.red - c1.red) * t
                    g_c = c1.green + (c2.green - c1.green) * t
                    b_c = c1.blue + (c2.blue - c1.blue) * t
                    canvas_obj.setFillColorRGB(r_c, g_c, b_c)
                    canvas_obj.rect(rx + t * rw, ry, rw / steps + 1, rh, fill=1, stroke=0)

                canvas_obj.restoreState()
                canvas_obj.saveState()

                canvas_obj.setFillColor(colors.HexColor("#ffffff20"))
                for cx_, cy_, cr_ in [
                    (rx + rw * 0.85, ry + rh * 0.3, 28 * mm),
                    (rx + rw * 0.05, ry + rh * 0.8, 18 * mm),
                ]:
                    canvas_obj.circle(cx_, cy_, cr_, fill=1, stroke=0)

                title_y = ry + rh - 13 * mm
                canvas_obj.setFont("Helvetica-Bold", 20)
                canvas_obj.setFillColor(COLOR_WHITE)
                canvas_obj.drawCentredString(rx + rw / 2, title_y, "Smarts-Telewizja.pl")

                canvas_obj.setFont("Helvetica", 10)
                canvas_obj.setFillColor(colors.HexColor("#e8d5ff"))
                canvas_obj.drawCentredString(rx + rw / 2, title_y - 8 * mm,
                                             "Faktura / Rachunek")

                line_y = title_y - 11 * mm
                canvas_obj.setStrokeColor(colors.HexColor("#ffffff40"))
                canvas_obj.setLineWidth(0.5)
                canvas_obj.line(rx + 20 * mm, line_y, rx + rw - 20 * mm, line_y)

                lx = rx + 8 * mm
                ry2 = ry + 6 * mm
                canvas_obj.setFont("Helvetica", 7.5)
                canvas_obj.setFillColor(colors.HexColor("#c9b8f0"))
                canvas_obj.drawRightString(rx + rw - 8 * mm, ry2 + 8 * mm, "Numer faktury:")
                canvas_obj.drawRightString(rx + rw - 8 * mm, ry2, "Data wystawienia:")
                canvas_obj.setFont("Helvetica-Bold", 8)
                canvas_obj.setFillColor(COLOR_WHITE)
                canvas_obj.drawRightString(rx + rw - 8 * mm + 20 * mm,
                                           ry2 + 8 * mm, invoice_number)
                canvas_obj.drawRightString(rx + rw - 8 * mm + 20 * mm,
                                           ry2, issue_date_str)

                canvas_obj.restoreState()

        return _Header()

    story.append(header_flowable())
    story.append(Spacer(1, 5 * mm))

    def card(inner_table, bg=COLOR_LIGHT, radius=4 * mm, padding=4 * mm):
        class _Card(object):
            def __init__(self):
                self._table = inner_table
                self.bg = bg
                self.radius = radius
                self._w = None
                self._h = None

            def wrap(self, aw, ah):
                w, h = self._table.wrap(aw - 2 * padding, ah)
                self._w = aw
                self._h = h + 2 * padding
                return aw, self._h

            def drawOn(self, canvas_obj, x, y):
                canvas_obj.saveState()
                canvas_obj.setFillColor(self.bg)
                canvas_obj.roundRect(x, y, self._w, self._h,
                                     self.radius, fill=1, stroke=0)
                canvas_obj.setStrokeColor(COLOR_MID)
                canvas_obj.setLineWidth(0.5)
                canvas_obj.roundRect(x, y, self._w, self._h,
                                     self.radius, fill=0, stroke=1)
                canvas_obj.restoreState()
                self._table.drawOn(canvas_obj, x + padding, y + padding)

        return _Card()

    def section_header(title: str, icon: str = ""):
        text = f"{icon}  {title}" if icon else title
        data_ = [[Paragraph(text, s_section)]]
        t = Table(data_, colWidths=[usable_width - 8 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_PURPLE),
            ("ROWPADDING", (0, 0), (-1, -1), [4 * mm, 3 * mm, 4 * mm, 3 * mm]),
            ("ROUNDEDCORNERS", [3 * mm]),
        ]))
        return t

    client_data = [
        [Paragraph("Imię", s_label),       Paragraph(data["first_name"], s_value),
         Paragraph("Nazwisko", s_label),    Paragraph(data["last_name"], s_value)],
        [Paragraph("Email", s_label),       Paragraph(data["email"], s_value),
         Paragraph("Telefon", s_label),     Paragraph(data["phone"], s_value)],
    ]
    col_w = usable_width / 4
    client_table = Table(client_data, colWidths=[col_w] * 4)
    client_table.setStyle(TableStyle([
        ("VALIGN",      (0, 0), (-1, -1), "TOP"),
        ("ROWPADDING",  (0, 0), (-1, -1), [2 * mm, 1.5 * mm, 2 * mm, 1.5 * mm]),
        ("LINEBELOW",   (0, 0), (-1, 0),  0.3, COLOR_GREY),
    ]))

    story.append(section_header("Dane klienta", ""))
    story.append(Spacer(1, 1.5 * mm))
    story.append(card(client_table))
    story.append(Spacer(1, 4 * mm))

    pack_label_pl = {
        "1mois": "1 miesiąc",
        "3mois": "3 miesiące",
        "6mois": "6 miesięcy",
        "1an":   "1 rok",
    }[data["pack_key"]]

    class PackCard(object):
        def __init__(self):
            self._w = None
            self._h = 36 * mm

        def wrap(self, aw, ah):
            self._w = aw
            return aw, self._h

        def drawOn(self, canvas_obj, x, y):
            canvas_obj.saveState()
            steps = 50
            c1, c2 = COLOR_PURPLE2, COLOR_PINK
            for i in range(steps):
                t = i / steps
                r_c = c1.red + (c2.red - c1.red) * t
                g_c = c1.green + (c2.green - c1.green) * t
                b_c = c1.blue + (c2.blue - c1.blue) * t
                canvas_obj.setFillColorRGB(r_c, g_c, b_c)
                canvas_obj.rect(x + t * self._w, y, self._w / steps + 1,
                                self._h, fill=1, stroke=0)

            canvas_obj.setStrokeColor(colors.HexColor("#ffffff50"))
            canvas_obj.setLineWidth(1)
            canvas_obj.roundRect(x, y, self._w, self._h, 4 * mm, fill=0, stroke=1)

            cx = x + self._w / 2
            canvas_obj.setFillColor(COLOR_WHITE)
            canvas_obj.setFont("Helvetica-Bold", 13)
            canvas_obj.drawCentredString(cx, y + self._h - 10 * mm,
                                         f"Pakiet: {pack_label_pl}")
            canvas_obj.setFont("Helvetica-Bold", 24)
            canvas_obj.drawCentredString(cx, y + self._h - 21 * mm,
                                         pack_info["price"])
            canvas_obj.setFont("Helvetica", 8.5)
            canvas_obj.setFillColor(colors.HexColor("#e8d5ff"))
            canvas_obj.drawCentredString(cx, y + self._h - 29 * mm,
                                         f"Aktywacja: {activation_str}   |   "
                                         f"Wygaśnięcie: {expiry_str}")
            canvas_obj.restoreState()

    story.append(section_header("Szczegóły subskrypcji", ""))
    story.append(Spacer(1, 1.5 * mm))
    story.append(PackCard())
    story.append(Spacer(1, 4 * mm))

    m3u = data["m3u"]

    def mono_style():
        return ParagraphStyle(
            "mono", fontName="Courier-Bold", fontSize=9,
            textColor=COLOR_NAVY, alignment=TA_LEFT, leading=12
        )

    access_data = [
        [Paragraph("Host", s_access_l),     Paragraph(m3u["host"], mono_style()),
         Paragraph("Port", s_access_l),      Paragraph(m3u["port"], mono_style())],
        [Paragraph("Nazwa użytkownika", s_access_l), Paragraph(m3u["username"], mono_style()),
         Paragraph("Hasło", s_access_l),     Paragraph(m3u["password"], mono_style())],
    ]
    col_w2 = usable_width / 4
    access_table = Table(access_data, colWidths=[col_w2 * 0.7, col_w2 * 1.3,
                                                  col_w2 * 0.7, col_w2 * 1.3])
    access_table.setStyle(TableStyle([
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("ROWPADDING",  (0, 0), (-1, -1), [2 * mm, 1.5 * mm, 2 * mm, 1.5 * mm]),
        ("LINEBELOW",   (0, 0), (-1, 0),  0.3, COLOR_GREY),
        ("BACKGROUND",  (0, 0), (-1, -1), colors.HexColor("#f0ebff")),
    ]))

    story.append(section_header("Dane dostępu", ""))
    story.append(Spacer(1, 1.5 * mm))
    story.append(card(access_table, bg=colors.HexColor("#f0ebff")))
    story.append(Spacer(1, 4 * mm))

    features = [
        ("✓", "+31 000 kanałów"),
        ("✓", "+130 000 VOD"),
        ("✓", "Przewodnik TV (EPG)"),
        ("✓", "Wydarzenia sportowe"),
        ("✓", "Streaming bez przerw"),
        ("✓", "Natychmiastowa aktywacja"),
        ("✓", "Pomoc przy instalacji 24/7"),
        ("✓", "Kompatybilny ze wszystkimi urządzeniami"),
        ("✓", "Codzienne aktualizacje"),
    ]

    check_style = ParagraphStyle(
        "check", fontName="Helvetica-Bold", fontSize=10,
        textColor=COLOR_PURPLE, alignment=TA_CENTER, leading=14,
    )
    feat_style = ParagraphStyle(
        "feat2", fontName="Helvetica", fontSize=9,
        textColor=COLOR_NAVY, alignment=TA_LEFT, leading=14,
    )

    n_cols = 3
    rows = []
    row = []
    for i, (icon, feat) in enumerate(features):
        cell = Table(
            [[Paragraph(icon, check_style), Paragraph(feat, feat_style)]],
            colWidths=[5 * mm, (usable_width / n_cols) - 10 * mm],
        )
        cell.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWPADDING", (0, 0), (-1, -1), [1 * mm, 1 * mm, 1 * mm, 1 * mm]),
        ]))
        row.append(cell)
        if len(row) == n_cols:
            rows.append(row)
            row = []
    if row:
        while len(row) < n_cols:
            row.append(Paragraph("", feat_style))
        rows.append(row)

    feat_table = Table(rows, colWidths=[usable_width / n_cols] * n_cols)
    feat_table.setStyle(TableStyle([
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("ROWPADDING", (0, 0), (-1, -1), [1 * mm, 1.5 * mm, 1 * mm, 1.5 * mm]),
        ("LINEBEFORE", (1, 0), (1, -1), 0.3, COLOR_GREY),
        ("LINEBEFORE", (2, 0), (2, -1), 0.3, COLOR_GREY),
        ("LINEBELOW",  (0, 0), (-1, -2), 0.3, COLOR_GREY),
    ]))

    story.append(section_header("Co zawiera Twój pakiet", ""))
    story.append(Spacer(1, 1.5 * mm))
    story.append(card(feat_table))
    story.append(Spacer(1, 5 * mm))

    story.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_MID,
                             spaceAfter=3 * mm))

    footer_data = [
        [Paragraph("Dziękujemy za wybór Smarts-Telewizja.pl", s_footer_h)],
        [Paragraph("W razie pytań skontaktuj się z naszym wsparciem.", s_footer_s)],
    ]
    footer_table = Table(footer_data, colWidths=[usable_width])
    footer_table.setStyle(TableStyle([
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("ROWPADDING", (0, 0), (-1, -1), [0, 1 * mm, 0, 1 * mm]),
    ]))
    story.append(footer_table)

    doc.build(story)
    buffer.seek(0)
    return buffer


async def start_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    keyboard = [
        [
            InlineKeyboardButton("1 mois — 10$",   callback_data="pack_1mois"),
            InlineKeyboardButton("3 mois — 20$",   callback_data="pack_3mois"),
        ],
        [
            InlineKeyboardButton("6 mois — 30$",   callback_data="pack_6mois"),
            InlineKeyboardButton("1 an — 37$ ⭐",  callback_data="pack_1an"),
        ],
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🧾 *Choisis le pack :*",
                                    reply_markup=markup,
                                    parse_mode="Markdown")
    return PACK_SELECTION


async def pack_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    pack_key = query.data.replace("pack_", "")
    pack = PACKS.get(pack_key)
    if not pack:
        await query.message.reply_text("❌ Pack invalide. Recommence avec /facture.")
        return ConversationHandler.END
    context.user_data["pack_key"] = pack_key
    context.user_data["pack_label"] = pack["label"]
    context.user_data["pack_price"] = pack["price"]
    await query.edit_message_text(
        f"✅ Pack sélectionné : *{pack['label']}* — {pack['price']}",
        parse_mode="Markdown",
    )
    await query.message.reply_text("👤 *Prénom du client ?*", parse_mode="Markdown")
    return FIRST_NAME


async def collect_first_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["first_name"] = update.message.text.strip()
    await update.message.reply_text("👤 *Nom du client ?*", parse_mode="Markdown")
    return LAST_NAME


async def collect_last_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["last_name"] = update.message.text.strip()
    await update.message.reply_text("📧 *Email du client ?*", parse_mode="Markdown")
    return EMAIL


async def collect_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["email"] = update.message.text.strip()
    await update.message.reply_text("📱 *Téléphone du client ?*", parse_mode="Markdown")
    return PHONE


async def collect_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["phone"] = update.message.text.strip()
    await update.message.reply_text("🔗 *Colle le lien M3U du client :*",
                                    parse_mode="Markdown")
    return M3U_LINK


async def collect_m3u(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    url = update.message.text.strip()
    m3u = parse_m3u(url)
    if not m3u:
        await update.message.reply_text(
            "❌ Lien M3U invalide ou incomplet.\n"
            "Le lien doit contenir `username`, `password`, `host` et `port`.\n\n"
            "Réessaie ou envoie /annuler pour quitter.",
            parse_mode="Markdown",
        )
        return M3U_LINK
    context.user_data["m3u_url"] = url
    context.user_data["m3u"] = m3u
    ud = context.user_data
    summary = (
        "📋 *Vérifie les informations :*\n\n"
        f"🎯 *Pack :* {ud['pack_label']}\n"
        f"💰 *Prix :* {ud['pack_price']}\n"
        f"👤 *Prénom :* {ud['first_name']}\n"
        f"👤 *Nom :* {ud['last_name']}\n"
        f"📧 *Email :* {ud['email']}\n"
        f"📱 *Téléphone :* {ud['phone']}\n"
        f"🔑 *Username :* `{m3u['username']}`\n"
        f"🌐 *Host :* `{m3u['host']}`\n"
        f"🔌 *Port :* `{m3u['port']}`\n\n"
        "Souhaites-tu générer la facture ?"
    )
    keyboard = [
        [
            InlineKeyboardButton("✅ Générer la facture", callback_data="confirm_yes"),
            InlineKeyboardButton("❌ Annuler",             callback_data="confirm_no"),
        ]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(summary, reply_markup=markup, parse_mode="Markdown")
    return CONFIRMATION


async def confirm_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "confirm_no":
        await query.edit_message_text("❌ Facture annulée.")
        context.user_data.clear()
        return ConversationHandler.END

    await query.edit_message_text("⏳ Génération de la facture en cours…")
    ud = context.user_data
    invoice_data = {
        "pack_key":   ud["pack_key"],
        "pack_label": ud["pack_label"],
        "pack_price": ud["pack_price"],
        "first_name": ud["first_name"],
        "last_name":  ud["last_name"],
        "email":      ud["email"],
        "phone":      ud["phone"],
        "m3u":        ud["m3u"],
    }
    try:
        pdf_buffer = generate_invoice_pdf(invoice_data)
        username = ud["m3u"]["username"]
        filename = f"facture_{username}.pdf"
        await query.message.reply_document(
            document=pdf_buffer,
            filename=filename,
            caption=(
                f"✅ *Facture générée avec succès !*\n"
                f"Client : {ud['first_name']} {ud['last_name']}\n"
                f"Pack : {ud['pack_label']} — {ud['pack_price']}"
            ),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.exception("Erreur lors de la génération du PDF")
        await query.message.reply_text(
            f"❌ Erreur lors de la génération de la facture : {e}"
        )
    finally:
        context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("❌ Facture annulée.")
    return ConversationHandler.END


def main():
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("facture", start_invoice)],
        states={
            PACK_SELECTION: [CallbackQueryHandler(pack_selected, pattern=r"^pack_")],
            FIRST_NAME:     [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_first_name)],
            LAST_NAME:      [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_last_name)],
            EMAIL:          [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_email)],
            PHONE:          [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_phone)],
            M3U_LINK:       [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_m3u)],
            CONFIRMATION:   [CallbackQueryHandler(confirm_invoice, pattern=r"^confirm_")],
        },
        fallbacks=[CommandHandler("annuler", cancel)],
        allow_reentry=True,
    )

    application.add_handler(conv_handler)
    logger.info("Bot démarré — en attente de commandes…")
    application.run_polling()


if __name__ == "__main__":
    main()
