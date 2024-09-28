import sys
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from telegram import *
from telegram.ext import *
import threading
import os
import json

with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), "env.json"), "r") as f:
	ENV = json.load(f)

TOKEN = ENV["TOKEN"]
CHATID = ENV["CHATID"]

class MainWindow(QMainWindow):
	def __init__(self):
		super().__init__()
		self.setWindowTitle("Main Window")
		self.setGeometry(300, 300, 400, 200)
	
	def closeEvent(self, event):
		event.ignore()
		self.hide()

menuButtons = ReplyKeyboardMarkup([
		["Lock", "Shut down", "Reboot"],
		["Get file"],
		["Restart bot"]
	], input_field_placeholder="Select an action:", is_persistent=True, resize_keyboard=True
)

environment = None
drives = None
path = None

def resetEnv():
	global environment, drives, path
	environment = None
	drives = [f'{d}:\\' for d in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' if os.path.exists(f'{d}:')]
	path = ""

resetEnv()
bot = Bot(TOKEN)

def browse():
	global path
	ls = os.listdir(path)
	files = [f for f in ls if os.path.isfile(os.path.join(path, f))]
	dirs = [f for f in ls if os.path.isdir(os.path.join(path, f))]
	return (dirs, files)

async def menu(self):
	await self.bot.sendMessage(CHATID, "PC online now.", reply_markup=menuButtons)

lastInterface = None

async def browseInterface():
	global path, lastInterface
	dirs, files = browse()
	if lastInterface:
		await bot.edit_message_text("[closed file browsing]", CHATID, lastInterface.message_id)
	lastInterface = await bot.send_message(CHATID, f"`{path}`", reply_markup=InlineKeyboardMarkup(
		[[InlineKeyboardButton(f"📂 ..", callback_data="..")]] + \
		[[InlineKeyboardButton(f"📂 {dir}", callback_data=dir)] for dir in dirs] + \
		[[InlineKeyboardButton(f"📄 {file}", callback_data=file)] for file in files]
	))

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
	global environment, drives, path
	rawMsg = update.message.text
	msg = rawMsg.lower()
	if msg == "exit":
		resetEnv()
		await update.message.reply_text("Now back to normal mode.", reply_markup=menuButtons)
	else:
		if environment == "FILE":
			path = rawMsg
			await browseInterface()
		else:
			if msg == "lock":
				os.startfile("rundll32.exe", arguments="user32.dll,LockWorkStation")
				await update.message.reply_text("PC locked.")
			elif msg == "shut down":
				await update.message.reply_text("Are you sure to shut down?", reply_markup=InlineKeyboardMarkup([[
					InlineKeyboardButton("Yes", callback_data="shutdown"),
					InlineKeyboardButton("No", callback_data="cancel")
				]]))
			elif msg == "reboot":
				await update.message.reply_text("Are you sure to reboot?", reply_markup=InlineKeyboardMarkup([[
					InlineKeyboardButton("Yes", callback_data="reboot"),
					InlineKeyboardButton("No", callback_data="cancel")
				]]))
			elif msg == "restart bot":
				await update.message.reply_text("Restarting bot ...")
				os.execv(sys.executable, [sys.executable] + sys.argv)
			elif msg == "get file":
				environment = "FILE"
				await update.message.reply_text("Entered file browsing mode.", reply_markup=ReplyKeyboardMarkup([
					drives, ["Exit"]
				], is_persistent=True, resize_keyboard=True))

async def query(update: Update, context: ContextTypes.DEFAULT_TYPE):
	global path
	query = update.callback_query
	await query.answer()
	ans = query.data
	if environment == "FILE":
		if os.path.isfile(path):
			if ans == "file/yes":
				await bot.send_document(CHATID, open(path, "rb"))
			elif ans == "file/no":
				pass
			path = os.path.split(path)[0]
			newPath = path
			await browseInterface()
			return
		else:
			newPath = os.path.join(path, ans)
		if ans == "..":
			path = os.path.split(path)[0]
		elif os.path.exists(newPath):
			path = newPath
			if os.path.isfile(path):
				await query.edit_message_text(f"`{path}`", reply_markup=InlineKeyboardMarkup([
					[InlineKeyboardButton("Yes", callback_data="file/yes")],
					[InlineKeyboardButton("No", callback_data="file/no")]
	  			]))
				return
		dirs, files = browse()
		await query.edit_message_text(f"`{path}`", reply_markup=InlineKeyboardMarkup(
			[[InlineKeyboardButton(f"📂 ..", callback_data="..")]] + \
			[[InlineKeyboardButton(f"📂 {dir}", callback_data=dir)] for dir in dirs] + \
			[[InlineKeyboardButton(f"📄 {file}", callback_data=file)] for file in files]
		))
	else:
		if ans == "cancel":
			await query.edit_message_text("Canceled.")
		elif ans == "shutdown":
			await query.edit_message_text("Shutting down.")
			os.system("shutdown /s")
		elif ans == "reboot":
			await query.edit_message_text("Rebooting ...")
			os.system("shutdown /r")

def ui():
	app = QApplication(sys.argv)
	window = MainWindow()
	tray_icon = QSystemTrayIcon()
	tray_icon.setIcon(QIcon(os.path.join(os.path.abspath(os.path.dirname(__file__)), "icon.png")))

	menu = QMenu()

	quit_action = QAction("Quit")
	quit_action.triggered.connect(app.quit)
	menu.addAction(quit_action)

	tray_icon.setContextMenu(menu)
	tray_icon.activated.connect(lambda reason: window.show() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
	tray_icon.show()

	os._exit(app.exec())

ui_thread = threading.Thread(target=ui)
ui_thread.start()

application = Application.builder().token(TOKEN).build()
application.post_init = menu
application.add_handler(MessageHandler(filters.ALL, handle))
application.add_handler(CallbackQueryHandler(query))
application.run_polling()
